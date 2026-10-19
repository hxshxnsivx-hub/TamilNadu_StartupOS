"""Question order and fact safety (task 1.1.3).

Arena findings covered: R007 (typed slots), R009 (a budget counted in
questions), R053 (put reports what happened), R070 (negated stage words),
R063 (corrections in passing, which place is meant), R113 (the WHY finger),
R119 (greedy unless a budget binds) and R157 (three confidence bands).
"""

from __future__ import annotations

import asyncio
import itertools

from app.agents import tools
from app.agents.ideation import AgentSession
from app.core.stages import Stage
from app.elicitation import engine, selector
from app.elicitation.answers import validate
from app.elicitation.extract import extract
from app.elicitation.places import find_district
from app.elicitation.selector import Q_MAX, candidates, is_objective_clear, select_next
from app.elicitation.session import ElicitationSession, Outcome, Source
from app.elicitation.slots import (
    BY_KEY,
    REQUIRED_BY_MODE,
    TAU_CONFIRM,
    TAU_FILL,
    Band,
    EntryMode,
    Finger,
    Sector,
    band,
)
from app.planner.plan import build_plan

WHAT = {k for k, s in BY_KEY.items() if s.finger is Finger.WHAT}
WHY = {"why_now", "differentiation", "motivation"}


def _note(s: ElicitationSession, key: str, value) -> dict:
    return asyncio.run(tools.run_tool("note_fact", {"key": key, "value": value}, s, {}))


def _said(text: str) -> ElicitationSession:
    s = engine.start("u1")
    engine.observe(s, text)
    return s


# ---- 1.1.3.1 the finger gate: what before anything else ------------------------------


def test_nothing_is_asked_before_the_idea_is_known():
    s = engine.start("u1")
    engine.observe(s, "hello")
    asked = []
    for _ in range(4):
        act = engine.step(s)
        assert act.kind == "ask"
        asked.append(act.slot)
        if act.slot in ("problem", "solution"):
            break
        engine.observe(
            s, {"sector": "textile", "product_form": "physical"}[act.slot], answering=act.slot
        )
    assert set(asked) <= WHAT, f"asked {asked} before the idea was known"
    assert asked[-1] in ("problem", "solution")


def test_the_gate_opens_once_the_idea_is_known():
    s = _said("I want to start a textile finishing unit for small weavers")
    assert engine.step(s).slot not in WHAT  # the pitch gave the what


def test_the_gate_never_stalls_when_every_what_question_is_skipped():
    s = engine.start("u1")
    for key in WHAT:
        s.skip(key)
    act = engine.step(s)
    assert act.kind == "ask" and act.slot not in WHAT


# ---- 1.1.3.2 a model-noted fact must be in the founder's words ------------------------


def test_a_noted_text_fact_must_be_a_span_of_the_founders_words():
    s = _said("We help small weavers in Erode reach buyers in other states")
    assert _note(s, "beneficiary", "Small weavers in Erode.") == {"recorded": "beneficiary"}
    out = _note(s, "solution", "an AI powered marketplace for exporters")
    assert out["rejected"] == "solution" and "words" in out["reason"]
    assert "solution" not in s.slots


def test_a_noted_district_must_have_been_named():
    s = _said("We help small weavers in Erode reach buyers")
    assert _note(s, "district", "madurai")["rejected"] == "district"
    assert s.slots["district"].value == "erode"
    s2 = _said("hello")
    assert "rejected" in _note(s2, "district", "erode")


def test_noted_skills_must_each_have_been_said():
    s = _said("I have done weaving and dyeing for years")
    assert _note(s, "founder_skills", ["weaving", "dyeing"]) == {"recorded": "founder_skills"}
    assert "rejected" in _note(s, "owned_assets", ["a lathe"])


# ---- R007 typed slots -------------------------------------------------------------------


def test_put_coerces_each_value_to_its_slot_type():
    s = engine.start("u1")
    assert s.put("team_size", "about five", 0.8, Source.EXTRACTED).outcome is Outcome.STORED
    s.put("sector", "healthtech", 0.8, Source.EXTRACTED)
    s.put("district", "Tiruppur", 0.8, Source.EXTRACTED)
    s.put("stage", Stage.MVP, 0.8, Source.EXTRACTED)
    s.put("founder_skills", "weaving, dyeing", 0.8, Source.EXTRACTED)
    got = {k: v.value for k, v in s.slots.items()}
    assert got == {
        "team_size": 5,
        "sector": Sector.HEALTH,
        "district": "tiruppur",
        "stage": "mvp",
        "founder_skills": ["weaving", "dyeing"],
    }


def test_put_rejects_values_that_fit_no_slot():
    s = engine.start("u1")
    bad = {
        "stage": "early stage startup",
        "sector": "banana",
        "district": "Mumbai",
        "founder_years": 99,
        "team_size": True,
        "problem": {"text": "x"},
        "not_a_slot": "x",
    }
    for key, value in bad.items():
        assert s.put(key, value, 0.8, Source.EXTRACTED).outcome is Outcome.REJECTED, key
    assert s.slots == {}


def test_bad_model_notes_never_break_the_roadmap():
    s = _said("I want to make banana chips in Trichy with about five people")
    for key, value in (
        ("team_size", "about five"),
        ("founder_years", "ten years"),
        ("stage", "early"),
    ):
        _note(s, key, value)
    slots = {k: getattr(v.value, "value", v.value) for k, v in s.slots.items()}
    assert isinstance(slots["team_size"], int) and isinstance(slots["founder_years"], int)
    assert "stage" not in slots or slots["stage"] in {x.value for x in Stage}
    build_plan("banana chips", slots)  # raised TypeError on 'about five'


def test_the_note_tool_names_the_allowed_values():
    desc = next(t for t in tools.TOOLS if t["name"] == "note_fact")["description"]
    assert "it_services" in desc and "prototype" in desc and "under_2L" in desc


# ---- R053 / 1.1.3.3 put reports the outcome; disagreement goes to the founder ----------


def test_a_disagreeing_note_is_reported_and_makes_the_slot_a_question():
    s = _said("A microprocessor trainer kit for farm colleges")
    assert s.slots["sector"].value is Sector.AGRI  # a cue in passing
    out = _note(s, "sector", "electronics")
    assert out["disputed"] == "sector"
    assert s.slots["sector"].confidence < TAU_CONFIRM
    assert s.rivals["sector"].value in (Sector.AGRI, Sector.ELECTRONICS)
    assert "sector" in candidates(s)
    engine.observe(s, "electronics", answering="sector")  # the founder settles it
    assert s.slots["sector"].value is Sector.ELECTRONICS and "sector" not in s.rivals


def test_a_dispute_is_settled_only_by_the_founder():
    s = engine.start("u1")
    s.put("sector", Sector.AGRI, 0.90, Source.EXTRACTED)
    assert s.put("sector", Sector.FOOD, 0.90, Source.EXTRACTED).outcome is Outcome.CONFLICT
    assert s.put("sector", Sector.FOOD, 0.95, Source.EXTRACTED).outcome is Outcome.CONFLICT
    assert s.slots["sector"].confidence < TAU_CONFIRM


def test_a_kept_founder_fact_is_reported_not_recorded():
    s = engine.start("u1", profile={"district": "Erode"})
    out = _note(s, "district", "madurai")  # span-check aside, the profile stands
    assert "recorded" not in out
    s.record(user_text="my cousin lives in Madurai")
    out = _note(s, "district", "madurai")
    assert out["kept"] == "district" and out["current"] == "erode"
    assert s.slots["district"].value == "erode"


def test_a_refinement_is_not_a_dispute():
    s = engine.start("u1")
    s.put("stage", "idea", 0.55, Source.EXTRACTED)
    assert s.put("stage", "prototype", 0.85, Source.EXTRACTED).outcome is Outcome.STORED
    assert s.put("stage", "prototype", 0.85, Source.EXTRACTED).outcome is Outcome.STORED
    assert "stage" not in s.rivals


def test_an_answer_to_another_question_does_not_replace_the_problem():
    """1.1.2 review: the beneficiary answer was read as a new problem at equal confidence."""
    s = _said("Weavers in Erode cannot reach buyers outside the district")
    problem = s.slots["problem"].value
    engine.observe(s, "small weavers who sell only in local markets", answering="beneficiary")
    assert s.slots["problem"].value == problem
    assert s.slots["beneficiary"].value == "small weavers who sell only in local markets"


# ---- R009 the budget counts questions ---------------------------------------------------


def test_re_asks_do_not_use_the_budget():
    s = _said("I want to start a textile unit")
    asked = []
    for _ in range(30):
        act = engine.step(s)
        if act.kind != "ask":
            break
        asked.append(act.slot)
        engine.observe(s, "not sure really", answering=act.slot)
    assert {"district", "beneficiary", "capital_band", "funding_route"} <= set(asked)
    assert s.questions_asked <= Q_MAX


def test_stepping_twice_asks_one_question():
    s = _said("hello")
    engine.step(s)
    engine.step(s)
    assert s.questions_asked == 1


def test_an_opinion_request_does_not_use_the_budget():
    s = _said("I want to start a textile unit")
    engine.step(s)
    engine.observe(s, "what do you think of it?")  # no answer, no new question
    assert s.questions_asked == 1


def test_a_reply_to_the_restatement_is_not_a_question():
    s = _said("I want to start a textile unit")
    for _ in range(30):
        act = engine.step(s)
        if act.kind != "ask":
            break
        engine.observe(s, "skip", answering=act.slot)
    n = s.questions_asked
    engine.reply(s, "hmm")
    assert s.questions_asked == n and s.refunds == 0


def test_an_old_session_document_counts_its_questions():
    s = _said("hello")
    engine.step(s)
    engine.observe(s, "textile", answering="sector")
    doc = s.model_dump(mode="json")
    doc.pop("questions_asked")
    doc.pop("open_question", None)
    assert ElicitationSession.model_validate(doc).questions_asked == 1


# ---- R070 negated stage words -----------------------------------------------------------


def test_a_negated_stage_word_is_not_the_stage():
    assert validate("stage", "no customers yet") is None
    assert validate("stage", "not selling yet") is None
    assert validate("stage", "we haven't launched") is None
    assert validate("stage", "customers illai") is None
    assert validate("stage", "we have a prototype but no customers yet") == "prototype"
    assert validate("stage", "not started yet") == "idea"
    assert validate("stage", "we are selling") == "revenue"
    stages = [e.value for e in extract("We don't have customers yet") if e.key == "stage"]
    assert "revenue" not in stages


# ---- R063 corrections in passing, and which place is meant ------------------------------


def test_the_place_the_founder_is_in_wins():
    assert find_district("I live in Salem but want to sell in Coimbatore") == "salem"
    assert find_district("sorry, actually I am in Salem, not Erode") == "salem"
    assert find_district("not Erode") is None
    assert find_district("Coimbatore and Salem") == "coimbatore"  # first named


def test_a_correction_in_passing_sticks():
    s = engine.start("u1")
    engine.observe(s, "Erode", answering="district")
    engine.observe(s, "sorry, actually I am in Salem, not Erode")
    assert s.slots["district"].value == "salem"
    assert s.slots["district"].source is Source.ANSWER


def test_an_aside_without_a_correction_word_is_still_only_a_rival():
    s = engine.start("u1")
    engine.observe(s, "Erode", answering="district")
    engine.observe(s, "my cousin sells in Salem")
    assert s.slots["district"].value == "erode"
    assert s.rivals["district"].value == "salem"


# ---- R113 the WHY finger ----------------------------------------------------------------


def _all_required(s: ElicitationSession) -> None:
    answers = {
        "problem": "weavers cannot reach buyers",
        "solution": "a shared finishing unit",
        "sector": "textile",
        "product_form": "physical",
        "beneficiary": "small weavers",
        "district": "Erode",
        "stage": "prototype",
        "capital_band": "10L_50L",
        "funding_route": "debt",
    }
    for key in REQUIRED_BY_MODE[EntryMode.IDEA]:
        s.put(key, validate(key, answers[key]), 0.90, Source.ANSWER)


def test_why_is_asked_when_nothing_said_it():
    s = engine.start("u1")
    _all_required(s)
    d = is_objective_clear(s)
    assert not d.stop and d.reason == "finger_uncovered"
    act = engine.step(s)
    assert act.kind == "ask" and act.slot in WHY


def test_why_said_in_the_pitch_needs_no_question():
    s = engine.start("u1")
    _all_required(s)
    engine.observe(s, "Unlike the big mills, we finish small batches within a day")
    assert "differentiation" in s.filled
    assert Finger.WHY in s.fingers
    assert is_objective_clear(s).reason in ("enrichment_available", "clear")


def test_why_cues_are_read():
    keys = {
        e.key: e.value for e in extract("Now that the state pays a 25% subsidy, the time is right")
    }
    assert "why_now" in keys
    keys = {e.key: e.value for e in extract("I want to carry on my father's business")}
    assert keys.get("motivation") is not None and keys["motivation"].value == "succession"


def test_skipped_why_questions_are_not_nagged():
    s = engine.start("u1")
    _all_required(s)
    for key in WHY:
        s.skip(key)
    assert is_objective_clear(s).reason in ("enrichment_available", "clear")


# ---- R119 greedy unless a burden budget binds -------------------------------------------


def test_greedy_is_the_default_and_matches_the_solver():
    keys = sorted(REQUIRED_BY_MODE[EntryMode.IDEA])
    for r in range(len(keys)):
        for filled in itertools.combinations(keys, r):
            s = engine.start("u1")
            s.put("problem", "weavers cannot reach buyers", 0.90, Source.ANSWER)
            for k in filled:
                s.put(
                    k,
                    validate(
                        k,
                        {
                            "sector": "textile",
                            "product_form": "physical",
                            "district": "Erode",
                            "stage": "prototype",
                            "capital_band": "10L_50L",
                            "funding_route": "debt",
                            "problem": "weavers cannot reach buyers",
                            "solution": "a shared finishing unit",
                            "beneficiary": "small weavers",
                        }[k],
                    ),
                    0.90,
                    Source.ANSWER,
                )
            plan = select_next(s)
            assert plan.status == "GREEDY"
            solved = selector._solve(s, candidates(s), horizon=3, burden_budget=9)
            assert solved.head == plan.head


def test_the_solver_runs_when_a_burden_budget_binds():
    s = engine.start("u1")
    s.put("problem", "weavers cannot reach buyers", 0.90, Source.ANSWER)
    plan = select_next(s, burden_budget=2)
    assert plan.status in ("OPTIMAL", "FEASIBLE", "GREEDY")
    burden = sum(selector.BURDEN_BY_KIND[BY_KEY[k].kind] for k in plan.plan)
    assert burden <= 2


def test_the_greedy_plan_keeps_required_before_enriching():
    s = engine.start("u1")
    s.put("problem", "weavers cannot reach buyers", 0.90, Source.ANSWER)
    plan = select_next(s, horizon=12)
    assert set(plan.plan) <= REQUIRED_BY_MODE[EntryMode.IDEA] | WHY  # WHY is in the contract
    assert plan.plan[-1] in WHY  # and comes after the required slots, by value


# ---- R157 three bands -------------------------------------------------------------------


def test_three_bands_known_confirm_unknown():
    assert band(0.90) is Band.KNOWN and band(TAU_FILL) is Band.KNOWN
    assert band(0.55) is Band.CONFIRM and band(TAU_CONFIRM) is Band.CONFIRM
    assert band(0.45) is Band.UNKNOWN


def test_a_confirm_band_fact_is_assumed_aloud_not_asked():
    s = engine.start("u1")
    s.put("sector", Sector.TEXTILE, 0.55, Source.ANSWER)
    assert "sector" in s.filled and "sector" not in candidates(s)
    assert "I assumed: a textile business" in engine.restate(s)


def test_an_unknown_band_fact_is_asked():
    s = engine.start("u1")
    s.put("sector", Sector.TEXTILE, 0.45, Source.EXTRACTED)
    assert "sector" not in s.filled and "sector" in candidates(s)


def test_a_session_round_trip_keeps_the_new_fields():
    s = _said("hello")
    engine.step(s)
    a = AgentSession(name="x", elicitation=s)
    back = AgentSession.from_dict(a.to_dict())
    assert back.elicitation.questions_asked == 1


# ---- review rework: tie-break, plan agrees with the restatement, Tamil script ----------


def test_at_a_tie_the_first_inference_stands_and_the_new_one_is_the_rival():
    s = engine.start("u1")
    s.put("sector", Sector.AGRI, 0.90, Source.EXTRACTED)
    s.put("sector", Sector.FINANCE, 0.90, Source.EXTRACTED)
    assert s.slots["sector"].value is Sector.AGRI
    assert s.rivals["sector"].value is Sector.FINANCE


def test_a_disputed_value_is_not_planned_on(monkeypatch):
    """A cold room's sector must not become finance because the founder said 'bank loan'."""
    s = _said(
        "Farmers in Erode lose tomatoes, so I want to build a solar cold room for agriculture"
    )
    assert s.slots["sector"].value is Sector.AGRI
    engine.observe(s, "bank loan", answering="funding_route")
    assert s.slots["sector"].value is Sector.AGRI and s.rivals["sector"].value is Sector.FINANCE
    s.skip("sector")
    assert "You skipped your sector; I will assume the sector your idea" in engine.restate(s)
    seen = {}

    def fake_plan(idea, slots, **kw):
        seen.update(slots)
        return {}

    monkeypatch.setattr(tools, "build_plan", fake_plan)
    tools._roadmap("solar cold room", None, s)
    assert "sector" not in seen  # the planner falls back, as the restatement says
    assert seen["funding_route"] == "debt" and seen["district"] == "erode"


def test_a_district_note_is_not_rejected_for_tamil_script_words():
    s = _said("நான் சேலத்தில் இருக்கிறேன்")
    assert _note(s, "district", "salem") == {"recorded": "district"}
    assert s.slots["district"].value == "salem"
    assert "rejected" in _note(_said("I am in Erode"), "district", "salem")
