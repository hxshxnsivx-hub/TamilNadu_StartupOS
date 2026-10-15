"""Background jobs: slow research and a slow panel enter a later turn, never block one."""

from __future__ import annotations

import asyncio
import json

import pytest
from app.agents import ideation as agent
from app.agents import tools
from app.agents.jobs import board
from app.core.config import get_settings
from httpx import AsyncClient

from tests.unit.test_ideation_agent import BCI, NOVELTY, SCAN


@pytest.fixture
def slow(monkeypatch):
    """A search that takes longer than the turn will wait."""
    calls: list[str] = []
    st = get_settings()
    monkeypatch.setattr(st, "research_wait_s", 0.05)
    monkeypatch.setattr(st, "council_wait_s", 0.05)
    monkeypatch.setattr(st, "opinion_wait_s", 0.05)

    async def slow_scan(text, *, elements=None, queries=None, client=None, private=False):
        calls.append(text)
        await asyncio.sleep(0.3)
        return SCAN

    async def fake_novelty(idea, **_kw):
        return NOVELTY

    monkeypatch.setattr("app.research.scan.scan", slow_scan)
    monkeypatch.setattr(tools.research, "scan", slow_scan)
    monkeypatch.setattr("app.research.novelty.check", fake_novelty)
    return calls


async def _turn(s, text):
    events = [ev async for ev in agent.turn_stream(s, text)]
    return events, events[-1]["data"]


def test_a_slow_search_is_announced_then_shared_on_the_next_turn(slow):
    async def go():
        s = agent.new_session("Kavya")[0]
        ev1, r1 = await _turn(s, BCI)
        kinds1 = [e["event"] for e in ev1]
        assert agent.SEARCHING in r1["reply"]  # said once, and the question still asked
        assert r1["reply"].rstrip().endswith("?")
        assert "evidence" not in kinds1 and r1["tools_used"] == []
        assert s.scan is None

        await asyncio.sleep(0.5)  # the founder answers while the search finishes
        ev2, r2 = await _turn(s, "Chennai")
        kinds2 = [e["event"] for e in ev2]
        assert kinds2.index("evidence") < kinds2.index("sentence")
        assert r2["tools_used"] == ["scan_prior_art", "check_novelty", "ask_council"]
        assert "23 clinical trials" in r2["reply"] and agent.SEARCHING not in r2["reply"]
        assert s.council is not None  # the rule panel followed the research

        _, r3 = await _turn(s, "skip")
        assert "clinical trials" not in r3["reply"]  # shared once, not every turn
        return slow

    calls = asyncio.run(go())
    assert len(calls) == 1  # one search per conversation, however many turns it took


def test_a_slow_panel_answers_a_later_turn(slow, monkeypatch):
    from app.agents import council

    real = council.convene

    async def slow_convene(*a, **kw):
        await asyncio.sleep(0.3)
        return await real(*a, **kw)

    async def go():
        s = agent.new_session("Kavya")[0]
        await _turn(s, BCI)
        await asyncio.sleep(0.5)
        await _turn(s, "Chennai")  # research and the first (rule) panel are in
        first = s.council["at"]
        monkeypatch.setattr(council, "convene", slow_convene)
        _, r = await _turn(s, "what do you think?")
        assert "still looking at it" in r["reply"] and s.council["at"] == first
        await asyncio.sleep(0.5)
        ev, r2 = await _turn(s, "skip")
        assert "council" in [e["event"] for e in ev] and s.council["at"] != first
        assert "ask_council" in r2["tools_used"]

    asyncio.run(go())


def test_the_board_runs_one_job_of_a_kind_at_a_time_and_forgets():
    async def go():
        started = []

        async def work():
            started.append(1)
            await asyncio.sleep(0.2)
            return {"ok": True}

        a = board.start("sess-board", "council", work)
        b = board.start("sess-board", "council", work)
        assert a is b  # still running: the same job
        assert await board.wait(a, 1) and await board.take("sess-board", "council") == {"ok": True}
        c = board.start("sess-board", "research", work, reuse_done=True)
        await board.wait(c, 1)
        assert board.start("sess-board", "research", work, reuse_done=True) is c
        assert len(started) == 2

        async def boom():
            raise RuntimeError("source down")

        f = board.start("sess-board", "council", boom)
        assert not await board.wait(f, 1)  # a failed job is not a result
        assert board.start("sess-board", "council", work) is not f  # and can start again

        slow_job = board.start("sess-gone", "research", work)
        await board.forget("sess-gone")
        await asyncio.sleep(0)
        assert slow_job.task.cancelled() or slow_job.task.done()
        assert await board.take("sess-gone", "research") is None

    asyncio.run(go())


async def test_the_screen_hears_when_research_finishes(client: AsyncClient, slow):
    from app.agents.store import MemoryStore, set_store

    store = MemoryStore()
    set_store(store)
    try:
        s = agent.new_session("Kavya")[0]
        await store.create(s)
        board.start(s.id, "research", agent._research_work(s))

        async with client.stream(
            "GET", f"/api/v1/ideation/agent/sessions/{s.id}/notices", params={"limit": 1}
        ) as r:
            assert r.status_code == 200
            lines = [line async for line in r.aiter_lines() if line.startswith(("event:", "data:"))]
        events = [x.split(": ", 1)[1] for x in lines if x.startswith("event:")]
        assert events == ["evidence", "novelty"]
        evidence = json.loads(lines[1].split(": ", 1)[1])
        assert evidence["trials"]["total"] == 23

        unknown = "0" * 32
        r = await client.get(f"/api/v1/ideation/agent/sessions/{unknown}/notices")
        assert r.status_code == 404
    finally:
        set_store(None)


def test_a_models_slow_search_does_not_hold_up_its_turn(slow, monkeypatch):
    import httpx
    from app.agents.providers import PROVIDERS  # noqa: F401 (breakers reset by conftest)

    from tests.unit.test_providers import _gemini_reply

    monkeypatch.setattr(get_settings(), "gemini_api_key", "g-key")
    sent: list[dict] = []
    replies = [
        _gemini_reply("", {"id": "c1", "name": "scan_prior_art", "arguments": {"idea": BCI}}),
        _gemini_reply("Let me look into that. Which district will you work from?"),
        _gemini_reply("I found 23 clinical trials. What will you build first?"),
    ]

    def handle(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        if not body.get("stream"):
            return httpx.Response(429, json={"error": {"message": "quota"}})
        sent.append(body)
        return httpx.Response(200, content=replies[len(sent) - 1],
                              headers={"content-type": "text/event-stream"})  # fmt: skip

    async def go():
        s = agent.new_session("Kavya")[0]
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:
            r1 = [ev async for ev in agent.turn_stream(s, BCI, client=c)][-1]["data"]
            tool_result = sent[1]["input"][-1]["result"][0]["text"]
            assert "still running" in tool_result and s.scan is None
            assert r1["provider"] == "gemini"
            await asyncio.sleep(0.5)  # the search finishes between turns
            r2 = [ev async for ev in agent.turn_stream(s, "Chennai", client=c)][-1]["data"]
        assert s.scan is not None and "scan_prior_art" in r2["tools_used"]
        assert "New since your last reply" in sent[2]["system_instruction"]
        assert "23 clinical trials" in r2["reply"]  # now backed by the finished search

    asyncio.run(go())
