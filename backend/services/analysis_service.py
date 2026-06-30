import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import ValidationError

from core.ai import LLMProvider, get_llm_provider
from core.config import Settings, get_settings
from models.insights import ExecutiveSummaryData, RiskAnalysisData
from services.chat_service import get_retrieval_collection
from services.rag_service import build_context, retrieve_documents
from utils.llm_output import strip_thinking_blocks

logger = logging.getLogger(__name__)

SUMMARY_RETRIEVAL_QUERY = (
    "business overview company profile revenue profit earnings management "
    "discussion analysis financial highlights outlook guidance annual report"
)

RISK_RETRIEVAL_QUERY = (
    "risk factors uncertainties regulatory litigation competition foreign exchange "
    "compliance legal proceedings market risks operational risks credit liquidity"
)

EXECUTIVE_SUMMARY_SYSTEM = """You are a professional financial analyst preparing an executive summary.

Use ONLY the provided document context. Never invent financial figures or facts.
If a section cannot be supported by the context, write "Not stated in the document."

Return valid JSON only (no markdown fences) with this exact structure:
{
  "businessOverview": "string",
  "revenueAndProfit": "string",
  "keyHighlights": ["string"],
  "managementOutlook": "string",
  "notableChanges": "string"
}"""

RISK_ANALYSIS_SYSTEM = """You are a professional financial analyst extracting explicitly stated risks.

Rules:
- Extract ONLY risks explicitly stated in the document context.
- Never infer or speculate about risks not mentioned.
- Severity must be High, Medium, or Low based on the document's own emphasis.
- If no risks are found, return an empty risks array.

Return valid JSON only (no markdown fences) with this exact structure:
{
  "risks": [
    {
      "category": "string",
      "description": "string",
      "severity": "High" | "Medium" | "Low"
    }
  ]
}"""


def _analysis_model(settings: Settings) -> str:
    return settings.ANALYSIS_MODEL or settings.CHAT_MODEL


def _extract_json(raw: str) -> dict[str, Any]:
    text = strip_thinking_blocks(raw).strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response")
    return json.loads(text[start : end + 1])


async def _generate_json(
    *,
    system_prompt: str,
    user_prompt: str,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    llm: LLMProvider = get_llm_provider()
    return await llm.chat_completion(
        model=_analysis_model(settings),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=settings.ANALYSIS_MAX_TOKENS,
    )


def _document_context_header(chat: dict[str, Any]) -> str:
    title = chat.get("documentName") or chat.get("title") or "Financial Document"
    if title.lower().endswith(".pdf"):
        title = title[:-4]
    return f"Document: {title}"


async def _retrieve_for_analysis(
    query: str,
    chat: dict[str, Any],
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    collection = get_retrieval_collection(chat, settings)
    if not collection:
        raise ValueError("No document indexed for this workspace")

    docs = await retrieve_documents(query, collection)
    if not docs:
        raise ValueError("No relevant content found in the document")

    header = _document_context_header(chat)
    return f"{header}\n\n{build_context(docs)}"


async def generate_executive_summary(
    chat: dict[str, Any],
    settings: Settings | None = None,
) -> ExecutiveSummaryData:
    settings = settings or get_settings()
    context = await _retrieve_for_analysis(SUMMARY_RETRIEVAL_QUERY, chat, settings)
    raw = await _generate_json(
        system_prompt=EXECUTIVE_SUMMARY_SYSTEM,
        user_prompt=f"Context:\n{context}\n\nGenerate the executive summary JSON.",
        settings=settings,
    )
    parsed = _extract_json(raw)
    return ExecutiveSummaryData.model_validate(parsed)


async def generate_risk_analysis(
    chat: dict[str, Any],
    settings: Settings | None = None,
) -> RiskAnalysisData:
    settings = settings or get_settings()
    context = await _retrieve_for_analysis(RISK_RETRIEVAL_QUERY, chat, settings)
    raw = await _generate_json(
        system_prompt=RISK_ANALYSIS_SYSTEM,
        user_prompt=f"Context:\n{context}\n\nExtract explicitly stated risks as JSON.",
        settings=settings,
    )
    parsed = _extract_json(raw)
    return RiskAnalysisData.model_validate(parsed)


def _serialize_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


async def get_cached_summary(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    chat_id: str,
) -> dict[str, Any]:
    chat = await db["chats"].find_one(
        {"chatId": chat_id, "userId": ObjectId(user_id)}
    )
    if not chat:
        return {"status": "unavailable", "error": "Workspace not found"}

    if chat.get("ingestionStatus") != "completed" and not chat.get("messages"):
        return {"status": "unavailable", "error": "Document is not ready for analysis"}

    if chat.get("executiveSummary"):
        return {
            "status": "ready",
            "data": chat["executiveSummary"],
            "generatedAt": _serialize_dt(chat.get("summaryGeneratedAt")),
            "cached": True,
        }

    if chat.get("summaryStatus") == "generating":
        return {"status": "generating"}

    return {"status": "idle"}


async def generate_summary(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    chat_id: str,
    regenerate: bool = False,
) -> dict[str, Any]:
    chat = await db["chats"].find_one(
        {"chatId": chat_id, "userId": ObjectId(user_id)}
    )
    if not chat:
        return {"status": "unavailable", "error": "Workspace not found"}

    if chat.get("ingestionStatus") != "completed" and not chat.get("messages"):
        return {"status": "unavailable", "error": "Document is not ready for analysis"}

    if not regenerate and chat.get("executiveSummary"):
        return {
            "status": "ready",
            "data": chat["executiveSummary"],
            "generatedAt": _serialize_dt(chat.get("summaryGeneratedAt")),
            "cached": True,
        }

    if chat.get("summaryStatus") == "generating" and not regenerate:
        return {"status": "generating"}

    now = datetime.now(timezone.utc)
    await db["chats"].update_one(
        {"chatId": chat_id, "userId": ObjectId(user_id)},
        {"$set": {"summaryStatus": "generating", "updatedAt": now}},
    )

    try:
        summary = await generate_executive_summary(chat)
        data = summary.model_dump()
        await db["chats"].update_one(
            {"chatId": chat_id, "userId": ObjectId(user_id)},
            {
                "$set": {
                    "executiveSummary": data,
                    "summaryStatus": "completed",
                    "summaryGeneratedAt": now,
                    "updatedAt": now,
                }
            },
        )
        return {
            "status": "ready",
            "data": data,
            "generatedAt": _serialize_dt(now),
            "cached": False,
        }
    except (ValidationError, ValueError, json.JSONDecodeError):
        logger.exception("Executive summary validation failed for %s", chat_id)
        await db["chats"].update_one(
            {"chatId": chat_id, "userId": ObjectId(user_id)},
            {"$set": {"summaryStatus": "failed", "updatedAt": now}},
        )
        return {
            "status": "error",
            "error": "Could not generate a valid summary. Please try again.",
        }
    except Exception:
        logger.exception("Executive summary generation failed for %s", chat_id)
        await db["chats"].update_one(
            {"chatId": chat_id, "userId": ObjectId(user_id)},
            {"$set": {"summaryStatus": "failed", "updatedAt": now}},
        )
        return {
            "status": "error",
            "error": "Summary generation failed. Please try again later.",
        }


async def get_cached_risks(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    chat_id: str,
) -> dict[str, Any]:
    chat = await db["chats"].find_one(
        {"chatId": chat_id, "userId": ObjectId(user_id)}
    )
    if not chat:
        return {"status": "unavailable", "error": "Workspace not found"}

    if chat.get("ingestionStatus") != "completed" and not chat.get("messages"):
        return {"status": "unavailable", "error": "Document is not ready for analysis"}

    if chat.get("riskAnalysis"):
        return {
            "status": "ready",
            "data": chat["riskAnalysis"],
            "generatedAt": _serialize_dt(chat.get("riskGeneratedAt")),
            "cached": True,
        }

    if chat.get("riskStatus") == "generating":
        return {"status": "generating"}

    return {"status": "idle"}


async def generate_risks(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    chat_id: str,
    regenerate: bool = False,
) -> dict[str, Any]:
    chat = await db["chats"].find_one(
        {"chatId": chat_id, "userId": ObjectId(user_id)}
    )
    if not chat:
        return {"status": "unavailable", "error": "Workspace not found"}

    if chat.get("ingestionStatus") != "completed" and not chat.get("messages"):
        return {"status": "unavailable", "error": "Document is not ready for analysis"}

    if not regenerate and chat.get("riskAnalysis"):
        return {
            "status": "ready",
            "data": chat["riskAnalysis"],
            "generatedAt": _serialize_dt(chat.get("riskGeneratedAt")),
            "cached": True,
        }

    if chat.get("riskStatus") == "generating" and not regenerate:
        return {"status": "generating"}

    now = datetime.now(timezone.utc)
    await db["chats"].update_one(
        {"chatId": chat_id, "userId": ObjectId(user_id)},
        {"$set": {"riskStatus": "generating", "updatedAt": now}},
    )

    try:
        risks = await generate_risk_analysis(chat)
        data = risks.model_dump()
        await db["chats"].update_one(
            {"chatId": chat_id, "userId": ObjectId(user_id)},
            {
                "$set": {
                    "riskAnalysis": data,
                    "riskStatus": "completed",
                    "riskGeneratedAt": now,
                    "updatedAt": now,
                }
            },
        )
        return {
            "status": "ready",
            "data": data,
            "generatedAt": _serialize_dt(now),
            "cached": False,
        }
    except (ValidationError, ValueError, json.JSONDecodeError):
        logger.exception("Risk analysis validation failed for %s", chat_id)
        await db["chats"].update_one(
            {"chatId": chat_id, "userId": ObjectId(user_id)},
            {"$set": {"riskStatus": "failed", "updatedAt": now}},
        )
        return {
            "status": "error",
            "error": "Could not generate a valid risk analysis. Please try again.",
        }
    except Exception:
        logger.exception("Risk analysis generation failed for %s", chat_id)
        await db["chats"].update_one(
            {"chatId": chat_id, "userId": ObjectId(user_id)},
            {"$set": {"riskStatus": "failed", "updatedAt": now}},
        )
        return {
            "status": "error",
            "error": "Risk analysis failed. Please try again later.",
        }
