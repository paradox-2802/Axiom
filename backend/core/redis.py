from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from core.config import Settings, get_settings

_pool: ArqRedis | None = None


def get_redis_settings(settings: Settings | None = None) -> RedisSettings:
    settings = settings or get_settings()
    return RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT)


async def get_redis_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(get_redis_settings())
    return _pool


async def close_redis_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
    _pool = None
