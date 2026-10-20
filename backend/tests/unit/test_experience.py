"""The entry for founders with experience but no idea (task 1.1.5): the session
starts in the experience conversation (1.1.5.1), asks about the founder in their
own words and leaves money for later (R089), searches nothing until an idea
exists (R118), and ends in a choice among cited opportunity cards (R066) whose
pick fills the idea slots (1.1.5.5). The ranking itself (1.1.5.3) waits on the
sector taxonomy, so with no card to offer the conversation says so."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest
from app.agents import ideation as agent
from app.agents import store
from app.elicitation import engine
from app.elicitation.selector import Q_MAX
from app.elicitation.session import SessionState, Source
from app.elicitation.slots import BY_KEY, SLOTS, EntryMode
from app.models.enums import EntryMode as Door
from app.planner import opportunities
from app.voice import phrasebook
from httpx import AsyncClient
from pydantic import ValidationError

from tests.unit import test_ideation_agent as agent_tests
from tests.unit.test_ideation_agent import _model, _text_reply, _with

URL = "/api/v1/ideation/agent/sessions"
# the scan and novelty stand-ins: an autouse fixture that records every search
_env = agent_tests._env
START = Path(__file__).resolve().parents[3] / "frontend" / "src" / "pages" / "Start.tsx"

SELF = "I worked 12 years as a cook in hotels in Salem"
ANSWERS = {
    "sector": "food",
    "product_form": "a product",
    "district": "Salem",
    "founder_years": "12",
    "owned_assets": "a gas stove and a van",
    "motivation": "a steady income",
}
CARD = {
    "id": "millet_snacks",
    "label": "Millet snack unit",
    "problem": "Schools in Salem need affordable healthy snacks",
    "solution": "Make packaged millet snacks for school canteens",
    "sector": "food",
    "product_form": "physical",
    "beneficiary": "school canteens",
    "skills_used": ["cooking"],
    "assets_used": ["gas stove"],
    "sources": [{"title": "TN millet mission notice", "url": "https://example.org/millets"}],
    "review": "approved",
}


def _run(coro):
    return asyncio.run(coro)


def _experience(**kw) -> agent.AgentSession:
    return agent.new_session("Murugan", entry_mode=Door.INTENT_ONLY, **kw)[0]


def _talk_to_the_restatement(s: agent.AgentSession) -> list[tuple[str, str]]:
    """Answer every question the experience conversation asks; (slot, question)."""
    asked: list[tuple[str, str]] = []
    done = _run(agent.turn(s, SELF))
    for _ in range(12):
        act = done["action"]
        if act["kind"] != "ask":
            break
        asked.append((act["slot"], act["question"]))
        done = _run(agent.turn(s, ANSWERS.get(act["slot"], "skip")))
    return asked


def _searched(calls: list) -> list[str]:
    """The texts every recorded prior-art scan and novelty check ran on."""
    return [str(c.get("text") or c.get("novelty") or "") for c in calls]


# ---- 1.1.5.1 / 1.1.5.2: the session starts in the experience conversation ------------


@pytest.mark.parametrize("door", [Door.DOMAIN_ONLY, Door.INTENT_ONLY])
def test_a_founder_with_no_idea_gets_the_experience_conversation(door):
    s, greeting = agent.new_session("Murugan", entry_mode=door)
    assert s.elicitation.mode is EntryMode.EXPERIENCE
    assert agent.OPENING_QUESTION not in greeting and "idea you are working on" not in greeting
    assert agent.EXPERIENCE_OPENING in greeting
    assert s.pending["slot"] == "founder_skills" and s.pending_slot == "founder_skills"
    assert s.elicitation.questions_asked == 0  # the opening uses no question, as for ideas
    back = agent.AgentSession.from_dict(s.to_dict())
    assert back.elicitation.mode is EntryMode.EXPERIENCE


def test_an_idea_or_no_entry_keeps_the_idea_conversation():
    assert agent.new_session("K", entry_mode=Door.IDEA)[0].elicitation.mode is EntryMode.IDEA
    assert agent.new_session("K")[0].elicitation.mode is EntryMode.IDEA


def test_a_domain_only_founder_starts_with_the_domain_filled():
    s = agent.new_session("K", entry_mode=Door.DOMAIN_ONLY, profile={"sector": "textiles"})[0]
    assert s.elicitation.slots["sector"].source is Source.PROFILE


def test_the_first_reply_is_the_founders_skills_not_an_idea():
    s = _experience()
    _run(agent.turn(s, SELF))
    sv = s.elicitation.slots["founder_skills"]
    assert sv.source is Source.ANSWER
    assert s.idea == ""  # R118: a self-description is not the idea
    # nor is it guessed into the idea's slots: there is no problem yet
    assert not {"problem", "solution", "beneficiary"} & set(s.elicitation.slots)


@pytest.mark.skipif(not START.exists(), reason="frontend not checked out")
def test_start_sends_no_idea_founders_to_the_conversation_not_to_schemes():
    src = START.read_text(encoding="utf8")
    finish = re.search(r"function finish\(\)[\s\S]*?\n  }", src)
    assert finish and '"/talk"' in finish.group(0) and '"/schemes"' not in finish.group(0)


# ---- R089: experience questions in their own words, money later ---------------------


def test_experience_questions_are_about_the_founder_and_never_about_money(_env):
    s = _experience(profile={"district": "salem"})
    asked = _talk_to_the_restatement(s)
    slots = [k for k, _ in asked]
    assert slots, "nothing was asked, so the test proved nothing"
    assert not {"capital_band", "funding_route", "problem", "solution", "beneficiary"} & set(slots)
    assert "stage" not in slots  # no idea yet: the first stage is assumed, not asked
    for key, question in asked:
        assert question.endswith(BY_KEY[key].question_for(EntryMode.EXPERIENCE)), question
    assert "Which sector does this sit in?" not in [q for _, q in asked]
    assert s.elicitation.questions_asked <= Q_MAX
    assert s.elicitation.state is SessionState.CONFIRMING
    assert "the idea stage" in s.elicitation.objective  # said back as assumed


def test_the_experience_conversation_asks_what_the_founder_can_do_first():
    s = engine.start("u", mode=EntryMode.EXPERIENCE)
    assert engine.step(s).slot == "founder_skills"
    engine.observe(s, "tailoring and embroidery", answering="founder_skills")
    assert engine.step(s).slot != "founder_skills"


def test_the_idea_conversation_keeps_its_words():
    for slot in SLOTS:
        assert slot.question_for(EntryMode.IDEA) == slot.question
    assert BY_KEY["sector"].question_for(EntryMode.EXPERIENCE) != BY_KEY["sector"].question


def test_the_experience_questions_are_in_the_recording_list():
    texts = {r["text"] for r in phrasebook.wanted() if r["language"] == "en-IN"}
    assert agent.EXPERIENCE_OPENING in texts


# ---- R118: no research on a self-description ----------------------------------------


def test_the_experience_conversation_searches_nothing(_env):
    s = _experience()
    _talk_to_the_restatement(s)
    assert _env == []  # no prior-art scan, no novelty check
    assert s.scan is None and s.novelty is None and s.idea == ""
    restated = s.elicitation.objective
    assert "problem" not in restated and "Your plan" not in restated  # no idea to restate


def test_the_model_cannot_note_an_idea_before_there_is_one():
    from app.agents import tools

    s = _experience()
    s.elicitation.record(user_text=SELF, asked="founder_skills")
    out = tools._note_fact("problem", SELF, s.elicitation)
    assert "rejected" in out and "problem" not in s.elicitation.slots


def test_a_guess_held_before_the_switch_is_not_the_idea():
    """A session saved before observe stopped guessing idea slots: the switch to
    the idea conversation drops the guess, never a founder-given value."""
    el = engine.start("u", mode=EntryMode.EXPERIENCE)
    el.put("problem", SELF, 0.7, Source.EXTRACTED)
    el.put("beneficiary", "hotel guests", 0.9, Source.ANSWER)
    engine.continue_with_idea(el)
    assert "problem" not in el.slots and el.slots["beneficiary"].source is Source.ANSWER


def test_the_model_cannot_search_or_judge_before_an_idea(monkeypatch):
    sent, transport = _model(monkeypatch, _text_reply("Thank you. How many years was that?"))
    s = _experience()
    _run(_with(transport, lambda c: agent.turn(s, SELF, client=c)))
    assert {t["name"] for t in sent[0]["tools"]} == {"note_fact"}
    assert "no idea yet" in sent[0]["system"]


# ---- R066 + 1.1.5.5: the choice, and its write-back ---------------------------------


def test_with_no_cited_card_the_choice_says_so_and_offers_an_idea(_env):
    s = _experience()
    _talk_to_the_restatement(s)
    done = _run(agent.turn(s, "yes"))
    assert done["action"]["kind"] == "choose"
    assert s.elicitation.state is SessionState.CHOOSING
    assert done["reply"] == agent.NO_CARDS and done["cards"] == []
    assert s.pending["kind"] == "choose_card" and s.pending["options"] == []
    assert s.roadmap is None and _env == []  # nothing built on a self-description
    # it survives a reload, and the screen sees the choice
    back = agent.AgentSession.from_dict(s.to_dict())
    assert back.elicitation.state is SessionState.CHOOSING
    assert agent.snapshot(back)["pending"]["kind"] == "choose_card"
    d = s.to_dict()
    del d["pending"]  # an old document: the choice is rebuilt
    assert agent.AgentSession.from_dict(d).pending["kind"] == "choose_card"
    # a yes starts the idea conversation, keeping what was said
    done = _run(agent.turn(s, "yes please"))
    assert done["action"]["kind"] == "ask" and done["action"]["question"] == agent.OPENING_QUESTION
    assert s.elicitation.mode is EntryMode.IDEA
    assert s.elicitation.slots["founder_skills"].source is Source.ANSWER
    assert s.elicitation.questions_asked == 0
    assert _env == [] and s.idea == ""  # a bare yes is no idea: nothing searched
    assert "problem" not in s.elicitation.slots
    idea = "I want to make ready to cook millet dosa batter for families in Salem"
    _run(agent.turn(s, idea))
    assert s.idea == idea
    assert _env, "the idea conversation searches once there is an idea"
    assert not any(SELF in text for text in _searched(_env))
    assert SELF not in str(s.elicitation.slots["problem"].value)


def test_a_no_at_the_choice_stops_without_inventing(_env):
    s = _experience()
    _talk_to_the_restatement(s)
    _run(agent.turn(s, "yes"))
    done = _run(agent.turn(s, "no"))
    assert done["reply"] == agent.DECLINED and done["action"]["kind"] == "choose"
    assert s.elicitation.state is SessionState.CHOOSING and s.roadmap is None


def test_an_idea_told_at_the_choice_is_read_as_the_idea(_env):
    s = _experience()
    _talk_to_the_restatement(s)
    _run(agent.turn(s, "yes"))
    text = "I could run a tiffin delivery service for office workers"
    _run(agent.turn(s, text))
    assert s.elicitation.mode is EntryMode.IDEA and s.idea == text
    assert not any(SELF in t for t in _searched(_env))  # the idea is searched, not the cook
    problem = s.elicitation.slots.get("problem")
    assert problem is None or SELF not in str(problem.value)
    assert SELF not in (s.elicitation.objective or "")


def test_a_picked_card_fills_the_idea_slots(monkeypatch, _env):
    card = opportunities.Card.model_validate(CARD)
    monkeypatch.setattr(opportunities, "rank", lambda facts: [card, card])
    s = _experience()
    _talk_to_the_restatement(s)
    before = s.idea_version
    done = _run(agent.turn(s, "yes"))
    assert done["action"]["kind"] == "choose"
    assert [c["id"] for c in done["cards"]] == ["millet_snacks"]  # each card once
    assert "Millet snack unit, from TN millet mission notice" in done["reply"]
    assert s.pending["options"] == ["millet_snacks"]
    _run(agent.turn(s, "number one"))
    el = s.elicitation
    for key in ("problem", "solution", "sector", "product_form", "beneficiary"):
        assert el.slots[key].source is Source.CHOSEN, key
    assert el.slots["problem"].value == CARD["problem"]
    assert el.mode is EntryMode.IDEA and s.chosen == "millet_snacks"
    assert s.idea == opportunities.idea_text(card) and s.idea_version != before
    assert el.state is not SessionState.CHOOSING


def test_a_card_must_be_cited_and_reviewed():
    for broken in ({"sources": []}, {"review": "draft"}, {"skills_used": []}):
        with pytest.raises(ValidationError):
            opportunities.Card.model_validate({**CARD, **broken})


def test_the_ranking_waits_for_the_taxonomy():
    assert opportunities.rank({"founder_skills": ["cooking"]}) == []


def test_the_restatement_says_back_what_the_choice_wrote():
    s = engine.start("u", mode=EntryMode.EXPERIENCE)
    s.state = SessionState.CHOOSING
    engine.choose(s, opportunities.idea_slots(opportunities.Card.model_validate(CARD)))
    assert s.mode is EntryMode.IDEA
    assert "From the opportunity you chose" in engine.restate(s)


# ---- the API ------------------------------------------------------------------------


async def test_api_starts_the_experience_conversation(client: AsyncClient):
    store.set_store(store.MemoryStore())
    try:
        r = await client.post(URL, json={"name": "Murugan", "entry_mode": "intent_only"})
        assert r.status_code == 200 and agent.EXPERIENCE_OPENING in r.json()["reply"]
        snap = (await client.get(f"{URL}/{r.json()['session_id']}")).json()
        assert snap["entry_mode"] == "intent_only" and snap["cards"] == []
        assert snap["pending"]["slot"] == "founder_skills"
    finally:
        store.set_store(None)
