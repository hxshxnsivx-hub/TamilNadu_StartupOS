"""The panel ranks the levers, in the conversation (task 1.3.1).

Narration follows the panel's order and remembers levers by their stable ids
(R041); no verdict before the search has finished (R068); a private session's idea
reaches no model seat; the ranked levers reach the model through council_brief.
"""

from __future__ import annotations

import asyncio
import copy

import pytest
from app.agents import ideation as agent
from app.agents import providers, tools
from app.core.config import get_settings
from app.research import levers

from tests.unit.test_ideation_agent import NOVELTY, SCAN

COPRA = "a solar dryer for copra so coconut farmers get a better price"
FOUR = [
    {"kind": "combine", "facts": {"a": "solar dryer", "b": "copra", "papers": 4}},
    {"kind": "localise", "facts": {"india_papers": 5, "world_papers": 900, "tn_scope": "x"}},
    {"kind": "cost-down", "facts": {"domain": None}},
    {"kind": "business model", "facts": {}},
]


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    st = get_settings()
    monkeypatch.setattr(st, "anthropic_api_key", "")
    monkeypatch.setattr(st, "gemini_api_key", "")


def _session(novelty: dict | None = None) -> agent.AgentSession:
    s = agent.new_session("Kavya")[0]
    s.idea = COPRA
    s.scan = copy.deepcopy(SCAN)
    s.novelty = novelty or {**copy.deepcopy(NOVELTY), "levers": [dict(x) for x in FOUR]}
    s.narrated += ["statement", "council:x"]
    return s


def _said(s: agent.AgentSession) -> list[str]:
    out = []
    while (line := agent._next_novelty_point(s)) is not None:
        out.append(line)
    return out


def _order(s: agent.AgentSession, *kinds: str) -> None:
    ids = {lv["kind"]: levers.lever_id(lv) for lv in s.novelty["levers"]}
    vote = {"band": "mixed", "stances": {}, "blockers": [], "variants": []}
    s.council = {"at": "x", "vote": {**vote, "lever_order": [ids[k] for k in kinds]}}


def test_the_narrator_speaks_the_top_three_of_the_panels_order():
    s = _session()
    _order(s, "business model", "cost-down", "localise", "combine")
    said = _said(s)
    assert len(said) == 3
    assert said[0].startswith("One way to stand out: compete on how it is delivered")
    assert said[1].startswith("Another way to stand out: compete on cost")
    assert "fit Tamil Nadu" in said[2] and not any("joining" in x for x in said)


def test_a_reorder_after_a_lever_was_said_neither_repeats_nor_skips_it():
    """R041: levers were tracked by place, so after the panel reordered them the three
    the founder heard were still the first three of the list, and the lever the panel
    ranked third was never spoken. The one already said is not repeated either."""
    s = _session()
    first = agent._next_novelty_point(s)  # before the panel: the novelty check's order
    assert "joining solar dryer with copra" in first
    _order(s, "localise", "combine", "business model", "cost-down")
    rest = _said(s)
    assert len(rest) == 2 and not any("joining" in x for x in rest)  # said once, not twice
    assert rest[0].startswith("Another way to stand out: make it fit Tamil Nadu")
    # the panel's third, not the list's third (which was the cost-down lever)
    assert rest[1].startswith("Another way to stand out: compete on how it is delivered")
    assert "compete on cost" not in rest[1]


def test_a_saved_session_with_positional_marks_is_upgraded():
    s = _session()
    s.narrated.append("lever:0")
    back = agent.AgentSession.from_dict(s.to_dict())
    assert "lever:0" not in back.narrated
    assert f"lever:{levers.lever_id(FOUR[0])}" in back.narrated
    assert not any("joining" in x for x in _said(back))


def test_no_panel_before_the_search_has_finished(monkeypatch):
    """R068: asked for an opinion while the search runs, the panel gave 'serious
    concerns' built on no evidence. Now it waits for the search."""
    monkeypatch.setattr(get_settings(), "research_wait_s", 0.05)

    async def slow_scan(text, **_kw):
        await asyncio.sleep(5)
        return SCAN

    monkeypatch.setattr("app.research.scan.scan", slow_scan)
    s = agent.new_session("Kavya")[0]
    r = asyncio.run(agent.turn(s, f"I want to build {COPRA}. What do you think?"))
    assert s.council is None and "ask_council" not in r["tools_used"]
    assert agent.PANEL_AFTER_SEARCH in r["reply"]
    assert "concerns" not in r["reply"]
    assert asyncio.run(agent._convene(agent.new_session("Kavya")[0])) is None


def test_the_models_ask_council_waits_for_the_search():
    async def never(idea):
        raise AssertionError("the panel ran with no evidence")

    s = agent.new_session("Kavya")[0]
    state = {"last_scan": None, "convene": never}
    r = asyncio.run(tools.run_tool("ask_council", {"idea": COPRA}, s.elicitation, state))
    assert r["status"] == "waiting for the search"


def test_a_private_session_sends_its_idea_to_no_model_seat(monkeypatch):
    """R015 for the panel (decision 0004): private mode judges with rule seats."""
    seen: list = []

    async def fake_convene(idea, slots, **kw):
        seen.append(kw["use_model"])
        return {}

    monkeypatch.setattr(providers, "judge", lambda: providers.PROVIDERS["anthropic"])
    monkeypatch.setattr(agent.council, "convene", fake_convene)
    for private in (True, False):
        s = _session()
        s.private = private
        asyncio.run(agent._council_work(s)())
    assert seen == [False, True]


def test_the_model_hears_the_panels_top_levers():
    from app.agents.council import convene

    nov = {**copy.deepcopy(NOVELTY), "levers": [dict(x) for x in FOUR]}
    r = asyncio.run(convene(COPRA, {}, scan=SCAN, novelty=nov, use_model=False))
    brief = tools.council_brief(r)
    top = r["vote"]["lever_order"][0]
    assert len(brief["levers"]) == 3
    assert brief["levers"][0] == r["evidence"][f"novelty:lever:{top}"]["text"]
