"""The session copy's put script against a real Redis (R114).

tests/unit/test_redis_layer.py mirrors the script in Python; this runs the Lua
itself. Requires a reachable Redis (REDIS_URL); skipped when there is none.
"""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
from app.agents.ideation import new_session
from app.agents.store import CachedStore, MemoryStore
from app.core.config import get_settings

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def redis():
    url = get_settings().redis_url
    if not url:
        pytest.skip("no REDIS_URL")
    from redis import asyncio as aioredis

    client = aioredis.from_url(url, socket_connect_timeout=0.5, decode_responses=True)
    try:
        await client.ping()
    except Exception as exc:  # pragma: no cover - infra-dependent
        pytest.skip(f"redis unavailable: {exc}")
    yield client
    await client.close()


async def test_the_script_refuses_older_copies_and_deleted_sessions(redis):
    store = CachedStore(MemoryStore(), redis)
    s, _ = new_session()
    key, gone = f"sess:{s.id}", f"sess:gone:{s.id}"
    try:
        await store.create(s)  # version 1
        await store.save(s)  # version 2
        stale = new_session()[0]
        stale.id, stale.version = s.id, 1
        await store._put(stale)
        assert json.loads(await redis.get(key))["version"] == 2

        assert await store.delete(s.id)
        assert await redis.get(key) is None and await redis.ttl(gone) > 0
        await store._put(s)  # a read that loaded the row before the delete
        assert await redis.get(key) is None
    finally:
        await redis.delete(key, gone)
