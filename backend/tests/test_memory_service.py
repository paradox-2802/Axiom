from datetime import datetime, timezone

from services.memory_service import (
    build_session_context,
    build_system_prompt,
    conversation_for_llm,
    format_conversation_for_rewrite,
    needs_query_rewrite,
)


def _sample_chat() -> dict:
    return {
        "chatId": "session-abc",
        "documentName": "acme-corp-annual-report-2024.pdf",
        "companyName": "Acme Corp",
        "reportingPeriod": "FY 2024",
        "uploadedAt": datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc),
        "vectorCollection": "axiom_session-abc",
    }


def test_build_session_context_includes_metadata():
    context = build_session_context(_sample_chat())
    assert "acme-corp-annual-report-2024.pdf" in context
    assert "Acme Corp" in context
    assert "FY 2024" in context
    assert "axiom_session-abc" in context
    assert "session-abc" in context


def test_build_session_context_derives_company_from_document_name():
    chat = {"documentName": "globex-q1-2025.pdf"}
    context = build_session_context(chat)
    assert "globex-q1-2025.pdf" in context
    assert "Company:" in context


def test_conversation_for_llm_limits_turns():
    messages = []
    for i in range(10):
        messages.append({"role": "user", "content": f"question {i}"})
        messages.append({"role": "assistant", "content": f"answer {i}"})

    limited = conversation_for_llm(messages, max_turns=3)
    assert len(limited) == 6
    assert limited[0]["content"] == "question 7"
    assert limited[-1]["content"] == "answer 9"


def test_conversation_for_llm_preserves_order_and_roles():
    messages = [
        {"role": "user", "content": "What was revenue?"},
        {"role": "assistant", "content": "Revenue was $10M."},
        {"role": "user", "content": "What about last year?"},
    ]
    result = conversation_for_llm(messages, max_turns=8)
    assert result == [
        {"role": "user", "content": "What was revenue?"},
        {"role": "assistant", "content": "Revenue was $10M."},
        {"role": "user", "content": "What about last year?"},
    ]


def test_conversation_for_llm_skips_empty_messages():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": ""},
        {"role": "user", "content": "Follow up"},
    ]
    result = conversation_for_llm(messages, max_turns=8)
    assert result == [
        {"role": "user", "content": "Hello"},
        {"role": "user", "content": "Follow up"},
    ]


def test_needs_query_rewrite_without_history():
    assert needs_query_rewrite("What about last year?", []) is False


def test_needs_query_rewrite_short_follow_up():
    prior = [{"role": "user", "content": "What was revenue?"}]
    assert needs_query_rewrite("What about last year?", prior) is True


def test_needs_query_rewrite_standalone_question():
    prior = [{"role": "user", "content": "What was revenue?"}]
    question = (
        "What was the company's total operating revenue in fiscal year 2024 "
        "according to this document?"
    )
    assert needs_query_rewrite(question, prior, min_words=6) is False


def test_needs_query_rewrite_pronoun_follow_up():
    prior = [
        {"role": "user", "content": "What was revenue?"},
        {"role": "assistant", "content": "Revenue was $10M."},
    ]
    assert needs_query_rewrite("Why was it higher?", prior) is True


def test_format_conversation_for_rewrite():
    messages = [
        {"role": "user", "content": "What was revenue?"},
        {"role": "assistant", "content": "Revenue was $10M."},
    ]
    text = format_conversation_for_rewrite(messages)
    assert "user: What was revenue?" in text
    assert "assistant: Revenue was $10M." in text


def test_build_system_prompt_prioritizes_document():
    prompt = build_system_prompt(
        session_context="Company: Acme Corp",
        document_context="Source 1: Revenue was $10M.",
    )
    assert "SESSION CONTEXT" in prompt
    assert "Acme Corp" in prompt
    assert "DOCUMENT CONTEXT" in prompt
    assert "Revenue was $10M" in prompt
    assert "always trust the document" in prompt


def test_session_context_isolated_per_chat():
    chat_a = _sample_chat()
    chat_b = {
        "chatId": "session-xyz",
        "documentName": "other-inc-10k.pdf",
        "companyName": "Other Inc",
        "vectorCollection": "axiom_session-xyz",
    }
    context_a = build_session_context(chat_a)
    context_b = build_session_context(chat_b)
    assert "Acme Corp" in context_a
    assert "Other Inc" in context_b
    assert "Acme Corp" not in context_b
    assert "Other Inc" not in context_a
