import logging
from datetime import datetime, timezone
from collections.abc import AsyncIterator
from typing import Any

from bson import ObjectId
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.ai import LLMProvider, get_llm_provider, get_vector_store
from core.config import get_settings
from services.ai_service import rewrite_question
from services.chat_service import get_retrieval_collection
from services.memory_service import (
    build_session_context,
    build_system_prompt,
    conversation_for_llm,
    format_conversation_for_rewrite,
    needs_query_rewrite,
)
from utils.llm_output import ThinkingStreamFilter, strip_thinking_blocks
from utils.response import sse_event

logger = logging.getLogger(__name__)

STREAM_ERROR_MESSAGE = "Sorry, I couldn't generate a response. Please try again."


def _format_chunk_metadata(metadata: dict[str, Any]) -> str:
    parts: list[str] = []
    page = metadata.get("page")
    if page is not None:
        parts.append(f"Page {int(page) + 1}")
    section = metadata.get("sectionHeading")
    if section:
        parts.append(f"Section: {section}")
    title = metadata.get("documentTitle")
    if title:
        parts.append(f"Document: {title}")
    return " | ".join(parts)


async def retrieve_documents(query: str, collection_name: str) -> list[Any]:
    settings = get_settings()
    vector_store = get_vector_store(settings, collection_name=collection_name)
    retriever = vector_store.as_retriever(search_kwargs={"k": settings.RETRIEVAL_K})
    return await retriever.ainvoke(query)


def build_context(docs: list[Any]) -> str:
    blocks: list[str] = []
    for index, doc in enumerate(docs):
        meta_line = _format_chunk_metadata(doc.metadata or {})
        header = f"Source {index + 1}"
        if meta_line:
            header = f"{header} ({meta_line})"
        blocks.append(f"{header}:\n{doc.page_content}")
    return "\n\n".join(blocks)


def build_sources(docs: list[Any]) -> list[dict[str, Any]]:
    settings = get_settings()
    preview_len = settings.SOURCE_PREVIEW_LENGTH
    sources: list[dict[str, Any]] = []
    for doc in docs:
        metadata = dict(doc.metadata or {})
        page = metadata.get("page")
        sources.append(
            {
                "preview": doc.page_content[:preview_len],
                "metadata": metadata,
                "page": int(page) + 1 if page is not None else None,
                "sectionHeading": metadata.get("sectionHeading"),
                "documentTitle": metadata.get("documentTitle"),
            }
        )
    return sources


async def _client_disconnected(request: Request | None) -> bool:
    return request is not None and await request.is_disconnected()


async def _persist_messages(
    chats,
    *,
    chat_id: str,
    user_object_id: ObjectId,
    messages: list[dict[str, Any]],
    title: str,
    updated_at: datetime,
) -> None:
    await chats.update_one(
        {"chatId": chat_id, "userId": user_object_id},
        {"$set": {"messages": messages, "title": title, "updatedAt": updated_at}},
    )


async def _resolve_retrieval_query(
    *,
    message: str,
    chat: dict[str, Any],
    prior_messages: list[dict[str, Any]],
    settings,
) -> str:
    """Rewrite follow-up questions for retrieval only; original message stays in history."""
    if not needs_query_rewrite(
        message,
        prior_messages,
        min_words=settings.REWRITE_MIN_WORDS,
    ):
        return message

    session_context = build_session_context(chat)
    history_messages = conversation_for_llm(
        prior_messages,
        max_turns=settings.CHAT_MEMORY_TURNS,
    )
    history_text = format_conversation_for_rewrite(history_messages)

    try:
        rewritten = await rewrite_question(
            message,
            session_context=session_context,
            history=history_text,
        )
        if rewritten and rewritten != message:
            logger.info("Query rewritten for retrieval: %r -> %r", message, rewritten)
        return rewritten or message
    except Exception:
        logger.exception("Query rewrite failed; using original message for retrieval")
        return message


async def stream_chat_response(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    chat_id: str,
    message: str,
    chat: dict[str, Any],
    request: Request | None = None,
) -> AsyncIterator[str]:
    settings = get_settings()
    chats = db["chats"]
    user_object_id = ObjectId(user_id)

    title = chat.get("title", "New Chat")
    messages = list(chat.get("messages", []))
    prior_messages = list(messages)

    if not messages or title == "New Chat":
        max_len = settings.CHAT_TITLE_MAX_LENGTH
        title = message if len(message) <= max_len else f"{message[:max_len]}..."

    now = datetime.now(timezone.utc)
    messages.append(
        {
            "role": "user",
            "content": message,
            "timestamp": now.isoformat(),
        }
    )
    await _persist_messages(
        chats,
        chat_id=chat_id,
        user_object_id=user_object_id,
        messages=messages,
        title=title,
        updated_at=now,
    )

    if await _client_disconnected(request):
        return

    collection_name = get_retrieval_collection(chat, settings)
    if not collection_name:
        fallback = "Please upload a PDF document to this chat before asking questions."
        messages.append(
            {
                "role": "assistant",
                "content": fallback,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        await _persist_messages(
            chats,
            chat_id=chat_id,
            user_object_id=user_object_id,
            messages=messages,
            title=title,
            updated_at=now,
        )
        yield sse_event({"error": fallback})
        yield sse_event({"sources": [], "title": title, "done": True})
        return

    logger.info(
        "Chat stream started: chat_id=%s user_id=%s collection=%s",
        chat_id,
        user_id,
        collection_name,
    )

    retrieval_query = await _resolve_retrieval_query(
        message=message,
        chat=chat,
        prior_messages=prior_messages,
        settings=settings,
    )

    try:
        docs = await retrieve_documents(retrieval_query, collection_name)
    except Exception:
        logger.exception("Document retrieval failed for chat %s", chat_id)
        fallback = STREAM_ERROR_MESSAGE
        messages.append(
            {
                "role": "assistant",
                "content": fallback,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        await _persist_messages(
            chats,
            chat_id=chat_id,
            user_object_id=user_object_id,
            messages=messages,
            title=title,
            updated_at=now,
        )
        yield sse_event({"error": fallback})
        yield sse_event({"sources": [], "title": title, "done": True})
        return

    if not docs:
        fallback = "This information is not stated in the document."
        messages.append(
            {
                "role": "assistant",
                "content": fallback,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        await _persist_messages(
            chats,
            chat_id=chat_id,
            user_object_id=user_object_id,
            messages=messages,
            title=title,
            updated_at=now,
        )
        yield sse_event({"content": fallback})
        yield sse_event({"sources": [], "title": title, "done": True})
        return

    if await _client_disconnected(request):
        return

    context = build_context(docs)
    sources = build_sources(docs)
    session_context = build_session_context(chat)
    llm: LLMProvider = get_llm_provider()

    prior_turns = conversation_for_llm(
        prior_messages,
        max_turns=settings.CHAT_MEMORY_TURNS,
    )
    stream_messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": build_system_prompt(
                session_context=session_context,
                document_context=context,
            ),
        },
        *prior_turns,
        {"role": "user", "content": message},
    ]

    full_answer = ""
    stream_failed = False
    thinking_filter = ThinkingStreamFilter()

    try:
        async for chunk in llm.stream_chat(
            model=settings.CHAT_MODEL,
            messages=stream_messages,
            temperature=settings.CHAT_TEMPERATURE,
            max_tokens=settings.CHAT_MAX_TOKENS,
        ):
            if await _client_disconnected(request):
                break

            full_answer += chunk
            visible = thinking_filter.feed(chunk)
            if visible:
                yield sse_event({"content": visible})
    except Exception:
        logger.exception("LLM stream failed for chat %s", chat_id)
        stream_failed = True

    disconnected = await _client_disconnected(request)

    trailing = thinking_filter.flush()
    if trailing:
        yield sse_event({"content": trailing})

    full_answer = strip_thinking_blocks(full_answer)

    if not full_answer.strip():
        full_answer = STREAM_ERROR_MESSAGE
        yield sse_event({"error": STREAM_ERROR_MESSAGE})
    elif stream_failed:
        logger.warning(
            "Chat stream ended with errors but a usable answer was recovered for chat %s",
            chat_id,
        )

    if full_answer:
        assistant_message = {
            "role": "assistant",
            "content": full_answer,
            "sources": sources,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        messages.append(assistant_message)
        await _persist_messages(
            chats,
            chat_id=chat_id,
            user_object_id=user_object_id,
            messages=messages,
            title=title,
            updated_at=datetime.now(timezone.utc),
        )

    if disconnected:
        return

    yield sse_event(
        {
            "sources": sources,
            "title": title,
            "content": full_answer if full_answer != STREAM_ERROR_MESSAGE else "",
            "done": True,
        }
    )
