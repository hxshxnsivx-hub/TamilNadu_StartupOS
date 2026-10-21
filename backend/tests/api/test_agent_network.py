"""Task 1.1.4: a conversation survives a 2G connection.

A turn retried with the same client_turn_id is answered from the session, not
run twice (R038), on the stream and on the plain endpoint; a stream that fails
after it started says why with a code (R159); the snapshot carries what is
pending (R176), the results that finished while the founder was away (R143)
and, after a long gap, a preamble that repeats the pending question without
spending the question budget (1.1.4.3).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from app.agents import ideation as agent
from app.agents import store, tools
from app.agents.jobs import LATEST, board
from app.core.config import get_settings
from app.main import app
from httpx import ASGITransport, AsyncClient
from tests.unit.test_ideation_agent import NOVELTY, SCAN

URL = "/api/v1/ideation/agent/sessions"


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No model, no network: the offline turn with a canned search."""

    async def fake_scan(text, *, elements=None, queries=None, client=None, private=False):
        return SCAN

    async def fake_novelty(idea, **_kw):
        return NOVELTY

    monkeypatch.setattr("app.research.scan.scan", fake_scan)
    monkeypatch.setattr(tools.research, "scan", fake_scan)
    monkeypatch.setattr("app.research.novelty.check", fake_novelty)
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")
    mem = store.MemoryStore()
    store.set_store(mem)
    yield mem
    store.set_store(None)


async def _start(client: AsyncClient) -> str:
    r = await client.post(URL, json={"name": "Kavya"})
    assert r.status_code == 200
    return f"{URL}/{r.json()['session_id']}"


async def _stream(client: AsyncClient, base: str, body: dict) -> list[tuple[str, object]]:
    async with client.stream("POST", f"{base}/turns/stream", json=body) as r:
        assert r.status_code == 200
        text = "".join([c async for c in r.aiter_text()])
    out, kind = [], None
    for line in text.splitlines():
        if line.startswith("event: "):
            kind = line[7:]
        elif line.startswith("data: "):
            out.append((kind, json.loads(line[6:])))
    return out


def _doc(mem: store.MemoryStore, base: str) -> dict:
    return json.loads(mem._docs[base.rsplit("/", 1)[1]])


# ---- R038: one turn, however many times the phone sends it ---------------------------


async def test_a_retried_stream_replays_the_saved_turn(client, offline):
    base = await _start(client)
    body = {"text": "a nurse alert device for paralysed patients", "client_turn_id": "turn-0001"}
    first = await _stream(client, base, body)
    before = _doc(offline, base)

    again = await _stream(client, base, body)

    assert [k for k, _ in again] == ["ack", *["sentence"] * (len(again) - 2), "done"]
    said = [d for k, d in first if k == "sentence"]
    assert [d for k, d in again if k == "sentence"] == said
    assert again[0][1] == first[0][1]  # the same ack: the same question
    done = dict(again[-1][1])
    assert done.pop("replayed") is True and done == first[-1][1]
    after = _doc(offline, base)
    # nothing ran twice: not the transcript, the turns, the budget or the version
    assert after["version"] == before["version"]
    assert after["messages"] == before["messages"]
    assert after["elicitation"]["turns"] == before["elicitation"]["turns"]
    assert after["elicitation"]["questions_asked"] == before["elicitation"]["questions_asked"]


async def test_the_plain_endpoint_and_the_stream_share_one_check(client, offline):
    base = await _start(client)
    body = {"text": "a nurse alert device for paralysed patients", "client_turn_id": "turn-0002"}
    done = (await client.post(f"{base}/turns", json=body)).json()
    version = _doc(offline, base)["version"]

    replayed = await _stream(client, base, body)
    assert replayed[-1][1]["reply"] == done["reply"]
    again = (await client.post(f"{base}/turns", json=body)).json()
    assert again["reply"] == done["reply"] and again["replayed"] is True
    assert _doc(offline, base)["version"] == version


async def test_a_new_id_or_no_id_is_a_new_turn(client, offline):
    base = await _start(client)
    await client.post(
        f"{base}/turns", json={"text": "a nurse alert device", "client_turn_id": "a" * 8}
    )
    turns = len(_doc(offline, base)["elicitation"]["turns"])

    await client.post(f"{base}/turns", json={"text": "Chennai", "client_turn_id": "b" * 8})
    assert len(_doc(offline, base)["elicitation"]["turns"]) == turns + 1
    # a turn without an id forgets the last one, so an old id cannot replay a stale reply
    await client.post(f"{base}/turns", json={"text": "hospitals"})
    assert _doc(offline, base)["last_turn"] is None
    r = await client.post(f"{base}/turns", json={"text": "Chennai", "client_turn_id": "b" * 8})
    assert "replayed" not in r.json()


async def test_a_turn_id_is_bounded(client):
    base = await _start(client)
    for bad in ("short", "x" * 65, "has space in it", "../../etc"):
        r = await client.post(f"{base}/turns", json={"text": "hello", "client_turn_id": bad})
        assert r.status_code == 422, bad


# ---- R159: an error after the stream started carries a code ------------------------


async def test_a_conflict_on_the_stream_is_typed(client, offline, monkeypatch):
    base = await _start(client)

    async def refused(s):
        raise store.VersionConflict(s.id)

    monkeypatch.setattr(offline, "save", refused)
    events = await _stream(
        client, base, {"text": "a nurse alert device", "client_turn_id": "c" * 8}
    )
    kind, data = events[-1]
    assert kind == "error" and data["code"] == "conflict" and data["detail"]
    assert "done" not in [k for k, _ in events]


async def test_a_failure_on_the_stream_is_typed(client, monkeypatch):
    base = await _start(client)

    async def broken(*a, **kw):
        raise ValueError("boom")
        yield  # pragma: no cover

    monkeypatch.setattr(agent, "turn_stream", broken)
    events = await _stream(client, base, {"text": "a nurse alert device"})
    assert events == [("error", {"code": "failed", "detail": "turn failed: ValueError"})]


# ---- R176: what the founder is being asked, as data ---------------------------------


async def test_the_snapshot_says_what_is_pending(client):
    base = await _start(client)
    pending = (await client.get(base)).json()["pending"]
    assert pending["kind"] == "ask" and pending["slot"] is None
    assert pending["question"] in (await client.get(base)).json()["transcript"][0]["text"]

    act = (await client.post(f"{base}/turns", json={"text": "a nurse alert device"})).json()[
        "action"
    ]
    snap = (await client.get(base)).json()
    assert snap["pending"] == {
        "kind": "ask",
        "slot": act["slot"],
        "question": act["question"],
        "options": [],
        "idea_version": snap["idea_version"],
    }


def test_an_old_document_without_pending_or_last_turn_still_loads():
    s = agent.new_session("Kavya")[0]
    agent_doc = s.to_dict()
    for key in ("pending", "last_turn"):
        agent_doc.pop(key)
    agent_doc["pending_slot"] = "district"
    back = agent.AgentSession.from_dict(agent_doc)
    assert back.last_turn is None
    assert back.pending["kind"] == "ask" and back.pending["slot"] == "district"
    assert back.pending["question"]

    agent_doc["pending_slot"] = None
    agent_doc["elicitation"]["state"] = "confirming"
    agent_doc["elicitation"]["objective"] = "A nurse alert for patients in Chennai."
    back = agent.AgentSession.from_dict(agent_doc)
    assert back.pending["kind"] == "confirm"
    assert "A nurse alert for patients in Chennai." in back.pending["question"]


# ---- 1.1.4.3: welcome back, and the question again, free -----------------------------


def _age(mem: store.MemoryStore, base: str, by: timedelta) -> None:
    sid = base.rsplit("/", 1)[1]
    doc = json.loads(mem._docs[sid])
    doc["updated_at"] = (datetime.now(UTC) - by).isoformat()
    mem._docs[sid] = json.dumps(doc)


async def test_a_resume_after_a_long_gap_repeats_the_question_for_free(client, offline):
    base = await _start(client)
    act = (await client.post(f"{base}/turns", json={"text": "a nurse alert device"})).json()[
        "action"
    ]
    assert (await client.get(base)).json()["resume"] is None  # a reload, not a return

    _age(offline, base, timedelta(hours=2))
    asked = _doc(offline, base)["elicitation"]["questions_asked"]
    snap = (await client.get(base)).json()
    assert snap["resume"].startswith("Welcome back, Kavya.")
    assert snap["resume"].endswith(act["question"])
    assert _doc(offline, base)["elicitation"]["questions_asked"] == asked

    # the answer to the repeated question is the answer to the question asked before
    await client.post(f"{base}/turns", json={"text": "patients in hospital wards"})
    turns = _doc(offline, base)["elicitation"]["turns"]
    assert turns[-1]["asked"] == act["slot"]


# ---- R143: results that finished while the founder was away -------------------------


async def test_results_finished_offline_are_in_the_snapshot_and_the_notices(client, offline):
    base = await _start(client)
    sid = base.rsplit("/", 1)[1]
    key = agent.research_key(await offline.get(sid))  # results are kept by research key
    await board.results.put(sid, key, "research", {"scan": SCAN, "novelty": NOVELTY})
    try:
        _age(offline, base, timedelta(hours=1))
        snap = (await client.get(base)).json()
        assert snap["evidence"]["trials"]["total"] == 23
        assert snap["novelty"] == NOVELTY
        assert "the search finished" in snap["resume"]

        async with client.stream("GET", f"{base}/notices", params={"limit": 1}) as r:
            lines = [ln async for ln in r.aiter_lines() if ln.startswith("event:")]
        assert lines == ["event: evidence", "event: novelty"]
    finally:
        await board.forget(sid)


async def test_results_for_other_research_inputs_are_not_shown(client, offline):
    """Task 1.2.3: a result made for research inputs the idea has moved on from is
    in neither the snapshot nor the notices replayed on subscribe."""
    base = await _start(client)
    sid = base.rsplit("/", 1)[1]
    await board.results.put(sid, "an-old-key", "research", {"scan": SCAN, "novelty": NOVELTY})
    await board.results.put(sid, LATEST, "research", {"scan": SCAN, "novelty": NOVELTY})
    try:
        snap = (await client.get(base)).json()
        assert snap["evidence"] is None and snap["novelty"] is None
    finally:
        await board.forget(sid)


async def test_a_stream_cut_before_done_saves_nothing_so_the_retry_runs_once(offline):
    """R076: the server side of the retry. A turn whose stream stops before `done`
    is not saved, so the same id finds no saved turn and runs it, once."""
    s, _ = agent.new_session("Kavya")
    await offline.create(s)
    cut = agent.turn_stream(s, "a nurse alert device", client_turn_id="d" * 8)
    async for ev in cut:
        if ev["event"] == "sentence":
            break  # the phone lost the connection here
    await cut.aclose()

    back = await offline.get(s.id)
    assert back.last_turn is None and agent.replay(back, "d" * 8) is None
    turns = len(back.elicitation.turns)
    await agent.turn(back, "a nurse alert device", client_turn_id="d" * 8)
    await offline.save(back)
    again = await offline.get(s.id)
    assert len(again.elicitation.turns) == turns + 1
    assert agent.replay(again, "d" * 8)[-1]["data"]["replayed"] is True
