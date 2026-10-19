"""Task 1.1.7: the founder can delete a conversation.

A conversation hidden after six idle hours answers 410 'expired', not 404, so
the screen keeps its id and can still delete what the server holds (R107).
Delete waits for a running turn, and once it has run no background job can
start or store results for that conversation (R173). The Redis side (R114) is
in tests/unit/test_redis_layer.py.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from app.agents import ideation as agent
from app.agents import store
from app.agents.jobs import FAILED, LATEST, Board, board
from app.agents.results import KEEP, MemoryResults
from app.core.config import get_settings
from app.routers import ideation as router
from httpx import AsyncClient

URL = "/api/v1/ideation/agent/sessions"


# `client` is the shared fixture in tests/conftest.py: a fresh app per test, so
# these requests do not count against the shared app's rate limit.


@pytest.fixture(autouse=True)
def mem(monkeypatch):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")
    m = store.MemoryStore()
    store.set_store(m)
    yield m
    store.set_store(None)


async def _start(client: AsyncClient) -> tuple[str, str]:
    r = await client.post(URL, json={"name": "Kavya"})
    sid = r.json()["session_id"]
    return sid, f"{URL}/{sid}"


def _age(mem: store.MemoryStore, sid: str, by: timedelta) -> None:
    doc = json.loads(mem._docs[sid])
    doc["updated_at"] = (datetime.now(UTC) - by).isoformat()
    mem._docs[sid] = json.dumps(doc)


# ---- R107: a hidden conversation is 'expired', and can still be deleted --------------


async def test_an_idle_conversation_is_expired_not_missing(client, mem):
    sid, base = await _start(client)
    _age(mem, sid, timedelta(hours=7))

    r = await client.get(base)
    assert r.status_code == 410 and "deleted" in json.dumps(r.json())
    turn = await client.post(f"{base}/turns", json={"text": "a nurse alert device"})
    assert turn.status_code == 410
    assert (await client.get(f"{base}/notices")).status_code == 410

    # the founder can still erase it
    assert (await client.delete(base)).status_code == 204
    assert sid not in mem._docs
    assert (await client.get(base)).status_code == 404
    assert (await client.delete(base)).status_code == 404


async def test_an_unknown_conversation_is_still_404(client):
    assert (await client.get(f"{URL}/{'a' * 32}")).status_code == 404


async def test_stores_tell_hidden_from_missing(mem):
    s, _ = agent.new_session("Kavya")
    await mem.create(s)
    _age(mem, s.id, timedelta(hours=7))
    assert await mem.get(s.id) is None
    hidden = await mem.get(s.id, include_expired=True)
    assert hidden is not None and hidden.id == s.id
    assert await mem.get("b" * 32, include_expired=True) is None


# ---- R173: delete takes the turn lock; nothing comes back after it -------------------


async def test_delete_waits_for_a_running_turn(client, mem):
    sid, base = await _start(client)
    lock = router._turn_locks.setdefault(sid, asyncio.Lock())
    await lock.acquire()  # a turn is running
    deleting = asyncio.create_task(client.delete(base))
    await asyncio.sleep(0.05)
    assert not deleting.done() and sid in mem._docs  # waits for the turn to finish
    lock.release()
    assert (await deleting).status_code == 204
    assert sid not in mem._docs and sid not in router._turn_locks


async def test_no_job_starts_or_stores_results_after_delete(client):
    sid, base = await _start(client)
    assert (await client.delete(base)).status_code == 204

    ran = []

    async def work():
        ran.append(1)
        return {"ok": True}

    job = board.start(sid, "research", work)
    assert not await board.wait(job, 0.1) and job.state == FAILED
    assert ran == [] and board.running(sid, "research") is None
    await board.results.put(sid, LATEST, "research", {"ok": True})  # a late write
    assert await board.take(sid, "research") is None


async def test_a_job_that_finishes_after_forget_writes_nothing():
    b = Board()
    gate = asyncio.Event()

    async def stubborn():
        with contextlib.suppress(asyncio.CancelledError):
            await gate.wait()  # work that ignores the cancel and finishes anyway
        return {"ok": True}

    b.start("sess-late", "council", stubborn)
    await asyncio.sleep(0)
    await b.forget("sess-late")
    await asyncio.sleep(0.01)
    assert await b.take("sess-late", "council") is None


async def test_the_notices_stream_ends_when_the_conversation_is_deleted(client):
    sid, base = await _start(client)

    async def listen():
        async with client.stream("GET", f"{base}/notices") as r:
            return [ln async for ln in r.aiter_lines() if ln.startswith("event:")]

    listening = asyncio.create_task(listen())
    await asyncio.sleep(0.05)
    assert (await client.delete(base)).status_code == 204
    assert await asyncio.wait_for(listening, 2) == []


async def test_old_results_and_finished_jobs_are_pruned(monkeypatch):
    results = MemoryResults()
    await results.put("sess-old", LATEST, "research", {"n": 1})
    at, doc = results._rows[("sess-old", LATEST, "research")]
    results._rows[("sess-old", LATEST, "research")] = (at - KEEP - timedelta(minutes=1), doc)
    await results.put("sess-new", LATEST, "research", {"n": 2})
    assert await results.get("sess-old", LATEST, "research") is None
    assert await results.get("sess-new", LATEST, "research") == {"n": 2}

    b = Board()

    async def work():
        return {"ok": True}

    old = b.start("sess-old", "council", work)
    await b.wait(old, 1)
    old.finished = datetime.now(UTC) - KEEP - timedelta(minutes=1)
    b.start("sess-new", "council", work)
    assert ("sess-old", "council") not in b.jobs and ("sess-new", "council") in b.jobs


async def test_forgotten_sessions_are_remembered_only_for_a_while():
    results = MemoryResults()
    await results.delete_session("sess-x")
    assert results.forgotten("sess-x")
    results._gone["sess-x"] -= KEEP + timedelta(minutes=1)
    assert not results.forgotten("sess-x") and "sess-x" not in results._gone
