import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from core.ai import collection_name_for_chat, delete_vector_collection
from core.config import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_DOCUMENT_FIELDS: dict[str, Any] = {
    "documentName": None,
    "documentUploaded": False,
    "documentLocked": False,
    "ingestionStatus": "pending",
    "uploadedAt": None,
    "vectorCollection": None,
    "pdfPath": None,
    "lastOpenedAt": None,
    "companyName": None,
    "reportingPeriod": None,
    "executiveSummary": None,
    "riskAnalysis": None,
    "summaryStatus": "pending",
    "riskStatus": "pending",
    "summaryGeneratedAt": None,
    "riskGeneratedAt": None,
}


def new_chat_document_fields() -> dict[str, Any]:
    return dict(DEFAULT_DOCUMENT_FIELDS)


def is_legacy_chat(chat: dict[str, Any]) -> bool:
    """Sessions with history but no session-scoped document (pre-migration)."""
    return bool(chat.get("messages")) and not chat.get("documentUploaded")


def can_send_messages(chat: dict[str, Any]) -> bool:
    if chat.get("documentUploaded"):
        return chat.get("ingestionStatus") == "completed"
    return is_legacy_chat(chat)


def get_retrieval_collection(chat: dict[str, Any], settings: Settings | None = None) -> str | None:
    settings = settings or get_settings()
    vector_collection = chat.get("vectorCollection")
    if vector_collection:
        return vector_collection
    if is_legacy_chat(chat):
        return settings.QDRANT_COLLECTION
    return None


def document_title_from_name(filename: str) -> str:
    name = filename
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    return name.strip() or "New Chat"


def normalize_messages(messages: Any) -> list[dict[str, Any]]:
    """Return chronological user/assistant messages for API responses."""
    if not isinstance(messages, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in ("user", "assistant"):
            continue

        content = item.get("content", "")
        if not isinstance(content, str):
            content = str(content) if content is not None else ""

        msg: dict[str, Any] = {"role": role, "content": content}
        if item.get("timestamp"):
            msg["timestamp"] = item["timestamp"]
        if item.get("insightType"):
            msg["insightType"] = item["insightType"]
        if role == "assistant" and item.get("sources"):
            msg["sources"] = item["sources"]
        normalized.append(msg)

    return normalized


def serialize_document_fields(chat: dict[str, Any]) -> dict[str, Any]:
    return {
        "documentName": chat.get("documentName"),
        "documentUploaded": bool(chat.get("documentUploaded")),
        "documentLocked": bool(chat.get("documentLocked")),
        "ingestionStatus": chat.get("ingestionStatus", "pending"),
        "uploadedAt": chat.get("uploadedAt"),
        "vectorCollection": chat.get("vectorCollection"),
        "companyName": chat.get("companyName"),
        "reportingPeriod": chat.get("reportingPeriod"),
        "executiveSummary": chat.get("executiveSummary"),
        "riskAnalysis": chat.get("riskAnalysis"),
        "summaryStatus": chat.get("summaryStatus", "pending"),
        "riskStatus": chat.get("riskStatus", "pending"),
        "summaryGeneratedAt": chat.get("summaryGeneratedAt"),
        "riskGeneratedAt": chat.get("riskGeneratedAt"),
    }


async def update_ingestion_status(
    db: AsyncIOMotorDatabase,
    chat_id: str,
    status: str,
) -> None:
    await db["chats"].update_one(
        {"chatId": chat_id},
        {
            "$set": {
                "ingestionStatus": status,
                "updatedAt": datetime.now(timezone.utc),
            }
        },
    )


async def cleanup_chat_resources(chat_id: str, chat: dict[str, Any]) -> None:
    settings = get_settings()

    collections_to_try: list[str] = []
    if chat.get("vectorCollection"):
        collections_to_try.append(chat["vectorCollection"])
    named = collection_name_for_chat(chat_id)
    if named not in collections_to_try:
        collections_to_try.append(named)

    for collection in collections_to_try:
        try:
            delete_vector_collection(collection)
        except Exception:
            logger.exception("Failed to delete vector collection %s", collection)

    pdf_path = chat.get("pdfPath")
    if pdf_path:
        try:
            Path(pdf_path).unlink(missing_ok=True)
        except OSError:
            logger.exception("Failed to delete PDF at %s", pdf_path)

    chat_upload_dir = Path(settings.UPLOAD_DIR) / chat_id
    if chat_upload_dir.exists():
        try:
            shutil.rmtree(chat_upload_dir)
        except OSError:
            logger.exception("Failed to delete upload directory %s", chat_upload_dir)
