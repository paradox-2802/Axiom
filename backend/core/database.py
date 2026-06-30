from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db["users"].create_index("email", unique=True)
    await db["chats"].create_index(
        [("userId", ASCENDING), ("chatId", ASCENDING)],
        unique=True,
    )
    await db["chats"].create_index(
        [("userId", ASCENDING), ("updatedAt", DESCENDING)],
    )


async def connect_db(uri: str) -> None:
    global _client, _db
    _client = AsyncIOMotorClient(uri)
    _db = _client.get_default_database()
    await ensure_indexes(_db)


async def close_db() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def get_database() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database is not initialized")
    return _db


def get_db() -> AsyncIOMotorDatabase:
    return get_database()
