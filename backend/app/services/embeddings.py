"""Embedding Service (Task 1.6) — multilingual sentence embeddings.

Managed-API-first with a swappable provider behind one interface, so the model
can change (Cohere multilingual, a self-hosted BGE-M3 server, …) without touching
callers. A deterministic offline provider keeps unit tests and local dev running
with no network or API key.

Design notes:
- query/passage asymmetry is handled *inside* the service so callers cannot get
  it wrong (BGE-M3-style models embed queries and passages differently).
- an optional cache (Redis when it runs, a week per vector) avoids re-embedding
  identical text.
- cosine similarity assumes L2-normalised vectors; providers must normalise.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Literal, Protocol

import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import RedisCache

Kind = Literal["query", "passage"]
_MAX_BATCH = 96  # keep provider batch calls bounded
CACHE_TTL = 7 * 86400  # Task 1.6: vectors kept a week
log = get_logger("embeddings")


# ── providers ───────────────────────────────────────────────────────────────
class EmbeddingProvider(ABC):
    dim: int
    model: str

    @abstractmethod
    async def embed(self, texts: list[str], kind: Kind) -> list[list[float]]:
        """Return one L2-normalised vector per input text."""


def _l2_normalise(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline pseudo-embeddings for dev/test.

    Not semantic — but stable (same text → same vector) and correctly shaped and
    normalised, so it exercises all the plumbing (cache, similarity, storage).
    """

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim
        self.model = "hash-dev"

    async def embed(self, texts: list[str], kind: Kind) -> list[list[float]]:
        out = []
        for t in texts:
            seed = int.from_bytes(hashlib.sha256(f"{kind}:{t}".encode()).digest()[:8], "big")
            rng = np.random.default_rng(seed)
            out.append(rng.standard_normal(self.dim))
        return _l2_normalise(np.asarray(out)).tolist()


class CohereEmbeddingProvider(EmbeddingProvider):
    """Managed multilingual embeddings via Cohere embed v2 (lazy httpx call)."""

    def __init__(self, api_key: str, dim: int = 1024, model: str = "embed-multilingual-v3.0"):
        self._api_key = api_key
        self.dim = dim
        self.model = model

    async def embed(self, texts: list[str], kind: Kind) -> list[list[float]]:
        import httpx

        input_type = "search_query" if kind == "query" else "search_document"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.cohere.com/v2/embed",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self.model,
                    "texts": texts,
                    "input_type": input_type,
                    "embedding_types": ["float"],
                },
            )
            resp.raise_for_status()
            vectors = resp.json()["embeddings"]["float"]
        return _l2_normalise(np.asarray(vectors)).tolist()


# ── cache interface ──────────────────────────────────────────────────────────
class EmbeddingCache(Protocol):
    async def get(self, key: str) -> list[float] | None: ...
    async def set(self, key: str, value: list[float]) -> None: ...


# ── service ──────────────────────────────────────────────────────────────────
class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider, cache: EmbeddingCache | None = None) -> None:
        self.provider = provider
        self.cache = cache

    @property
    def dim(self) -> int:
        return self.provider.dim

    def _key(self, text: str, kind: Kind) -> str:
        digest = hashlib.sha256(text.encode()).hexdigest()
        return f"emb:{self.provider.model}:{self.provider.dim}:{kind}:{digest}"

    async def embed_one(self, text: str, kind: Kind = "passage") -> list[float]:
        return (await self.embed_batch([text], kind))[0]

    async def embed_batch(self, texts: list[str], kind: Kind = "passage") -> list[list[float]]:
        results: list[list[float] | None] = [None] * len(texts)
        misses: list[int] = []

        if self.cache is not None:
            for i, t in enumerate(texts):
                cached = await self.cache.get(self._key(t, kind))
                if cached is not None:
                    results[i] = cached
                else:
                    misses.append(i)
        else:
            misses = list(range(len(texts)))

        for start in range(0, len(misses), _MAX_BATCH):
            chunk_idx = misses[start : start + _MAX_BATCH]
            vectors = await self.provider.embed([texts[i] for i in chunk_idx], kind)
            for i, vec in zip(chunk_idx, vectors, strict=True):
                results[i] = vec
                if self.cache is not None:
                    await self.cache.set(self._key(texts[i], kind), vec)

        return [r for r in results if r is not None]

    @staticmethod
    def cosine_similarity(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
        va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom == 0.0:
            return 0.0
        return float(np.dot(va, vb) / denom)


def _select_provider() -> EmbeddingProvider:
    s = get_settings()
    if s.embedding_provider == "cohere" and s.cohere_api_key:
        return CohereEmbeddingProvider(s.cohere_api_key, dim=s.embedding_dim)
    if s.embedding_provider not in ("cohere", "hash"):
        log.warning("embeddings.unknown_provider", provider=s.embedding_provider)
    # Dev-safe default: deterministic offline embeddings when no key is configured.
    log.info("embeddings.using_hash_provider")
    return HashEmbeddingProvider(dim=s.embedding_dim)


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(_select_provider(), cache=RedisCache(CACHE_TTL))
