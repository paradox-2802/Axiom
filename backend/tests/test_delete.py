from httpx import AsyncClient

from tests.conftest import auth_headers, create_chat, signup_user


async def test_delete_chat_removes_session(
    client: AsyncClient,
    mock_delete_vector_collection,
):
    signup = await signup_user(client, email="delete-user@example.com")
    token = signup["token"]
    await create_chat(client, token, chat_id="delete-chat")

    deleted = await client.delete("/chat/delete-chat", headers=auth_headers(token))
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True

    history = await client.get("/chat/history/delete-chat", headers=auth_headers(token))
    assert history.status_code == 200
    assert history.json()["messages"] == []

    listed = await client.get("/chat/list", headers=auth_headers(token))
    assert listed.json() == []


async def test_delete_chat_not_found(client: AsyncClient, mock_delete_vector_collection):
    signup = await signup_user(client, email="delete-missing@example.com")
    token = signup["token"]

    response = await client.delete("/chat/missing-chat", headers=auth_headers(token))
    assert response.status_code == 404
    assert response.json()["success"] is False
    mock_delete_vector_collection.assert_not_called()


async def test_delete_chat_cleans_up_uploaded_document_resources(
    client: AsyncClient,
    mock_enqueue_pdf_job,
    mock_delete_vector_collection,
):
    from tests.conftest import MINIMAL_PDF

    signup = await signup_user(client, email="delete-upload@example.com")
    token = signup["token"]
    await create_chat(client, token, chat_id="delete-upload-chat")

    upload = await client.post(
        "/upload",
        headers=auth_headers(token),
        data={"chatId": "delete-upload-chat"},
        files={"pdf": ("report.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200

    deleted = await client.delete(
        "/chat/delete-upload-chat",
        headers=auth_headers(token),
    )
    assert deleted.status_code == 200
    mock_delete_vector_collection.assert_called()
