"""Results tied to the idea they were made for (task 1.2.3).

Research is keyed by what the search would send (`research_key`, R014, R171);
jobs and results by session, key and kind (R040). A changed idea puts the old
scan aside and searches again; an unchanged one spends no new search; a result
for old inputs is never narrated.
"""

from __future__ import annotations

import asyncio
import copy

import httpx
import pytest
from app.agents import ideation as agent
from app.agents.jobs import Board, board
from app.core.config import get_settings
from app.elicitation import engine
from app.elicitation.session import Source
from app.research import novelty, sources

from tests.unit.test_ideation_agent import NOVELTY, SCAN

CHECK = novelty.check  # the real check, for the R158 test (the fixture replaces it)

COPRA = "a solar dryer for copra so coconut farmers get a better price"
TEA = "a herbal tea brand made from tulsi leaves for office workers"
TEA_SCAN = {**copy.deepcopy(SCAN), "idea": TEA}
TEA_SCAN["trials"] = {"total": 0, "items": []}
TEA_SCAN["projects"] = {"total": 4, "items": [{"name": "tulsi-tea-blends", "stars": 3}]}


@pytest.fixture(autouse=True)
def _research(monkeypatch):
    """Offline searches: the copra idea finds SCAN, the tea idea TEA_SCAN."""
    calls: list[str] = []
    st = get_settings()
    monkeypatch.setattr(st, "anthropic_api_key", "")
    monkeypatch.setattr(st, "gemini_api_key", "")

    async def fake_scan(text, *, elements=None, queries=None, client=None, private=False):
        calls.append(text)
        return TEA_SCAN if "tea" in text else SCAN

    async def fake_novelty(idea, *, scan=None, **_kw):
        if asyncio.isfuture(scan):
            await scan
        return NOVELTY

    monkeypatch.setattr("app.research.scan.scan", fake_scan)
    monkeypatch.setattr("app.research.novelty.check", fake_novelty)
    return calls


def _run(coro):
    return asyncio.run(coro)


def _session(idea: str = COPRA) -> agent.AgentSession:
    s = agent.new_session("Kavya")[0]
    s.idea = idea
    return s


# ---- the key (R014, R171) -------------------------------------------------------------


def test_the_key_exists_before_any_slot_is_filled():
    s = agent.new_session("Kavya")[0]
    assert s.idea_version is None
    assert isinstance(agent.research_key(s), str)  # never None (R171)
    s.idea = COPRA
    assert agent.research_key(s) != agent.research_key(agent.new_session("Kavya")[0])


def test_filling_slots_the_search_does_not_use_keeps_the_key():
    """R014: sector, product form, stage and district change idea_version, not the search."""
    s = _session()
    engine.observe(s.elicitation, COPRA)
    key, version = agent.research_key(s), s.idea_version
    for slot, value in (("sector", "agri"), ("product_form", "physical"), ("stage", "idea")):
        s.elicitation.put(slot, value, 0.9, Source.ANSWER)
    s.elicitation.put("district", "coimbatore", 0.9, Source.ANSWER)
    assert s.idea_version != version
    assert agent.research_key(s) == key


def test_a_change_the_search_would_send_changes_the_key():
    s = _session()
    engine.observe(s.elicitation, COPRA)
    key = agent.research_key(s)
    s.elicitation.put("problem", TEA, 0.9, Source.ANSWER)  # new terms
    assert agent.research_key(s) != key
    s = _session()
    engine.observe(s.elicitation, COPRA)
    s.private = True  # private mode searches nothing outside: another search
    assert agent.research_key(s) != key


def test_a_health_device_by_the_founders_answers_is_another_search():
    """The health-product rule (R139) picks the levers, so it is part of the key."""
    s = _session("a reminder box so elderly people take their medicine on time")
    engine.observe(s.elicitation, s.idea)
    s.elicitation.put("sector", "health", 0.9, Source.ANSWER)
    key = agent.research_key(s)
    s.elicitation.put("product_form", "physical", 0.9, Source.ANSWER)
    assert agent.research_key(s) != key


# ---- the board (R040) -----------------------------------------------------------------


def test_the_board_keeps_jobs_and_results_by_version():
    async def go():
        b = Board()
        gate = asyncio.Event()
        heard: list[str] = []

        def work(tag: str, wait: bool = False):
            async def run() -> dict:
                if wait:
                    await gate.wait()
                return {"tag": tag}

            return run

        q = b.subscribe("s1")
        a = b.start("s1", "research", work("a"), reuse_done=True, version="key-a")
        assert await b.wait(a, 1)
        # a finished job is reused only for its own version
        assert b.start("s1", "research", work("a2"), reuse_done=True, version="key-a") is a
        slow = b.start("s1", "research", work("b", wait=True), reuse_done=True, version="key-b")
        assert slow is not a and b.running("s1", "research", "key-b") is slow
        assert b.superseded("s1", "research", "key-c")
        # a new version does not wait behind the old one: the old one is cancelled
        c = b.start("s1", "research", work("c"), reuse_done=True, version="key-c")
        assert await b.wait(c, 1)
        await asyncio.sleep(0)
        assert slow.task.cancelled() and not b.superseded("s1", "research", "key-c")
        assert await b.take("s1", "research", "key-a") == {"tag": "a"}
        assert await b.take("s1", "research", "key-b") is None
        assert await b.take("s1", "research", "key-c") == {"tag": "c"}
        while not q.empty():
            heard.append(q.get_nowait()["payload"]["tag"])
        assert heard == ["a", "c"]
        await b.forget("s1")

    _run(go())


def test_a_late_result_for_an_old_version_is_kept_apart_and_not_announced():
    async def go():
        b = Board()
        gate = asyncio.Event()

        async def late() -> dict:
            await gate.wait()
            return {"tag": "old"}

        async def quick() -> dict:
            return {"tag": "new"}

        q = b.subscribe("s2")
        old = b.start("s2", "council", late, version="key-a")
        new = b.start("s2", "council", quick, version="key-b")
        await b.wait(new, 1)
        assert old.task.cancelled() or old.state == "running"
        assert await b.take("s2", "council", "key-b") == {"tag": "new"}
        assert q.get_nowait()["payload"] == {"tag": "new"} and q.empty()
        await b.forget("s2")

    _run(go())


def test_a_panel_for_the_old_idea_finishing_after_the_change_sends_no_notice():
    """A slow panel (a model's) for the old inputs must not reach the screen once the
    idea changed: only the new search is announced."""

    async def go():
        s = _session()
        await agent.turn(s, COPRA)
        q = board.subscribe(s.id)
        while not q.empty():
            q.get_nowait()
        old_key = agent.research_key(s)
        gate = asyncio.Event()

        async def slow_panel() -> dict:
            await gate.wait()
            return {"tag": "old panel", "at": "x"}

        panel = board.start(s.id, "council", slow_panel, version=old_key)
        s.elicitation.put("problem", TEA, 0.9, Source.ANSWER)
        agent._retire_stale(s)  # the next turn starts after the idea changed
        gate.set()
        await asyncio.sleep(0.2)
        heard = []
        while not q.empty():
            heard.append(q.get_nowait()["kind"])
        assert panel.task.cancelled()
        assert heard == ["research"]  # the new search only, never the old panel
        assert (await board.take(s.id, "council", old_key) or {}).get("tag") != "old panel"
        board.unsubscribe(s.id, q)
        await board.forget(s.id)

    _run(go())


# ---- the conversation -----------------------------------------------------------------


def test_a_changed_idea_searches_again_and_the_old_scan_is_never_narrated(_research):
    """1.2.3.3: after the problem changes, nothing from the old scan is spoken."""

    async def go():
        s = _session()
        r1 = await agent.turn(s, COPRA)
        assert r1["evidence"]["trials"]["total"] == 23 and s.research_key
        old_key = s.research_key
        await agent.turn(s, "Coimbatore")
        assert "statement" in s.narrated
        # the founder changes the idea itself
        r3 = await agent.turn(s, f"Sorry, actually the problem is {TEA}")
        assert s.research_key not in (None, old_key)
        assert r3["evidence"]["projects"]["total"] == 4  # the tea search, not the copra one
        assert "23 clinical trials" not in r3["reply"]
        assert "tea" in _research[-1]

    _run(go())
    assert len(_research) == 2


def test_an_unchanged_search_runs_once_over_a_whole_interview(_research):
    """R014: answering the other questions is not a new idea; the free budget is kept."""

    async def go():
        s = _session()
        await agent.turn(s, COPRA)
        for reply in ("agriculture", "physical", "Coimbatore", "just an idea", "skip"):
            await agent.turn(s, reply)

    _run(go())
    assert len(_research) == 1


def test_a_late_result_for_the_old_idea_is_not_taken_in(monkeypatch, _research):
    """R040: a search for the old idea that finishes after the change is never absorbed."""
    monkeypatch.setattr(get_settings(), "research_wait_s", 0.05)
    gate: dict = {}

    async def slow_scan(text, *, elements=None, queries=None, client=None, private=False):
        _research.append(text)
        if "tea" not in text:
            await asyncio.sleep(0.3)  # the copra search is still running at the change
            return SCAN
        await gate.setdefault("tea", asyncio.Event()).wait()
        return TEA_SCAN

    monkeypatch.setattr("app.research.scan.scan", slow_scan)

    async def go():
        s = _session()
        r1 = await agent.turn(s, COPRA)
        assert agent.SEARCHING in r1["reply"] and s.scan is None
        r2 = await agent.turn(s, f"Sorry, actually the problem is {TEA}")
        await asyncio.sleep(0.4)  # the copra search would have finished by now
        r3 = await agent.turn(s, "skip")
        assert s.scan is None and r3["evidence"] is None  # never the copra result
        assert "23 clinical trials" not in r2["reply"] + r3["reply"]
        await board.forget(s.id)

    _run(go())


def test_a_re_run_that_finds_the_same_is_not_said_again(_research):
    async def go():
        s = _session()
        await agent.turn(s, COPRA)
        second = await agent.turn(s, "Coimbatore")
        assert "only what I found in the sources I searched" in second["reply"]
        # who it is for changes the search (the re-target lever), but it finds the same
        s.elicitation.put("beneficiary", "smallholder farmers", 0.9, Source.ANSWER)
        third = await agent.turn(s, "skip")
        assert len(_research) == 2
        assert "only what I found in the sources I searched" not in third["reply"]
        assert "23 clinical trials" not in third["reply"]

    _run(go())


def test_an_old_saved_session_loads_and_keeps_its_scan(_research):
    """A document saved before research keys: its scan stays, and no search is spent."""

    async def go():
        s = _session()
        await agent.turn(s, COPRA)
        doc = s.to_dict()
        del doc["research_key"]
        back = agent.AgentSession.from_dict(doc)
        assert back.scan is not None and back.research_key == agent.research_key(back)
        await agent.turn(back, "Coimbatore")
        assert back.scan is not None

    _run(go())
    assert len(_research) == 1


# ---- R033: a reply to another question is not the problem ------------------------------


def test_a_long_answer_to_another_question_is_not_read_as_the_problem():
    """A short opening fills no problem; the stage answer that follows must not be
    taken for it (and so must not become the text the search is made from)."""
    s = _session("solar copra dryer")
    engine.observe(s.elicitation, "solar copra dryer")
    assert "problem" not in s.elicitation.slots
    key = agent.research_key(s)
    engine.observe(
        s.elicitation, "we have a working prototype that we tested last month", answering="stage"
    )
    assert "problem" not in s.elicitation.slots and agent.research_key(s) == key
    # a stated problem still counts, whatever was asked
    engine.observe(
        s.elicitation, "the problem is that copra rots in the monsoon rains", answering="stage"
    )
    assert "rots in the monsoon" in s.elicitation.slots["problem"].value
    # an opening description, with no question asked, is still read for its problem
    t = _session()
    engine.observe(t.elicitation, "I want to dry copra with the sun for coconut farmers")
    assert "problem" in t.elicitation.slots


# ---- R158: the research job's calls side by side --------------------------------------


def test_the_part_counts_are_sent_while_the_scan_runs(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "research_cache_dir", str(tmp_path))
    counted = asyncio.Event()

    async def count(client, query, cache=None, filter=None):
        counted.set()
        return sources.SourceResult("papers", "ok", total=400)

    monkeypatch.setattr(sources, "paper_count", count)

    async def go():
        async def scan() -> dict:
            await asyncio.wait_for(counted.wait(), 1)  # finishes only once counting began
            return {"local": {}}

        async with httpx.AsyncClient() as c:
            idea = "brain waves to send a nurse call for medication"
            return await CHECK(idea, scan=asyncio.ensure_future(scan()), client=c)

    r = _run(go())
    assert r["elements"] and r["elements"][0]["papers"] == 400
