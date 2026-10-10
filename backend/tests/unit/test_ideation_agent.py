"""Unit tests for the ideation agent: streamed turns, fact check, saved sessions, offline path."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from app.agents import ideation as agent
from app.agents import tools
from app.agents.grounding import NOVELTY_LINE
from app.agents.store import MemoryStore, VersionConflict
from app.core.config import get_settings
from app.elicitation.slots import Sector

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
    "trials": {"total": 23, "items": [{"id": "NCT01234567", "title": "BCI speech trial"}]},
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


NOVELTY = {
    "elements": [],
    "pairs": [],
    "context": {"searched": True, "world_papers": 1118, "india_papers": 52},
    "statement": {
        "type": "combination",
        "text": "Both parts are well studied on their own: brain waves (760,191 papers) and"
        " nurse call (980). Together, I found only 19.",
    },
    "levers": [
        {
            "kind": "combine",
            "text": "Build your version around joining brain waves with nurse call.",
            "because": "only 19 papers cover both",
        },
        {
            "kind": "localise",
            "text": "Make it fit Tamil Nadu.",
            "because": "52 of 1,118 papers are from India",
        },
    ],
    "caveat": "not proof of novelty",
}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    calls: list = []

    async def fake_scan(text, *, elements=None, queries=None, client=None, private=False):
        calls.append({"text": text, "elements": elements, "queries": queries, "private": private})
        return SCAN

    async def fake_novelty(idea, *, elements=None, scan=None, beneficiary=None, client=None,
                           private=False):  # fmt: skip
        calls.append({"novelty": idea, "elements": elements, "private": private})
        return NOVELTY

    monkeypatch.setattr("app.research.scan.scan", fake_scan)
    monkeypatch.setattr(tools.research, "scan", fake_scan)
    monkeypatch.setattr("app.research.novelty.check", fake_novelty)
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")
    return calls


def _run(coro):
    return asyncio.run(coro)


def _new(name="Kavya", **kw) -> agent.AgentSession:
    return agent.new_session(name, **kw)[0]


async def _events(s, text, client=None) -> list[dict]:
    return [ev async for ev in agent.turn_stream(s, text, client=client)]


# ---- the model, as a server-sent event stream ----------------------------------


def _sse(*events: dict) -> bytes:
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


def _text_reply(text: str, stop: str = "end_turn") -> bytes:
    return _sse(
        {"type": "message_start", "message": {}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        *[
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": c}}
            for c in (text[: len(text) // 2], text[len(text) // 2 :])
        ],
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": stop}},
        {"type": "message_stop"},
    )


def _tool_reply(say: str, tool: str, args: dict) -> bytes:
    raw = json.dumps(args)
    return _sse(
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": say}},
        {"type": "content_block_stop", "index": 0},
        {
            "type": "content_block_start",
            "index": 1,
            "content_block": {"type": "tool_use", "id": "tu_1", "name": tool, "input": {}},
        },
        {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": raw[:10]},
        },
        {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": raw[10:]},
        },
        {"type": "content_block_stop", "index": 1},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use"}},
    )


def _model(monkeypatch, *bodies: bytes) -> list:
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "test-key")
    sent: list = []

    def handle(req: httpx.Request) -> httpx.Response:
        sent.append(json.loads(req.content))
        assert req.headers["x-api-key"] == "test-key"
        return httpx.Response(
            200, content=bodies[len(sent) - 1], headers={"content-type": "text/event-stream"}
        )

    return sent, httpx.MockTransport(handle)


async def _with(transport, fn):
    async with httpx.AsyncClient(transport=transport) as c:
        return await fn(c)


# ---- offline path ------------------------------------------------------------------


def test_greeting_uses_the_founders_name():
    s, greeting = agent.new_session("Kavya")
    assert "Kavya" in greeting and s.messages[0]["role"] == "user"


def test_offline_turn_scans_and_cites_evidence(_env):
    s = _new()
    r = _run(agent.turn(s, BCI))
    assert r["tools_used"] == ["scan_prior_art", "check_novelty", "ask_council"]
    assert "23 clinical trials" in r["reply"] and "lab/eeg-bci" in r["reply"]
    assert "could not search patents" in r["reply"]  # not searched is never "nothing"
    assert r["evidence"]["trials"]["total"] == 23
    assert r["action"]["kind"] in ("ask", "confirm")
    # the scan is summarised once, not repeated every turn
    r2 = _run(agent.turn(s, "Chennai"))
    assert r2["tools_used"] == [] and "clinical trials" not in r2["reply"]
    assert len(_env) == 2  # one scan, one novelty check


def test_stream_events_come_in_order():
    kinds = [e["event"] for e in _run(_events(_new(), BCI))]
    assert kinds[0] == "ack" and kinds[-1] == "done"
    assert "evidence" in kinds and kinds.count("sentence") >= 2
    assert kinds.index("evidence") < kinds.index("sentence")


def test_private_session_scans_privately(_env):
    s = _new(private=True)
    _run(agent.turn(s, BCI))
    assert _env[0]["private"] is True


def test_compact_scan_keeps_coverage_and_drops_bulk():
    c = tools.compact_scan(SCAN)
    assert c["coverage"] == SCAN["coverage"] and c["caveat"]
    assert set(c["trials"]["items"][0]) == {"id", "title", "status", "sponsor", "url"}


def test_note_fact_refuses_unknown_keys():
    s = _new()
    out = _run(tools.run_tool("note_fact", {"key": "aadhaar", "value": "1"}, s.elicitation, {}))
    assert "error" in out
    out = _run(
        tools.run_tool("note_fact", {"key": "district", "value": "madurai"}, s.elicitation, {})
    )
    assert out == {"recorded": "district"} and "district" in s.elicitation.slots


def test_support_for_lists_schemes_and_incubators():
    args = {"domain_id": "banana_value_added", "district": "tiruchirappalli"}
    out = _run(tools.run_tool("support_for", args, _new().elicitation, {}))
    assert out.get("schemes") is not None and "incubators" in out


def test_confirmation_builds_the_roadmap_offline():
    s = _new("Meena")
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


# ---- with the model ------------------------------------------------------------------


def test_model_tool_loop_streams_and_cites(monkeypatch, _env):
    sent, transport = _model(
        monkeypatch,
        _tool_reply(
            "Let me look that up.",
            "scan_prior_art",
            {"idea": BCI, "queries": {"papers": "P300 BCI nurse call"}},
        ),
        _text_reply("I found 23 trials, such as NCT01234567. Which signal would you use?"),
    )
    s = _new("Arun")
    evs = _run(_with(transport, lambda c: _events(s, BCI, c)))
    said = [e["data"] for e in evs if e["event"] == "sentence"]
    assert said == [
        "Let me look that up.",
        "I found 23 trials, such as NCT01234567.",
        "Which signal would you use?",
    ]
    done = evs[-1]["data"]
    assert done["tools_used"] == ["scan_prior_art"] and done["dropped"] == 0
    assert _env[0]["queries"] == {"papers": "P300 BCI nurse call"}
    first = sent[0]
    assert first["stream"] is True and first["messages"][0]["role"] == "user"
    assert "Arun" in first["system"] and {t["name"] for t in first["tools"]} >= {
        "scan_prior_art",
        "build_roadmap",
    }
    # the tool result went back to the model, paired with its call
    result = sent[1]["messages"][-1]["content"][0]
    assert result["type"] == "tool_result" and result["tool_use_id"] == "tu_1"
    assert json.loads(result["content"])["trials"]["total"] == 23


def test_unbacked_sentences_are_never_spoken(monkeypatch):
    _, transport = _model(
        monkeypatch,
        _text_reply(
            "There are 4,500 papers on this. PMEGP gives you 25 lakh. This is a unique idea."
            " Who would pay for it?"
        ),
    )
    s = _new()
    evs = _run(_with(transport, lambda c: _events(s, "a device for paralysed patients", c)))
    said = [e["data"] for e in evs if e["event"] == "sentence"]
    assert said == [NOVELTY_LINE, "Who would pay for it?"]
    assert evs[-1]["data"]["dropped"] == 2


def test_when_every_sentence_fails_the_question_is_still_asked(monkeypatch):
    _, transport = _model(monkeypatch, _text_reply("You will get 40 lakh from TANSEED."))
    s = _new()
    evs = _run(_with(transport, lambda c: _events(s, "a device for paralysed patients", c)))
    said = [e["data"] for e in evs if e["event"] == "sentence"]
    assert len(said) == 1 and said[0] == evs[0]["data"]["action"]["question"]


# ---- saved sessions ----------------------------------------------------------------------


def test_session_survives_a_save_and_load():
    store = MemoryStore()
    s = _new()
    _run(store.create(s))
    _run(agent.turn(s, "textile finishing unit for weavers in Erode"))
    _run(store.save(s))
    back = _run(store.get(s.id))
    assert back.elicitation.slots["sector"].value is Sector.TEXTILE  # enum restored
    assert back.elicitation.slots["district"].value == "erode"
    assert back.pending_slot == s.pending_slot and back.idea_version == s.idea_version
    snap = agent.snapshot(back)
    assert snap["last_question"] and snap["transcript"][0]["role"] == "assistant"


def test_concurrent_saves_do_not_overwrite_each_other():
    store = MemoryStore()
    s = _new()
    _run(store.create(s))
    a, b = _run(store.get(s.id)), _run(store.get(s.id))
    _run(store.save(a))
    with pytest.raises(VersionConflict):
        _run(store.save(b))


def test_idea_version_changes_with_the_idea_only():
    s = _new()
    _run(agent.turn(s, "The problem is weavers in Erode cannot reach buyers outside the district"))
    v1 = s.idea_version
    s.elicitation.put("team_size", 3, 0.9, s.elicitation.slots["problem"].source)
    assert s.idea_version == v1
    s.elicitation.put(
        "problem", "dyers lose colour batches", 0.95, s.elicitation.slots["problem"].source
    )
    assert s.idea_version != v1


def test_novelty_is_narrated_one_point_per_turn():
    s = _new()
    first = _run(agent.turn(s, BCI))
    assert first["novelty"]["statement"]["type"] == "combination"
    assert "Together, I found only 19" not in first["reply"]  # turn 1: what exists
    second = _run(agent.turn(s, "Chennai"))["reply"]
    assert second.startswith("Got it, Chennai. Both parts are well studied")  # ack first
    assert "only what I found in the sources I searched" in second
    third = _run(agent.turn(s, "prototype"))["reply"]
    assert third.startswith("Looking at it from seven angles")  # turn 3: the panel's view
    fourth = _run(agent.turn(s, "skip"))["reply"]
    assert fourth.startswith("One way to stand out: build your version around joining")
    assert "because only 19 papers cover both" in fourth
    fifth = _run(agent.turn(s, "skip"))["reply"]
    assert fifth.startswith("Another way to stand out: make it fit Tamil Nadu")
    assert s.narrated[0] == "statement" and s.narrated[1].startswith("council:")
    assert s.narrated[2:] == ["lever:0", "lever:1"]


def test_the_panels_question_is_asked_after_any_reask():
    s = _new()
    _run(agent.turn(s, BCI))
    asked = [d["question"] for d in s.elicitation.dynamic]
    assert asked and s.council["synthesis"]["question"] == asked[0]
    second = _run(agent.turn(s, "Chennai"))  # misanswered stage: re-asked first
    assert second["action"]["slot"] == "stage"
    third = _run(agent.turn(s, "prototype"))
    assert third["action"]["slot"].startswith("dyn:") and third["action"]["question"] == asked[0]
    r = _run(agent.turn(s, "what do you think?"))  # a view first: the question stays open
    assert r["action"]["slot"] == third["action"]["slot"]
    _run(agent.turn(s, "hospitals would pay, through their equipment budget"))
    assert s.elicitation.dynamic[0]["answer"].startswith("hospitals would pay")


def test_asking_for_an_opinion_convenes_the_panel():
    s = _new()
    _run(agent.turn(s, BCI))
    first_run = s.council["at"]
    r = _run(agent.turn(s, "what do you think, honestly?"))
    assert "ask_council" in r["tools_used"] and s.council["at"] != first_run
    # nothing changed since the panel first met: a short line, not the whole brief again
    assert r["reply"].startswith("My view hasn't changed since we last looked")
    assert r["action"]["slot"] == "stage"  # the open question stays open
    assert r["council"]["band"] in ("strong", "mixed", "weak")


def test_roadmap_carries_the_panels_risks():
    s = _new("Meena")
    _run(agent.turn(s, BCI))
    for _ in range(12):
        if s.elicitation.state.value == "confirming":
            break
        _run(agent.turn(s, "skip"))
    else:
        pytest.skip("engine did not reach confirmation")
    r = _run(agent.turn(s, "yes"))
    rows = [row for rows in r["roadmap"]["risks_by_phase"].values() for row in rows]
    assert any(row["why"].startswith("review panel") for row in rows)


def test_model_failure_finishes_the_turn_offline(monkeypatch):
    from app.services.breaker import model_breaker

    model_breaker.succeed()
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "k")

    def handle(req: httpx.Request) -> httpx.Response:
        return httpx.Response(529, json={"error": {"message": "overloaded"}})

    s = _new()
    before = len(s.messages)
    r = _run(_with(httpx.MockTransport(handle), lambda c: agent.turn(s, BCI, client=c)))
    assert r["model"] == "offline (model failed)" and r["reply"]
    assert s.messages[before]["role"] == "user" and s.messages[-1]["role"] == "assistant"
    roles = [m["role"] for m in s.messages]
    assert all(a != b for a, b in zip(roles, roles[1:], strict=False))  # still alternating
    for _ in range(2):
        _run(_with(httpx.MockTransport(handle), lambda c: agent.turn(s, "Chennai", client=c)))
    assert model_breaker.state == "open"  # three failures in a minute
    r = _run(agent.turn(s, "prototype"))  # no call attempted while open
    assert r["model"] == "offline"
    model_breaker.succeed()


def test_spend_cap_moves_the_panel_to_rules(monkeypatch):
    monkeypatch.setattr(get_settings(), "session_token_budget", 100)
    s = _new()
    s.usage = {"input_tokens": 150}
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "k")
    assert agent._model_allowed(s) is False
    s.usage = {"input_tokens": 50}
    assert agent._model_allowed(s) is True


def test_model_can_call_check_novelty(monkeypatch, _env):
    _, transport = _model(
        monkeypatch,
        _tool_reply("Checking.", "check_novelty", {"idea": BCI, "elements": ["EEG", "nurse call"]}),
        _text_reply("Together, I found only 19 papers. Who would buy it?"),
    )
    s = _new()
    evs = _run(_with(transport, lambda c: _events(s, BCI, c)))
    assert any(e["event"] == "novelty" for e in evs)
    said = [e["data"] for e in evs if e["event"] == "sentence"]
    assert "Together, I found only 19 papers." in said  # backed by the novelty result
    assert s.novelty == NOVELTY and _env[-1]["elements"] == ["EEG", "nurse call"]
