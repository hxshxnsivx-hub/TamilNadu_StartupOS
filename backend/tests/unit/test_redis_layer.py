"""The optional Redis layer: research cache, source pauses, daily caps, live sessions,
translation and embedding caches.

A small in-memory stand-in implements the few Redis commands used, so these
tests run without a server. Every feature must also work with Redis absent or
failing.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from app.agents.ideation import new_session
from app.agents.store import CachedStore, MemoryStore, VersionConflict
from app.core.config import get_settings
from app.core.redis import RedisCache, set_redis
from app.research import sources
from app.services.embeddings import EmbeddingService, HashEmbeddingProvider
from app.services.translation import PassthroughTranslationProvider, TranslationService


class FakeRedis:
    def __init__(self, broken: bool = False) -> None:
        self.data: dict[str, str] = {}
        self.ttl: dict[str, int] = {}
        self.broken = broken

    def _check(self):
        if self.broken:
            raise ConnectionError("redis down")

    async def get(self, k):
        self._check()
        return self.data.get(k)

    async def set(self, k, v, ex=None):
        self._check()
        self.data[k] = v
        if ex:
            self.ttl[k] = ex

    async def delete(self, k):
        self._check()
        self.data.pop(k, None)

    async def exists(self, k):
        self._check()
        return int(k in self.data)

    async def incr(self, k):
        self._check()
        self.data[k] = str(int(self.data.get(k, "0")) + 1)
        return int(self.data[k])

    async def expire(self, k, s):
        self._check()
        self.ttl[k] = s


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "openalex_api_key", "")
    return sources.Cache(tmp_path, 7)


def _client(calls: list, status: int = 200, headers: dict | None = None):
    def handle(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        if status != 200:
            return httpx.Response(status, text="slow down", headers=headers or {})
        return httpx.Response(200, json={"meta": {"count": 42}})

    return httpx.AsyncClient(transport=httpx.MockTransport(handle))


def _count(cache, calls, **kw):
    async def go():
        async with _client(calls, **kw) as c:
            return await sources.paper_count(c, "EEG", cache)

    return asyncio.run(go())


def test_redis_serves_research_without_a_request(cache):
    r = FakeRedis()
    set_redis(r)
    calls: list = []
    assert _count(cache, calls).total == 42 and len(calls) == 1
    assert any(k.startswith("rs:") for k in r.data)  # stored in Redis too
    for p in cache.root.glob("*.json"):
        p.unlink()  # disk gone: Redis alone answers
    assert _count(cache, calls).total == 42 and len(calls) == 1


def test_disk_hit_is_copied_into_redis(cache):
    calls: list = []
    _count(cache, calls)  # no Redis: disk only
    r = FakeRedis()
    set_redis(r)
    _count(cache, calls)
    assert len(calls) == 1 and any(k.startswith("rs:") for k in r.data)


def test_a_429_pauses_the_source_for_everyone(cache):
    r = FakeRedis()
    set_redis(r)
    calls: list = []
    first = _count(cache, calls, status=429, headers={"Retry-After": "120"})
    assert first.status == "budget_exhausted" and len(calls) == 1
    assert r.ttl["rs:neg:openalex"] == 120
    again = _count(cache, calls)  # source is fine again, but we promised to wait
    assert again.status == "budget_exhausted" and len(calls) == 1


def test_pause_works_without_redis(cache):
    calls: list = []
    _count(cache, calls, status=429, headers={"Retry-After": "30"})
    assert _count(cache, calls).status == "budget_exhausted" and len(calls) == 1


def test_daily_cap_stops_requests(cache, monkeypatch):
    monkeypatch.setattr(get_settings(), "research_daily_limit", 2)
    set_redis(FakeRedis())
    calls: list = []

    async def go():
        async with _client(calls) as c:
            return [
                await sources.paper_count(c, f"EEG {i}", cache) for i in range(3)
            ]  # three different queries, so no cache hits

    out = asyncio.run(go())
    assert [o.status for o in out] == ["ok", "ok", "budget_exhausted"] and len(calls) == 2


def test_broken_redis_never_breaks_a_search(cache):
    set_redis(FakeRedis(broken=True))
    calls: list = []
    assert _count(cache, calls).total == 42
    assert _count(cache, calls).total == 42 and len(calls) == 1  # disk cache still works


# ---- live sessions ---------------------------------------------------------------


def test_cached_store_reads_through_and_writes_the_database_first():
    inner, r = MemoryStore(), FakeRedis()
    store = CachedStore(inner, r)
    s, _ = new_session("Kavya")
    asyncio.run(store.create(s))
    assert json.loads(r.data[f"sess:{s.id}"])["version"] == 1
    assert r.ttl[f"sess:{s.id}"] == 6 * 3600
    r.data.clear()  # copy lost: the database still has it
    back = asyncio.run(store.get(s.id))
    assert back is not None and f"sess:{s.id}" in r.data


def test_a_refused_save_drops_the_stale_copy():
    inner, r = MemoryStore(), FakeRedis()
    store = CachedStore(inner, r)
    s, _ = new_session()
    asyncio.run(store.create(s))
    a, b = asyncio.run(store.get(s.id)), asyncio.run(store.get(s.id))
    asyncio.run(store.save(a))
    with pytest.raises(VersionConflict):
        asyncio.run(store.save(b))
    assert f"sess:{s.id}" not in r.data  # next read goes to the database
    assert asyncio.run(store.get(s.id)).version == a.version


def test_cached_store_survives_a_broken_redis():
    store = CachedStore(MemoryStore(), FakeRedis(broken=True))
    s, _ = new_session()
    asyncio.run(store.create(s))
    asyncio.run(store.save(asyncio.run(store.get(s.id))))
    assert asyncio.run(store.delete(s.id))


# ---- translation and embedding caches (Tasks 1.5.5, 1.6.4) -------------------------

WEEK = 7 * 86400


class _CountingTranslator(PassthroughTranslationProvider):
    def __init__(self):
        self.calls = 0

    async def translate(self, text, src, tgt):
        self.calls += 1
        return f"[{tgt}] {text}"


class _CountingEmbedder(HashEmbeddingProvider):
    def __init__(self):
        super().__init__(dim=16)
        self.calls = 0

    async def embed(self, texts, kind):
        self.calls += 1
        return await super().embed(texts, kind)


def _translate(provider, text="hello world", src="en", tgt="ta"):
    svc = TranslationService(provider, cache=RedisCache(WEEK))
    return asyncio.run(svc.translate(text, src, tgt))


def _embed(provider, text="cold storage for Salem mangoes"):
    svc = EmbeddingService(provider, cache=RedisCache(WEEK))
    return asyncio.run(svc.embed_one(text))


def test_translation_is_cached_in_redis_for_a_week():
    r = FakeRedis()
    set_redis(r)
    p = _CountingTranslator()
    first = _translate(p)
    (key,) = r.data
    assert key.startswith("tr:passthrough:en:ta:") and r.ttl[key] == WEEK
    assert _translate(p) == first and p.calls == 1  # a fresh service, same Redis
    _translate(p, tgt="hi")
    _translate(p, text="hello there")
    assert p.calls == 3 and len(r.data) == 3  # pair and text are both in the key


def test_embedding_is_cached_in_redis_for_a_week():
    r = FakeRedis()
    set_redis(r)
    p = _CountingEmbedder()
    first = _embed(p)
    (key,) = r.data
    assert key.startswith("emb:hash-dev:16:passage:") and r.ttl[key] == WEEK
    assert _embed(p) == first and p.calls == 1  # the vector round-trips exactly
    _embed(p, text="something else")
    assert p.calls == 2


def test_embedding_sizes_never_share_a_cache_entry():
    set_redis(FakeRedis())
    small, large = _CountingEmbedder(), _CountingEmbedder()
    large.dim = 32  # same model name, other EMBEDDING_DIM
    assert len(_embed(small)) == 16
    assert len(_embed(large)) == 32 and large.calls == 1


def test_caches_work_without_redis():
    tp, ep = _CountingTranslator(), _CountingEmbedder()
    assert _translate(tp) == _translate(tp) and tp.calls == 2  # no cache, no failure
    assert _embed(ep) == _embed(ep) and ep.calls == 2


def test_broken_redis_never_breaks_translation_or_embedding():
    set_redis(FakeRedis(broken=True))
    assert _translate(_CountingTranslator()) == "[ta] hello world"
    assert len(_embed(_CountingEmbedder())) == 16


def test_default_services_use_the_redis_cache():
    from app.services.embeddings import get_embedding_service
    from app.services.translation import get_translation_service

    for svc in (get_translation_service(), get_embedding_service()):
        assert isinstance(svc.cache, RedisCache) and svc.cache.ttl == WEEK
