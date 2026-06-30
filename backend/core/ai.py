import json
import logging
import time
from collections.abc import AsyncIterator
from functools import lru_cache

import httpx
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from core.config import Settings, get_settings

logger = logging.getLogger(__name__)

HF_ROUTER_URL = "https://router.huggingface.co"
HF_CHAT_URL = f"{HF_ROUTER_URL}/v1/chat/completions"


def collection_name_for_chat(chat_id: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return f"{settings.QDRANT_COLLECTION_PREFIX}{chat_id}"


class HFRouterEmbeddings(Embeddings):
    """Hugging Face embeddings via router.huggingface.co (replaces deprecated api-inference)."""

    def __init__(self, api_key: str, model_name: str, settings: Settings) -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._settings = settings
        self._api_url = (
            f"{HF_ROUTER_URL}/hf-inference/models/"
            f"{model_name}/pipeline/feature-extraction"
        )

    def _post(self, texts: list[str]) -> list[list[float]]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        attempts = self._settings.HF_EMBEDDING_RETRY_ATTEMPTS
        timeout = self._settings.HF_EMBEDDING_TIMEOUT
        for attempt in range(attempts):
            response = httpx.post(
                self._api_url,
                headers=headers,
                json={"inputs": texts},
                timeout=timeout,
            )
            if response.status_code == 503:
                time.sleep(5 * (attempt + 1))
                continue
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and "error" in data:
                raise RuntimeError(data["error"])
            return data
        raise RuntimeError("Hugging Face embedding model is loading; try again shortly")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._post(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._post([text])[0]


class LLMProvider:
    """Abstraction over Hugging Face chat completion APIs."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._headers = {
            "Authorization": f"Bearer {self.settings.HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json",
        }

    async def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 80,
    ) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.settings.HF_CHAT_TIMEOUT) as client:
            response = await client.post(
                HF_CHAT_URL,
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    async def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                HF_CHAT_URL,
                headers=self._headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line.removeprefix("data:").strip()
                    if chunk == "[DONE]":
                        break
                    parsed = json.loads(chunk)
                    delta = parsed.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content


def get_embeddings(settings: Settings | None = None) -> HFRouterEmbeddings:
    settings = settings or get_settings()
    return HFRouterEmbeddings(
        api_key=settings.HUGGINGFACE_API_KEY,
        model_name=settings.EMBEDDING_MODEL,
        settings=settings,
    )


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.QDRANT_URL)


def close_qdrant_client() -> None:
    if get_qdrant_client.cache_info().currsize > 0:
        get_qdrant_client().close()
    get_qdrant_client.cache_clear()


def delete_vector_collection(collection_name: str) -> None:
    client = get_qdrant_client()
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)
        logger.info("Deleted vector collection %s", collection_name)


def get_vector_store(
    settings: Settings | None = None,
    collection_name: str | None = None,
) -> QdrantVectorStore:
    settings = settings or get_settings()
    collection = collection_name or settings.QDRANT_COLLECTION
    embeddings = get_embeddings(settings)
    client = get_qdrant_client()

    if client.collection_exists(collection):
        return QdrantVectorStore(
            client=client,
            collection_name=collection,
            embedding=embeddings,
        )

    QdrantVectorStore.construct_instance(
        embedding=embeddings,
        collection_name=collection,
        client_options={"url": settings.QDRANT_URL},
    )
    return QdrantVectorStore(
        client=client,
        collection_name=collection,
        embedding=embeddings,
    )


def get_llm_provider() -> LLMProvider:
    return LLMProvider()
