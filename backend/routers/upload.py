import logging
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.ai import collection_name_for_chat
from core.config import get_settings
from core.database import get_db
from core.rate_limit import limiter
from middleware.auth import get_current_user_id
from services.chat_service import document_title_from_name
from utils.file_upload import save_pdf_for_chat
from worker.tasks import enqueue_pdf_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])
_settings = get_settings()


@router.post("")
@limiter.limit(_settings.RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    chatId: str = Form(...),
    pdf: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not chatId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Chat ID required"},
        )

    chat = await db["chats"].find_one(
        {"chatId": chatId, "userId": ObjectId(user_id)}
    )
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Chat not found"},
        )

    if chat.get("documentLocked") or chat.get("documentUploaded"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "message": (
                    "This chat already has an uploaded document. "
                    "Create a new chat to analyse another PDF."
                ),
            },
        )

    path, filename = await save_pdf_for_chat(chatId, pdf)
    vector_collection = collection_name_for_chat(chatId)
    now = datetime.now(timezone.utc)
    title = document_title_from_name(filename)

    try:
        await db["chats"].update_one(
            {"chatId": chatId, "userId": ObjectId(user_id)},
            {
                "$set": {
                    "documentName": filename,
                    "documentUploaded": True,
                    "documentLocked": True,
                    "ingestionStatus": "processing",
                    "uploadedAt": now,
                    "vectorCollection": vector_collection,
                    "pdfPath": path,
                    "title": title,
                    "companyName": title,
                    "updatedAt": now,
                }
            },
        )
        await enqueue_pdf_job(path, filename, chatId, vector_collection)
    except Exception:
        Path(path).unlink(missing_ok=True)
        await db["chats"].update_one(
            {"chatId": chatId, "userId": ObjectId(user_id)},
            {
                "$set": {
                    "documentName": None,
                    "documentUploaded": False,
                    "documentLocked": False,
                    "ingestionStatus": "pending",
                    "uploadedAt": None,
                    "vectorCollection": None,
                    "pdfPath": None,
                    "companyName": None,
                    "reportingPeriod": None,
                    "updatedAt": now,
                }
            },
        )
        logger.exception("Failed to enqueue PDF job for chat %s", chatId)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to queue document for processing"},
        )

    logger.info("PDF uploaded for chat %s: %s", chatId, filename)
    return {
        "success": True,
        "message": "Document uploaded and processing",
        "ingestionStatus": "processing",
        "documentName": filename,
        "vectorCollection": vector_collection,
    }
