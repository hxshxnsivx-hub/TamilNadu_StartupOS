"""Unit tests for the Embedding Service (deterministic offline provider)."""

import pytest
from app.services.embeddings import (
    EmbeddingProvider,
    EmbeddingService,
    HashEmbeddingProvider,
)


@pytest.fixture
def service():
    return EmbeddingService(HashEmbeddingProvider(dim=1024))


async def test_embedding_shape_and_norm(service):
    v = await service.embed_one("AI healthcare startup", kind="passage")
    assert len(v) == 1024
    # provider L2-normalises → unit length
    import numpy as np

    assert np.isclose(np.linalg.norm(v), 1.0, atol=1e-6)


async def test_deterministic(service):
    a = await service.embed_one("handloom weaving cooperative")
    b = await service.embed_one("handloom weaving cooperative")
    assert a == b


async def test_query_and_passage_differ(service):
    q = await service.embed_one("solar irrigation", kind="query")
    p = await service.embed_one("solar irrigation", kind="passage")
    assert q != p  # asymmetric encoding


async def test_cosine_bounds(service):
    a = await service.embed_one("agritech drone")
    assert EmbeddingService.cosine_similarity(a, a) == pytest.approx(1.0, abs=1e-6)
    b = await service.embed_one("fintech lending")
    sim = EmbeddingService.cosine_similarity(a, b)
    assert -1.0 <= sim <= 1.0


async def test_batch_length_matches(service):
    texts = ["one", "two", "three", "four"]
    out = await service.embed_batch(texts)
    assert len(out) == len(texts)
    assert all(len(v) == 1024 for v in out)


class _CountingProvider(EmbeddingProvider):
    def __init__(self):
        self.dim = 8
        self.model = "count"
        self.calls = 0

    async def embed(self, texts, kind):
        self.calls += 1
        return [[float(len(t))] * 8 for t in texts]


class _DictCache:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value):
        self.store[key] = value


async def test_cache_prevents_recompute():
    provider = _CountingProvider()
    svc = EmbeddingService(provider, cache=_DictCache())
    await svc.embed_one("repeat me")
    await svc.embed_one("repeat me")
    assert provider.calls == 1  # second call served from cache
