from httpx import AsyncClient

from tests.conftest import MINIMAL_PDF, auth_headers, create_chat, signup_user


async def test_upload_requires_authentication(client: AsyncClient):
    response = await client.post(
        "/upload",
        data={"chatId": "chat-1"},
        files={"pdf": ("report.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert response.status_code == 401


async def test_upload_success_queues_processing(
    client: AsyncClient,
    mock_enqueue_pdf_job,
):
    signup = await signup_user(client, email="upload-user@example.com")
    token = signup["token"]
    await create_chat(client, token, chat_id="upload-chat")

    response = await client.post(
        "/upload",
        headers=auth_headers(token),
        data={"chatId": "upload-chat"},
        files={"pdf": ("Infosys FY2024.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["ingestionStatus"] == "processing"
    assert body["documentName"] == "Infosys FY2024.pdf"
    assert body["vectorCollection"] == "axiom_upload-chat"
    mock_enqueue_pdf_job.assert_awaited_once()

    history = await client.get("/chat/history/upload-chat", headers=auth_headers(token))
    chat = history.json()
    assert chat["documentUploaded"] is True
    assert chat["documentLocked"] is True
    assert chat["ingestionStatus"] == "processing"
    assert chat["title"] == "Infosys FY2024"


async def test_upload_conflict_when_document_already_exists(
    client: AsyncClient,
    mock_enqueue_pdf_job,
):
    signup = await signup_user(client, email="conflict-user@example.com")
    token = signup["token"]
    await create_chat(client, token, chat_id="locked-chat")

    first = await client.post(
        "/upload",
        headers=auth_headers(token),
        data={"chatId": "locked-chat"},
        files={"pdf": ("first.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert first.status_code == 200

    second = await client.post(
        "/upload",
        headers=auth_headers(token),
        data={"chatId": "locked-chat"},
        files={"pdf": ("second.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert second.status_code == 409
    body = second.json()
    assert body["success"] is False
    assert "already has an uploaded document" in body["message"]


async def test_upload_chat_not_found(client: AsyncClient, mock_enqueue_pdf_job):
    signup = await signup_user(client, email="missing-chat@example.com")
    token = signup["token"]

    response = await client.post(
        "/upload",
        headers=auth_headers(token),
        data={"chatId": "does-not-exist"},
        files={"pdf": ("report.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert response.status_code == 404
    mock_enqueue_pdf_job.assert_not_awaited()


async def test_upload_rejects_non_pdf(client: AsyncClient):
    signup = await signup_user(client, email="bad-file@example.com")
    token = signup["token"]
    await create_chat(client, token, chat_id="bad-file-chat")

    response = await client.post(
        "/upload",
        headers=auth_headers(token),
        data={"chatId": "bad-file-chat"},
        files={"pdf": ("notes.pdf", b"plain text", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid PDF file"
