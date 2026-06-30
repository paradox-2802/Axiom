import logging

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import get_settings
from core.security import verify_user_token

logger = logging.getLogger(__name__)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return get_remote_address(request)


def ip_rate_limit_key(request: Request) -> str:
    return f"ip:{client_ip(request)}"


def user_rate_limit_key(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        user_id = verify_user_token(token)
        if user_id:
            return f"user:{user_id}"
    return ip_rate_limit_key(request)


def _redis_available(settings) -> bool:
    try:
        import redis

        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_RATE_LIMIT_DB,
            socket_connect_timeout=1,
        )
        client.ping()
        return True
    except Exception:
        return False


def _storage_uri() -> str:
    settings = get_settings()
    if settings.RATE_LIMIT_STORAGE == "memory":
        return "memory://"

    if not _redis_available(settings):
        logger.warning(
            "Redis unavailable at %s:%s; using in-memory rate limiting",
            settings.REDIS_HOST,
            settings.REDIS_PORT,
        )
        return "memory://"

    return (
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/"
        f"{settings.REDIS_RATE_LIMIT_DB}"
    )


def create_limiter() -> Limiter:
    settings = get_settings()
    return Limiter(
        key_func=user_rate_limit_key,
        storage_uri=_storage_uri(),
        enabled=settings.RATE_LIMIT_ENABLED,
    )


limiter = create_limiter()
