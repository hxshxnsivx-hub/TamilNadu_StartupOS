"""The optional Redis layer: research cache, source pauses, daily caps, live sessions.

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
from app.core.redis import set_redis
from app.research import sources


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

    def register_script(self, lua):
        """The session put script (store._PUT_IF_NEWER), mirrored in Python: no
        Lua here. tests/integration/test_redis_sessions.py runs the real one."""

        async def run(keys, args):
            self._check()
            key, gone = keys
            doc, version, ttl = args
            if gone in self.data:
                return 0
            cur = self.data.get(key)
            if cur is not None and json.loads(cur).get("version", 0) >= int(version):
                return 0
            self.data[key] = doc
            self.ttl[key] = int(ttl)
            return 1

        return run


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


class SlowStore(MemoryStore):
    """A database read that takes a while (the R114 probe)."""

    async def get(self, session_id, include_expired=False):
        s = await super().get(session_id, include_expired)
        await asyncio.sleep(0.05)
        return s


def test_a_read_in_flight_cannot_bring_back_a_deleted_session():
    inner, r = SlowStore(), FakeRedis()
    store = CachedStore(inner, r)
    s, _ = new_session()
    asyncio.run(inner.create(s))  # in the database, not in Redis

    async def race():
        reading = asyncio.create_task(store.get(s.id))  # reads the row, then fills Redis
        await asyncio.sleep(0.01)
        assert await store.delete(s.id)
        await reading
        return await store.get(s.id)

    assert asyncio.run(race()) is None
    assert f"sess:{s.id}" not in r.data
    assert r.ttl[f"sess:gone:{s.id}"] == 6 * 3600  # the tombstone outlives any copy


def test_a_slow_read_cannot_overwrite_a_newer_copy():
    inner, r = SlowStore(), FakeRedis()
    store = CachedStore(inner, r)
    s, _ = new_session()
    asyncio.run(store.create(s))

    async def race():
        r.data.clear()  # copy lost: the next read goes to the database
        reading = asyncio.create_task(store.get(s.id))  # loads version 1
        await asyncio.sleep(0.01)
        fresh = await inner.get(s.id)
        await store.save(fresh)  # version 2, written to Redis
        await reading  # its version 1 must not replace version 2
        return fresh.version

    newest = asyncio.run(race())
    assert json.loads(r.data[f"sess:{s.id}"])["version"] == newest == 2


def test_delete_removes_the_row_before_the_copy():
    order: list[str] = []

    class Inner(MemoryStore):
        async def delete(self, session_id):
            order.append("row")
            return await super().delete(session_id)

    class Watch(FakeRedis):
        async def set(self, k, v, ex=None):
            if k.startswith("sess:gone:"):
                order.append("tombstone")
            await super().set(k, v, ex)

    store = CachedStore(Inner(), Watch())
    s, _ = new_session()
    asyncio.run(store.create(s))
    assert asyncio.run(store.delete(s.id))
    assert order == ["row", "tombstone"]


def test_cached_store_tells_hidden_from_missing():
    inner, r = MemoryStore(), FakeRedis()
    store = CachedStore(inner, r)
    s, _ = new_session()
    asyncio.run(store.create(s))
    doc = json.loads(inner._docs[s.id])
    doc["updated_at"] = "2020-01-01T00:00:00+00:00"
    inner._docs[s.id] = json.dumps(doc)
    r.data.clear()
    assert asyncio.run(store.get(s.id)) is None
    assert asyncio.run(store.get(s.id, include_expired=True)).id == s.id
    assert f"sess:{s.id}" not in r.data  # a hidden session is never copied
