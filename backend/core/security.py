from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from core.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    payload: dict[str, Any],
    secret: str,
    expires_delta: timedelta,
) -> str:
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(data, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=["HS256"])


def _refresh_secret() -> str:
    settings = get_settings()
    return settings.JWT_REFRESH_SECRET or settings.JWT_SECRET


def create_user_tokens(user_id: str) -> tuple[str, str]:
    settings = get_settings()
    access = create_access_token(
        {"id": user_id, "type": "access"},
        settings.JWT_SECRET,
        timedelta(days=settings.JWT_ACCESS_EXPIRE_DAYS),
    )
    refresh = create_access_token(
        {"id": user_id, "type": "refresh"},
        _refresh_secret(),
        timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
    )
    return access, refresh


def verify_user_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = decode_token(token, settings.JWT_SECRET)
        token_type = payload.get("type", "access")
        if token_type != "access":
            return None
        user_id = payload.get("id")
        return str(user_id) if user_id else None
    except JWTError:
        return None


def verify_refresh_token(token: str) -> str | None:
    try:
        payload = decode_token(token, _refresh_secret())
        if payload.get("type") != "refresh":
            return None
        user_id = payload.get("id")
        return str(user_id) if user_id else None
    except JWTError:
        return None
