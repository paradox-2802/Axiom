from httpx import AsyncClient

from tests.conftest import auth_headers, create_chat, signup_user


async def test_create_list_and_history(client: AsyncClient):
    signup = await signup_user(client, email="chat-user@example.com")
    token = signup["token"]

    created = await create_chat(client, token, chat_id="session-1", title="New Chat")
    assert created["chatId"] == "session-1"
    assert created["documentUploaded"] is False
    assert created["ingestionStatus"] == "pending"
    assert created["messages"] == []

    listed = await client.get("/chat/list", headers=auth_headers(token))
    assert listed.status_code == 200
    chats = listed.json()
    assert len(chats) == 1
    assert chats[0]["id"] == "session-1"
    assert chats[0]["documentUploaded"] is False

    history = await client.get("/chat/history/session-1", headers=auth_headers(token))
    assert history.status_code == 200
    body = history.json()
    assert body["chatId"] == "session-1"
    assert body["documentLocked"] is False


async def test_chat_blocked_without_ready_document(client: AsyncClient):
    signup = await signup_user(client, email="gate-user@example.com")
    token = signup["token"]
    await create_chat(client, token, chat_id="gate-chat")

    response = await client.post(
        "/chat/",
        headers=auth_headers(token),
        json={"chatId": "gate-chat", "message": "What is revenue?"},
    )
    assert response.status_code == 400
    assert "upload" in response.json()["error"].lower()


async def test_chat_blocked_while_processing(client: AsyncClient, mock_enqueue_pdf_job):
    signup = await signup_user(client, email="processing-user@example.com")
    token = signup["token"]
    await create_chat(client, token, chat_id="processing-chat")

    upload = await client.post(
        "/upload",
        headers=auth_headers(token),
        data={"chatId": "processing-chat"},
        files={"pdf": ("report.pdf", b"%PDF-1.4\n%EOF", "application/pdf")},
    )
    assert upload.status_code == 200
    assert upload.json()["ingestionStatus"] == "processing"

    response = await client.post(
        "/chat/",
        headers=auth_headers(token),
        json={"chatId": "processing-chat", "message": "Summarize this report"},
    )
    assert response.status_code == 400


async def test_legacy_chat_with_messages_can_post(client: AsyncClient):
    from unittest.mock import patch

    from bson import ObjectId

    import core.database as database
    from utils.response import sse_event

    async def fake_stream(*_args, **_kwargs):
        yield sse_event({"content": "Legacy response"})
        yield sse_event({"done": True})

    signup = await signup_user(client, email="legacy-user@example.com")
    token = signup["token"]
    user_id = signup["user"]["id"]

    await database._db.chats.insert_one(
        {
            "chatId": "legacy-chat",
            "userId": ObjectId(user_id),
            "title": "Legacy Session",
            "messages": [{"role": "user", "content": "Hello"}],
            "documentUploaded": False,
            "documentLocked": False,
            "ingestionStatus": "pending",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        }
    )

    with patch("routers.chat.stream_chat_response", side_effect=fake_stream):
        response = await client.post(
            "/chat/",
            headers=auth_headers(token),
            json={"chatId": "legacy-chat", "message": "Follow up question"},
        )
    assert response.status_code == 200
