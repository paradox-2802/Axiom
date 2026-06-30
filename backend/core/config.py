from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MONGODB_URI: str
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str = ""
    JWT_ACCESS_EXPIRE_DAYS: int = 7
    JWT_REFRESH_EXPIRE_DAYS: int = 30
    HUGGINGFACE_API_KEY: str
    QDRANT_URL: str = "http://localhost:6333"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    PORT: int = 8000

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    QDRANT_COLLECTION: str = "axiom-documents"
    QDRANT_COLLECTION_PREFIX: str = "axiom_"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHAT_MODEL: str = "deepseek-ai/DeepSeek-R1:novita"
    RETRIEVAL_K: int = 5
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_BYTES: int = 200 * 1024 * 1024

    CHAT_HISTORY_LIMIT: int = 8
    CHAT_TITLE_MAX_LENGTH: int = 50
    CHAT_MAX_TOKENS: int = 500
    CHAT_TEMPERATURE: float = 0.3
    SOURCE_PREVIEW_LENGTH: int = 200
    INGESTION_BATCH_SIZE: int = 50
    HF_EMBEDDING_TIMEOUT: float = 120.0
    HF_EMBEDDING_RETRY_ATTEMPTS: int = 5
    HF_CHAT_TIMEOUT: float = 120.0
    ANALYSIS_MAX_TOKENS: int = 2000
    ANALYSIS_MODEL: str = ""

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE: str = "redis"
    REDIS_RATE_LIMIT_DB: int = 1
    RATE_LIMIT_AUTH: str = "20/minute"
    RATE_LIMIT_UPLOAD: str = "10/hour"
    RATE_LIMIT_CHAT: str = "60/minute"

    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
