import os
import shutil
import tempfile
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

# Environment must be set before application imports.
_TEST_UPLOAD_DIR = tempfile.mkdtemp(prefix="axiom_test_uploads_")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/axiom_test")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-at-least-32-chars")
os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh-secret-at-least-32-chars")
os.environ.setdefault("HUGGINGFACE_API_KEY", "test-hf-key")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ["UPLOAD_DIR"] = _TEST_UPLOAD_DIR
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["RATE_LIMIT_STORAGE"] = "memory"

import core.database as database
from core.config import get_settings

get_settings.cache_clear()


async def _test_connect_db(_uri: str) -> None:
    database._client = AsyncMongoMockClient()
    database._db = database._client["axiom_test"]
    await database.ensure_indexes(database._db)


async def _test_close_db() -> None:
    if database._client is not None:
        database._client.close()
    database._client = None
    database._db = None


database.connect_db = _test_connect_db
database.close_db = _test_close_db

from main import app  # noqa: E402

MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]/Parent 2 0 R>>endobj\n"
    b"trailer<</Root 1 0 R>>\n"
    b"%%EOF"
)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    get_settings.cache_clear()
    await _test_connect_db(os.environ["MONGODB_URI"])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    await _test_close_db()


@pytest.fixture(autouse=True)
async def clean_database():
    if database._db is not None:
        await database._db.users.delete_many({})
        await database._db.chats.delete_many({})
    upload_root = get_settings().UPLOAD_DIR
    if os.path.isdir(upload_root):
        shutil.rmtree(upload_root, ignore_errors=True)
    os.makedirs(upload_root, exist_ok=True)
    yield


@pytest.fixture
def mock_enqueue_pdf_job():
    with patch("routers.upload.enqueue_pdf_job", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_delete_vector_collection():
    with patch("services.chat_service.delete_vector_collection") as mock:
        yield mock


async def signup_user(
    client: AsyncClient,
    *,
    name: str = "Test User",
    email: str = "test@example.com",
    password: str = "password123",
) -> dict:
    response = await client.post(
        "/auth/signup",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def create_chat(
    client: AsyncClient,
    token: str,
    chat_id: str = "chat-1",
    title: str = "New Chat",
) -> dict:
    response = await client.post(
        "/chat/create",
        headers=auth_headers(token),
        json={"chatId": chat_id, "title": title},
    )
    assert response.status_code == 200, response.text
    return response.json()
