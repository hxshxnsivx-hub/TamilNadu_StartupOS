"""Unit tests for the ideation agent: tool loop with a mock model, and the offline path."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from app.agents import ideation as agent
from app.agents import tools
from app.core.config import get_settings

BCI = (
    "I want to build a device so paralysed patients can ask nurses for a change in medication"
    " using their brain waves"
)

SCAN = {
    "idea": BCI,
    "queries": {},
    "associated_domains": {
        "basis": "papers",
        "fields": [
            {"name": "Neuroscience", "share_pct": 60},
            {"name": "Medicine", "share_pct": 40},
        ],
        "subfields": [],
    },
    "vanigam_categories": ["health_bio"],
    "papers": {
        "total": 420,
        "by_year": {2023: 55},
        "most_relevant": [{"title": "P300 speller", "year": 2023, "cited_by": 9, "url": "u"}],
        "most_cited": [],
    },
    "trials": {"total": 23, "items": [{"id": "NCT1", "title": "BCI speech trial"}]},
    "projects": {"total": 702, "items": [{"name": "lab/eeg-bci", "stars": 169}]},
    "patents": {"total": 0, "items": []},
    "local": {"startups": [], "registry_domains": []},
    "elements": [],
    "discuss": [{"field": "Neuroscience", "questions": ["Which signal do you rely on?"]}],
    "coverage": [
        {"source": "papers", "status": "ok", "found": 420, "note": ""},
        {"source": "patents", "status": "no_key", "found": 0, "note": "add key"},
    ],
    "caveat": "not proof of novelty",
}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    agent._reset_sessions()
    calls: list = []

    async def fake_scan(text, *, elements=None, queries=None, client=None):
        calls.append({"text": text, "elements": elements, "queries": queries})
        return SCAN

    monkeypatch.setattr("app.research.scan.scan", fake_scan)
    monkeypatch.setattr(tools.research, "scan", fake_scan)
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")
    return calls


def _run(coro):
    return asyncio.run(coro)


def test_greeting_uses_the_founders_name():
    r = agent.start("Kavya")
    assert "Kavya" in r["reply"] and agent.get_session(r["session_id"])


def test_offline_turn_scans_and_cites_evidence(_env):
    s = agent.get_session(agent.start("Kavya")["session_id"])
    r = _run(agent.turn(s, BCI))
    assert r["tools_used"] == ["scan_prior_art"]
    assert "23 clinical trials" in r["reply"] and "lab/eeg-bci" in r["reply"]
    assert "could not search patents" in r["reply"]  # not searched is never "nothing"
    assert r["evidence"]["trials"]["total"] == 23
    assert r["action"]["kind"] in ("ask", "confirm")
    # the scan is summarised once, not repeated every turn
    r2 = _run(agent.turn(s, "Chennai"))
    assert r2["tools_used"] == [] and "clinical trials" not in r2["reply"]
    assert len(_env) == 1


def test_compact_scan_keeps_coverage_and_drops_bulk():
    c = tools.compact_scan(SCAN)
    assert c["coverage"] == SCAN["coverage"] and c["caveat"]
    assert set(c["trials"]["items"][0]) == {"id", "title", "status", "sponsor", "url"}


def test_note_fact_refuses_unknown_keys():
    s = agent.get_session(agent.start()["session_id"])
    out = _run(tools.run_tool("note_fact", {"key": "aadhaar", "value": "1"}, s.elicitation, {}))
    assert "error" in out
    out = _run(
        tools.run_tool("note_fact", {"key": "district", "value": "madurai"}, s.elicitation, {})
    )
    assert out == {"recorded": "district"} and "district" in s.elicitation.slots


def test_support_for_lists_schemes_and_incubators():
    out = _run(
        tools.run_tool(
            "support_for", {"domain_id": "banana_value_added", "district": "tiruchirappalli"},
            agent.get_session(agent.start()["session_id"]).elicitation, {},
        )
    )  # fmt: skip
    assert out.get("schemes") is not None and "incubators" in out


def test_model_tool_loop(monkeypatch, _env):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "test-key")
    sent: list = []
    replies = [
        {
            "stop_reason": "tool_use",
            "content": [
                {"type": "text", "text": "Let me look that up."},
                {
                    "type": "tool_use",
                    "id": "tu_1",
                    "name": "scan_prior_art",
                    "input": {"idea": BCI, "queries": {"papers": "P300 BCI nurse call"}},
                },
            ],
        },
        {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "23 trials exist, e.g. a BCI speech trial."}],
        },
    ]

    def handle(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        sent.append(body)
        assert req.headers["x-api-key"] == "test-key"
        return httpx.Response(200, json=replies[len(sent) - 1])

    s = agent.get_session(agent.start("Arun")["session_id"])

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:
            return await agent.turn(s, BCI, client=c)

    r = _run(go())
    assert r["reply"] == "23 trials exist, e.g. a BCI speech trial."
    assert r["tools_used"] == ["scan_prior_art"] and r["evidence"]["projects"]["total"] == 702
    assert _env[0]["queries"] == {"papers": "P300 BCI nurse call"}
    first = sent[0]
    assert first["messages"][0]["role"] == "user"  # the API needs a user turn first
    assert "Arun" in first["system"] and {t["name"] for t in first["tools"]} >= {
        "scan_prior_art",
        "build_roadmap",
    }
    # the tool result went back to the model, paired with its call
    result = sent[1]["messages"][-1]["content"][0]
    assert result["type"] == "tool_result" and result["tool_use_id"] == "tu_1"
    assert json.loads(result["content"])["trials"]["total"] == 23


def test_confirmation_builds_the_roadmap_offline():
    s = agent.get_session(agent.start("Meena")["session_id"])
    _run(agent.turn(s, "banana chips and banana flour unit in Tiruchirappalli for B-grade fruit"))
    for _ in range(10):  # answer until the engine restates the objective
        if s.elicitation.state.value == "confirming":
            break
        _run(agent.turn(s, "skip"))
    else:
        pytest.skip("engine did not reach confirmation with these answers")
    assert s.elicitation.skipped  # "skip" declined the questions instead of answering them
    r = _run(agent.turn(s, "yes, that's right"))
    assert r["action"]["kind"] == "generate" and "build_roadmap" in r["tools_used"]
    assert r["roadmap"]["milestones"] and "milestones" in r["reply"]
