import os

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter

from core.config import get_settings
from core.rate_limit import create_limiter, ip_rate_limit_key
from tests.conftest import _test_close_db, _test_connect_db


@pytest.fixture
async def limited_app_client():
    limiter = Limiter(
        key_func=ip_rate_limit_key,
        storage_uri="memory://",
        enabled=True,
    )
    app = FastAPI()
    app.state.limiter = limiter

    @app.post("/login")
    @limiter.limit("2/minute", key_func=ip_rate_limit_key)
    async def login(request: Request):
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def redis_down_client(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "redis")
    monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
    monkeypatch.setenv("REDIS_PORT", "59999")
    get_settings.cache_clear()

    from core import rate_limit as rate_limit_module

    rate_limit_module.limiter = create_limiter()

    import importlib
    import main

    importlib.reload(main)
    main.app.state.limiter = rate_limit_module.limiter

    await _test_connect_db(os.environ["MONGODB_URI"])
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    await _test_close_db()


async def test_ip_rate_limit_returns_429(limited_app_client: AsyncClient):
    for _ in range(2):
        response = await limited_app_client.post("/login")
        assert response.status_code == 200

    response = await limited_app_client.post("/login")
    assert response.status_code == 429


async def test_auth_works_when_redis_is_unavailable(redis_down_client: AsyncClient):
    response = await redis_down_client.post(
        "/auth/signup",
        json={
            "name": "Redis Down",
            "email": "redisdown@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["refreshToken"]
    assert body["user"]["email"] == "redisdown@example.com"
