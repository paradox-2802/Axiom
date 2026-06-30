import re
from datetime import datetime
from typing import Any

from services.chat_service import document_title_from_name

_FOLLOW_UP_PATTERN = re.compile(
    r"\b("
    r"what about|how about|last year|last quarter|previous year|"
    r"further|more detail|more about|compare|versus|vs\.?|"
    r"explain that|explain this|why\?|"
    r"\b(it|they|them|those|these|their|its)\b|"
    r"\b(that|this)\b(?!\s+document)"
    r")",
    re.IGNORECASE,
)


def _format_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def build_session_context(chat: dict[str, Any]) -> str:
    """Layer 1 — session-scoped metadata injected into every LLM request."""
    lines: list[str] = []

    document_name = chat.get("documentName")
    if document_name:
        lines.append(f"Document file: {document_name}")

    company = chat.get("companyName")
    if not company and document_name:
        company = document_title_from_name(document_name)
    if company:
        lines.append(f"Company: {company}")

    reporting_period = chat.get("reportingPeriod")
    if reporting_period:
        lines.append(f"Reporting period: {reporting_period}")

    uploaded_at = _format_timestamp(chat.get("uploadedAt"))
    if uploaded_at:
        lines.append(f"Uploaded at: {uploaded_at}")

    vector_collection = chat.get("vectorCollection")
    if vector_collection:
        lines.append(f"Vector collection: {vector_collection}")

    chat_id = chat.get("chatId")
    if chat_id:
        lines.append(f"Chat session: {chat_id}")

    if not lines:
        return "Document: Financial Document (no session metadata yet)"

    return "\n".join(lines)


def conversation_for_llm(
    messages: list[dict[str, Any]],
    *,
    max_turns: int,
) -> list[dict[str, str]]:
    """
    Layer 2 — recent user/assistant turns for this session only.
    max_turns is the number of user+assistant exchanges (not individual messages).
    """
    eligible: list[dict[str, str]] = []
    for item in messages:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            eligible.append({"role": role, "content": content})

    if max_turns <= 0:
        return []

    max_messages = max_turns * 2
    return eligible[-max_messages:]


def format_conversation_for_rewrite(messages: list[dict[str, str]]) -> str:
    if not messages:
        return "(no prior conversation)"
    return "\n".join(f"{item['role']}: {item['content']}" for item in messages)


def needs_query_rewrite(
    message: str,
    prior_messages: list[dict[str, Any]],
    *,
    min_words: int = 6,
) -> bool:
    """Rewrite retrieval query when the question depends on prior conversation."""
    if not prior_messages:
        return False

    word_count = len(message.split())
    if word_count < min_words:
        return True

    return bool(_FOLLOW_UP_PATTERN.search(message))


def build_system_prompt(*, session_context: str, document_context: str) -> str:
    return f"""You are a professional financial analyst assisting with document intelligence.

SESSION CONTEXT (current workspace only):
{session_context}

INSTRUCTIONS:
1. Answer ONLY using information from the Document Context below — never invent financial figures or facts.
2. If the answer is not in the Document Context, clearly state: "This information is not stated in the document."
3. Cite page numbers when available (e.g., "Page 12").
4. Use recent conversation history for follow-up continuity, but if it conflicts with the document, always trust the document.
5. Distinguish documented facts from your interpretation.
6. Use clear, professional language appropriate for financial analysis.
7. Structure responses with direct answers followed by supporting detail when helpful.
8. Respond directly to the user. Never include internal reasoning, thinking tags, or chain-of-thought in your reply.

DOCUMENT CONTEXT (retrieved from the uploaded PDF — highest-priority factual source):
{document_context}"""
