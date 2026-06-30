"""
Idempotent migration: add session-scoped document fields to existing chat documents.

Run from backend directory:
    python scripts/migrate_chats.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient

from core.config import get_settings
from core.logging_config import setup_logging
from services.chat_service import DEFAULT_DOCUMENT_FIELDS

logger = logging.getLogger(__name__)


async def migrate() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client.get_default_database()
    chats = db["chats"]

    updated = 0
    async for chat in chats.find({}):
        missing = {
            key: value
            for key, value in DEFAULT_DOCUMENT_FIELDS.items()
            if key not in chat
        }
        if not missing:
            continue
        await chats.update_one({"_id": chat["_id"]}, {"$set": missing})
        updated += 1

    logger.info("Migration complete. Updated %s chat document(s).", updated)
    client.close()


if __name__ == "__main__":
    setup_logging()
    asyncio.run(migrate())
