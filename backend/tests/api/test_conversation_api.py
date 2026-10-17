"""API test of a multi-turn orchestrator conversation that switches context and comes back."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.fixture
def offline(monkeypatch):
    """No model and no network: idea turns search only Vanigam's own data."""
    from app.agents import store
    from app.core.config import get_settings
    from app.research import novelty
    from app.research import scan as research

    real_scan, real_novelty = research.scan, novelty.check

    async def private_scan(text, *, elements=None, queries=None, client=None, private=False):
        return await real_scan(text, client=client, private=True)

    async def private_novelty(idea, **kw):
        return await real_novelty(idea, **{**kw, "private": True})

    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")
    monkeypatch.setattr(research, "scan", private_scan)
    monkeypatch.setattr(novelty, "check", private_novelty)
    store.set_store(store.MemoryStore())
    yield
    store.set_store(None)


async def test_conversation_routes_switches_context_and_resumes(client: AsyncClient, offline):
    r = await client.post("/api/v1/orchestrator/sessions", json={"name": "Kavya"})
    assert r.status_code == 200 and "Kavya" in r.json()["reply"]
    sid = r.json()["session_id"]
    base = f"/api/v1/orchestrator/sessions/{sid}"

    async def say(text: str) -> dict:
        resp = await client.post(f"{base}/turns", json={"text": text})
        assert resp.status_code == 200, resp.text
        return resp.json()

    # 1. an idea goes to the ideation agent, which asks its next question
    t = await say("I have a startup idea: a nurse alert device")
    assert (t["node"], t["swarm"], t["action"]) == ("idea_discussion", "roadmap", "route")
    assert t["data"]["action"]["kind"] == "ask"
    idea_question = t["reply"]

    # 2. no new topic: the answer stays with the idea, saved in the same session
    t = await say("Chennai")
    assert (t["node"], t["action"]) == ("idea_discussion", "continue")
    snap = (await client.get(f"/api/v1/ideation/agent/sessions/{sid}")).json()
    assert snap["known"]["district"] == "chennai"
    idea_question = t["reply"] or idea_question

    # 2b. the agent asks how it will be funded; "a grant" answers it, it is no scheme query
    from app.agents import store

    funding_q = "How do you expect to fund it — your own money, a loan, a grant, investors?"
    saved = await (await store.get_store()).get(sid)
    saved.pending_slot = "funding_route"
    saved.orchestrator["last_question"] = funding_q
    await (await store.get_store()).save(saved)
    t = await say("a grant")
    assert (t["node"], t["action"], t["paused"]) == ("idea_discussion", "continue", [])
    snap = (await client.get(f"/api/v1/ideation/agent/sessions/{sid}")).json()
    assert snap["known"]["funding_route"] == "grant"
    idea_question = t["reply"] or idea_question

    # 3. a scheme question pauses the idea, is answered, and the idea resumes
    t = await say("wait, which scheme am I eligible for?")
    assert t["swarm"] == "scheme" and t["data"]["total_checked"] > 0
    assert t["resumed"]["swarm"] == "roadmap" and t["node"] == "idea_discussion"
    assert t["paused"] == [] and "back to your idea" in t["reply"]
    assert idea_question in t["reply"]

    # 4. the saved state says the idea is the task in hand again
    state = (await client.get(base)).json()
    assert state["active_swarm"] == "roadmap" and state["paused"] == []
    assert [m["role"] for m in state["transcript"]][:3] == ["assistant", "user", "assistant"]

    # 5. a roadmap request stays with the idea and shows its roadmap
    t = await say("show me the roadmap")
    assert t["node"] == "idea_discussion" and t["data"]["roadmap"]["milestones"]
    assert t["action"] == "continue" and state["paused"] == []


async def test_conversation_errors_use_the_envelope(client: AsyncClient, offline):
    missing = await client.post(
        f"/api/v1/orchestrator/sessions/{'0' * 32}/turns", json={"text": "hi"}
    )
    assert missing.status_code == 404 and missing.json()["error_code"] == "HTTP_404"
    bad = await client.post("/api/v1/orchestrator/sessions/nope/turns", json={"text": "hi"})
    assert bad.status_code == 422 and bad.json()["error_code"] == "VALIDATION_FAILED"


async def test_unclear_first_turn_asks_for_clarification(client: AsyncClient, offline):
    sid = (await client.post("/api/v1/orchestrator/sessions", json={})).json()["session_id"]
    t = (
        await client.post(f"/api/v1/orchestrator/sessions/{sid}/turns", json={"text": "hmm"})
    ).json()
    assert t["node"] == "clarification" and t["action"] == "clarify"


async def test_route_preview_still_works(client: AsyncClient):
    r = await client.post("/api/v1/orchestrator/route", json={"message": "my startup idea"})
    assert r.status_code == 200 and r.json()["swarm"] == "roadmap"
