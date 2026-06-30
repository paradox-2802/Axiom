from core.ai import LLMProvider, get_llm_provider
from core.config import get_settings


async def rewrite_question(
    question: str,
    *,
    session_context: str,
    history: str,
) -> str:
    """Rewrite a follow-up into a standalone retrieval query (retrieval only)."""
    prompt = f"""You rewrite follow-up questions about a financial document into standalone search queries.

SESSION CONTEXT:
{session_context}

CONVERSATION:
{history}

FOLLOW-UP QUESTION:
{question}

Rewrite as one complete standalone question suitable for document search.
- Include company, metric, and reporting period from session context when implied
- If the question is already standalone, return it unchanged
- Do NOT answer the question
- Keep financial terminology precise
- Output only the rewritten question, nothing else"""

    settings = get_settings()
    llm: LLMProvider = get_llm_provider()
    rewritten = await llm.chat_completion(
        model=settings.REWRITE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=settings.REWRITE_MAX_TOKENS,
    )
    return rewritten.strip().strip('"') or question
