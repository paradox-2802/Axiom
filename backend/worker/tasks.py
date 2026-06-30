import logging

from core.database import get_database
from core.redis import get_redis_pool
from services.chat_service import update_ingestion_status

logger = logging.getLogger(__name__)


async def process_pdf(
    ctx,
    path: str,
    filename: str,
    chat_id: str,
    vector_collection: str,
):
    from services.ingestion_service import ingest_pdf

    db = get_database()
    try:
        result = await ingest_pdf(
            path,
            filename,
            chat_id=chat_id,
            vector_collection=vector_collection,
        )
        await update_ingestion_status(db, chat_id, "completed")
        logger.info(
            "Indexed %s for chat %s (%s chunks)",
            filename,
            chat_id,
            result["chunks"],
        )
        return result
    except Exception:
        await update_ingestion_status(db, chat_id, "failed")
        logger.exception("Failed to index PDF %s for chat %s", filename, chat_id)
        raise


async def enqueue_pdf_job(
    path: str,
    filename: str,
    chat_id: str,
    vector_collection: str,
) -> None:
    redis = await get_redis_pool()
    await redis.enqueue_job(
        "process_pdf",
        path,
        filename,
        chat_id,
        vector_collection,
    )
