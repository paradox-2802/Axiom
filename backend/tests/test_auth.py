from httpx import AsyncClient

from tests.conftest import auth_headers, signup_user


async def test_signup_login_and_refresh(client: AsyncClient):
    signup = await signup_user(client, email="alice@example.com")
    assert signup["token"]
    assert signup["refreshToken"]
    assert signup["user"]["email"] == "alice@example.com"

    login = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    login_data = login.json()
    assert login_data["token"]

    refresh = await client.post(
        "/auth/refresh",
        json={"refreshToken": login_data["refreshToken"]},
    )
    assert refresh.status_code == 200
    refreshed = refresh.json()
    assert refreshed["token"]
    assert refreshed["refreshToken"]
    assert refreshed["user"]["email"] == "alice@example.com"


async def test_signup_duplicate_email(client: AsyncClient):
    await signup_user(client, email="dup@example.com")
    response = await client.post(
        "/auth/signup",
        json={"name": "Other", "email": "dup@example.com", "password": "password123"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "User already exists"


async def test_login_invalid_credentials(client: AsyncClient):
    await signup_user(client, email="bob@example.com")
    response = await client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid credentials"


async def test_refresh_invalid_token(client: AsyncClient):
    response = await client.post(
        "/auth/refresh",
        json={"refreshToken": "not-a-valid-token"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid refresh token"


async def test_protected_route_requires_auth(client: AsyncClient):
    response = await client.get("/chat/list")
    assert response.status_code == 401
    assert response.json()["error"] == "Unauthorized"

    signup = await signup_user(client, email="carol@example.com")
    authed = await client.get("/chat/list", headers=auth_headers(signup["token"]))
    assert authed.status_code == 200
    assert authed.json() == []
