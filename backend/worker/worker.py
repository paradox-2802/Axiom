from dotenv import load_dotenv

load_dotenv()

from arq.connections import RedisSettings

from core.config import get_settings
from core.database import close_db, connect_db
from core.logging_config import setup_logging
from worker.tasks import process_pdf

setup_logging()

_settings = get_settings()


async def startup(_ctx) -> None:
    await connect_db(_settings.MONGODB_URI)


async def shutdown(_ctx) -> None:
    await close_db()


class WorkerSettings:
    functions = [process_pdf]
    redis_settings = RedisSettings(
        host=_settings.REDIS_HOST,
        port=_settings.REDIS_PORT,
    )
    max_jobs = 2
    on_startup = startup
    on_shutdown = shutdown
