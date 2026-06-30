from services.chat_service import (
    can_send_messages,
    get_retrieval_collection,
    is_legacy_chat,
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
