from services.chat_service import (
    can_send_messages,
    get_retrieval_collection,
    is_legacy_chat,
    normalize_messages,
)


def test_can_send_messages_requires_completed_ingestion():
    chat = {
        "documentUploaded": True,
        "ingestionStatus": "processing",
        "messages": [],
    }
    assert can_send_messages(chat) is False

    chat["ingestionStatus"] = "completed"
    assert can_send_messages(chat) is True


def test_legacy_chat_allows_messages_without_document():
    chat = {
        "documentUploaded": False,
        "ingestionStatus": "pending",
        "messages": [{"role": "user", "content": "hello"}],
    }
    assert is_legacy_chat(chat) is True
    assert can_send_messages(chat) is True


def test_new_empty_chat_cannot_send_messages():
    chat = {
        "documentUploaded": False,
        "ingestionStatus": "pending",
        "messages": [],
    }
    assert can_send_messages(chat) is False
    assert get_retrieval_collection(chat) is None


def test_session_scoped_collection_used_for_uploaded_chat():
    chat = {
        "documentUploaded": True,
        "ingestionStatus": "completed",
        "vectorCollection": "axiom_chat-99",
        "messages": [],
    }
    assert get_retrieval_collection(chat) == "axiom_chat-99"
    assert can_send_messages(chat) is True


def test_normalize_messages_preserves_order_and_fields():
    raw = [
        {"role": "user", "content": "What is revenue?", "timestamp": "2024-01-01T00:00:00Z"},
        {
            "role": "assistant",
            "content": "Revenue was $10M.",
            "timestamp": "2024-01-01T00:00:01Z",
            "sources": [{"page": 1, "preview": "Revenue..."}],
        },
        {"role": "system", "content": "ignored"},
        {"role": "user", "content": "What about last year?", "timestamp": "2024-01-01T00:00:02Z"},
        {
            "role": "assistant",
            "content": "Prior year revenue was $8M.",
            "insightType": "summary",
        },
    ]

    messages = normalize_messages(raw)
    assert len(messages) == 4
    assert messages[0]["content"] == "What is revenue?"
    assert messages[1]["sources"][0]["page"] == 1
    assert messages[3]["insightType"] == "summary"

