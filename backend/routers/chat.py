from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import get_settings
from core.database import get_db
from core.rate_limit import limiter
from middleware.auth import get_current_user_id
from models.chat import ChatCreate, ChatMessageRequest
from services.chat_service import (
    can_send_messages,
    cleanup_chat_resources,
    document_title_from_name,
    new_chat_document_fields,
    serialize_document_fields,
)
from services.rag_service import stream_chat_response

router = APIRouter(prefix="/chat", tags=["chat"])
_settings = get_settings()


def serialize_chat(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"messages": [], **serialize_document_fields({})}
    serialized = dict(doc)
    if "_id" in serialized:
        serialized["_id"] = str(serialized["_id"])
    if isinstance(serialized.get("userId"), ObjectId):
        serialized["userId"] = str(serialized["userId"])
    serialized.update(serialize_document_fields(doc))
    return serialized


def _chat_list_title(chat: dict[str, Any]) -> str:
    if chat.get("documentName"):
        return document_title_from_name(chat["documentName"])
    return chat.get("title") or "New Chat"


@router.post("/create")
async def create_chat(
    body: ChatCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not body.chatId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid request"},
        )

    now = datetime.now(timezone.utc)
    chat_doc = {
        "chatId": body.chatId,
        "userId": ObjectId(user_id),
        "title": body.title or "New Chat",
        "messages": [],
        "createdAt": now,
        "updatedAt": now,
        **new_chat_document_fields(),
    }
    try:
        result = await db["chats"].insert_one(chat_doc)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to create chat"},
        )

    chat_doc["_id"] = result.inserted_id
    return serialize_chat(chat_doc)


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    chat = await db["chats"].find_one(
        {"chatId": chat_id, "userId": ObjectId(user_id)}
    )
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Chat not found"},
        )

    await cleanup_chat_resources(chat_id, chat)
    await db["chats"].delete_one(
        {"chatId": chat_id, "userId": ObjectId(user_id)}
    )
    return {"success": True}


@router.get("/list")
async def list_chats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db["chats"].find(
        {"userId": ObjectId(user_id)},
        {
            "chatId": 1,
            "title": 1,
            "updatedAt": 1,
            "documentName": 1,
            "ingestionStatus": 1,
            "documentUploaded": 1,
            "summaryStatus": 1,
            "riskStatus": 1,
        },
    ).sort("updatedAt", -1)

    chats = []
    async for chat in cursor:
        chats.append(
            {
                "id": chat["chatId"],
                "title": _chat_list_title(chat),
                "updatedAt": chat.get("updatedAt"),
                "documentName": chat.get("documentName"),
                "ingestionStatus": chat.get("ingestionStatus", "pending"),
                "documentUploaded": bool(chat.get("documentUploaded")),
                "summaryStatus": chat.get("summaryStatus", "pending"),
                "riskStatus": chat.get("riskStatus", "pending"),
            }
        )
    return chats


@router.get("/history/{chat_id}")
async def get_chat_history(
    chat_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    chat = await db["chats"].find_one(
        {"chatId": chat_id, "userId": ObjectId(user_id)}
    )
    if chat:
        await db["chats"].update_one(
            {"chatId": chat_id, "userId": ObjectId(user_id)},
            {"$set": {"lastOpenedAt": datetime.now(timezone.utc)}},
        )
    return serialize_chat(chat)


@router.post("/")
@limiter.limit(_settings.RATE_LIMIT_CHAT)
async def handle_chat(
    request: Request,
    body: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not body.message or not body.chatId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid request"},
        )

    chat = await db["chats"].find_one(
        {"chatId": body.chatId, "userId": ObjectId(user_id)}
    )
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Chat not found"},
        )

    if not can_send_messages(chat):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": (
                    "Please upload and wait for your document to finish processing "
                    "before chatting."
                ),
            },
        )

    return StreamingResponse(
        stream_chat_response(
            db,
            user_id=user_id,
            chat_id=body.chatId,
            message=body.message,
            chat=chat,
            request=request,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
