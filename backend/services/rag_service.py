import logging
from datetime import datetime, timezone
from collections.abc import AsyncIterator
from typing import Any

from bson import ObjectId
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.ai import LLMProvider, get_llm_provider, get_vector_store
from core.config import get_settings
from services.chat_service import document_title_from_name, get_retrieval_collection
from utils.llm_output import ThinkingStreamFilter, strip_thinking_blocks
from utils.response import sse_event

logger = logging.getLogger(__name__)

STREAM_ERROR_MESSAGE = "Sorry, I couldn't generate a response. Please try again."

SYSTEM_PROMPT_TEMPLATE = """You are a professional financial analyst assisting with document intelligence.

Document: {document_title}

INSTRUCTIONS:
1. Answer ONLY using information from the Context below — never invent financial figures or facts.
2. If the answer is not in the Context, clearly state: "This information is not stated in the document."
3. Cite page numbers when available (e.g., "Page 12").
4. Distinguish documented facts from your interpretation.
5. Use clear, professional language appropriate for financial analysis.
6. Structure responses with direct answers followed by supporting detail when helpful.
7. Respond directly to the user. Never include internal reasoning, thinking tags, or chain-of-thought in your reply.

Context:
{context}"""

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


def _document_title(chat: dict[str, Any]) -> str:
    if chat.get("documentName"):
        return document_title_from_name(chat["documentName"])
    return chat.get("title") or "Financial Document"


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


def _conversation_for_llm(
    messages: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, str]]:
    recent = messages[-limit:]
    llm_messages: list[dict[str, str]] = []
    for item in recent:
        role = item.get("role")
        content = item.get("content", "")
        if role in ("user", "assistant") and content:
            llm_messages.append({"role": role, "content": content})
    return llm_messages


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

    if not messages or title == "New Chat":
        max_len = settings.CHAT_TITLE_MAX_LENGTH
        title = message if len(message) <= max_len else f"{message[:max_len]}..."

    now = datetime.now(timezone.utc)
    messages.append({"role": "user", "content": message})
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
        messages.append({"role": "assistant", "content": fallback})
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

    try:
        docs = await retrieve_documents(message, collection_name)
    except Exception:
        logger.exception("Document retrieval failed for chat %s", chat_id)
        fallback = STREAM_ERROR_MESSAGE
        messages.append({"role": "assistant", "content": fallback})
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
        messages.append({"role": "assistant", "content": fallback})
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
    document_title = _document_title(chat)
    llm: LLMProvider = get_llm_provider()

    prior_turns = _conversation_for_llm(
        messages[:-1],
        limit=settings.CHAT_HISTORY_LIMIT,
    )
    stream_messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT_TEMPLATE.format(
                document_title=document_title,
                context=context,
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

    if not full_answer.strip() and not stream_failed:
        full_answer = STREAM_ERROR_MESSAGE
        yield sse_event({"error": STREAM_ERROR_MESSAGE})

    if stream_failed and not full_answer:
        full_answer = STREAM_ERROR_MESSAGE
        yield sse_event({"error": STREAM_ERROR_MESSAGE})
    elif stream_failed:
        yield sse_event({"error": STREAM_ERROR_MESSAGE})

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

    yield sse_event({"sources": sources, "title": title, "done": True})
