"""The elicitation turn loop (Req 1.2 AC4).

These tests exist because the defect they guard against was architectural: the
old code generated clarifying questions and had no way to receive answers. The
central assertion here is simply that a conversation *converges* — that asking
and answering actually moves the session toward a clear objective and stops.
"""

from __future__ import annotations

from app.elicitation import engine
from app.elicitation.extract import extract
from app.elicitation.selector import Q_MAX, candidates, is_objective_clear, question_value
from app.elicitation.session import SessionState, Source
from app.elicitation.slots import REQUIRED_BY_MODE, EntryMode, Sector


def _run(opening: str, *, profile=None, max_turns: int = 20):
    """Drive a full conversation, answering every question plausibly."""
    s = engine.start("u1", profile=profile)
    engine.observe(s, opening)
    asked: list[str] = []
    for _ in range(max_turns):
        act = engine.step(s)
        if act.kind != "ask":
            return s, asked, act
        asked.append(act.slot)
        engine.observe(s, _answer_for(act.slot), answering=act.slot)
    raise AssertionError("conversation did not converge")


def _answer_for(slot: str) -> str:
    return {
        "sector": "textile",
        "product_form": "physical",
        "district": "Erode",
        "beneficiary": "small weavers who sell locally",
        "stage": "prototype",
        "capital_band": "10L_50L",
        "funding_route": "debt",
        "problem": "weavers cannot reach buyers outside the district",
        "solution": "a shared dyeing and finishing unit",
    }.get(slot, "yes")


# ---------------------------------------------------------------- extraction


def test_extraction_captures_real_text_not_placeholders():
    """The old extractor wrote the literal string 'solution described'."""
    out = {
        e.key: e.value
        for e in extract(
            "The problem is weavers in Erode cannot reach buyers. "
            "I want to start a textile finishing unit with 15 lakh from a bank loan."
        )
    }
    assert out["sector"] is Sector.TEXTILE
    assert "weavers" in str(out["problem"]).lower()
    assert str(out["problem"]) != "problem described"
    assert out["capital_band"].value == "10L_50L"
    assert out["funding_route"].value == "debt"


def test_bare_number_is_not_read_as_money():
    """'3 employees' must not become a ₹3 budget."""
    keys = {e.key for e in extract("We are 3 people working on this")}
    assert "capital_band" not in keys


def test_loose_guess_stays_below_fill_threshold():
    """A positional guess must be confirmed, never silently assumed."""
    got = [
        e for e in extract("something about helping local shops sell online") if e.key == "problem"
    ]
    assert got and got[0].confidence < 0.60


# ---------------------------------------------------------------- turn loop


def test_conversation_converges_and_stops():
    s, asked, act = _run("I want to start a textile unit in Erode")
    assert act.kind == "confirm"
    assert s.state is SessionState.CONFIRMING
    assert not s.missing
    assert len(asked) == len(set(asked)), "a slot was asked twice"


def test_answer_actually_lands_in_the_session():
    """The defect: questions were generated with nowhere to send an answer."""
    s = engine.start("u1")
    engine.observe(s, "I want to build something")
    act = engine.step(s)
    assert act.kind == "ask" and act.slot
    before = s.slots.get(act.slot)
    engine.observe(s, _answer_for(act.slot), answering=act.slot)
    after = s.slots.get(act.slot)
    assert after is not None
    assert after.source is Source.ANSWER
    assert before is None or after.confidence >= before.confidence


def test_profile_prefill_is_never_re_asked():
    s, asked, _ = _run(
        "I want to start a textile unit",
        profile={"district": "Erode", "founder_years": 12},
    )
    assert "district" not in asked, "re-asked a fact the profile already had"
    assert s.slots["district"].source is Source.PROFILE


def test_direct_answer_outranks_earlier_extraction():
    s = engine.start("u1")
    engine.observe(s, "some software idea")  # weak extraction
    engine.observe(s, "physical", answering="product_form")
    assert s.slots["product_form"].source is Source.ANSWER


def test_skip_is_not_asked_again():
    s = engine.start("u1")
    engine.observe(s, "I want to start something in textiles")
    act = engine.step(s)
    target = act.slot
    engine.skip(s, target)
    assert target not in candidates(s)
    for _ in range(12):
        act = engine.step(s)
        if act.kind != "ask":
            break
        assert act.slot != target, "a skipped slot came back"
        engine.observe(s, _answer_for(act.slot), answering=act.slot)


def test_required_precede_enriching():
    s = engine.start("u1")
    engine.observe(s, "textile unit in Erode")
    req = REQUIRED_BY_MODE[EntryMode.IDEA]
    act = engine.step(s)
    assert act.slot in req


# ---------------------------------------------------------------- stopping


def test_budget_exhaustion_stops_but_names_the_gaps():
    """Must not silently pretend the objective is clear."""
    s = engine.start("u1")
    engine.observe(s, "hello")
    for _ in range(Q_MAX):
        act = engine.step(s)
        if act.kind != "ask":
            break
        engine.observe(s, "not sure", answering=None)  # answers nothing
    d = is_objective_clear(s)
    assert d.stop and d.reason == "budget_exhausted"
    assert d.unfilled, "stopped without reporting what is still unknown"


def test_restatement_names_the_gaps():
    s = engine.start("u1")
    engine.observe(s, "a textile idea")
    text = engine.restate(s)
    assert "don't know" in text


def test_confirm_rejection_returns_to_eliciting():
    s, _, act = _run("I want to start a textile unit in Erode")
    assert act.kind == "confirm"
    nxt = engine.confirm(s, accepted=False)
    assert s.state in (
        SessionState.ELICITING,
        SessionState.AWAITING_ANSWER,
        SessionState.CONFIRMING,
    )
    assert nxt.kind in ("ask", "confirm")


def test_confirm_acceptance_hands_off_to_generation():
    """The client's requirement: ideation flows automatically into roadmap."""
    s, _, _ = _run("I want to start a textile unit in Erode")
    act = engine.confirm(s, accepted=True)
    assert act.kind == "generate"
    assert s.state is SessionState.GENERATING


# ---------------------------------------------------------------- value fn


def test_district_does_not_outrank_problem():
    """The R&D's key finding: scoring over raw domain size (38 districts)
    made the bot open by asking which district you live in."""
    s = engine.start("u1")
    assert question_value("problem", s) > question_value("district", s)


def test_experience_mode_drops_idea_slots():
    """Req 1.6 — the user has no idea yet; that is the point."""
    req = REQUIRED_BY_MODE[EntryMode.EXPERIENCE]
    assert "problem" not in req and "solution" not in req
    assert "founder_skills" in req and "founder_years" in req


# ---------------------------------------------------------------- answer check


def test_wrong_type_answer_is_routed_and_asked_once_more():
    """'Chennai' answered to the stage question was stored as the stage."""
    s = engine.start("u1")
    engine.observe(s, "I want to build a nurse alert device for paralysed patients")
    engine.observe(s, "Chennai", answering="stage")
    assert s.slots["district"].value == "chennai"
    assert "stage" not in s.slots
    act = engine.step(s)
    assert act.slot == "stage" and act.question.startswith("Got it, Chennai.")
    engine.observe(s, "Madurai", answering="stage")  # second miss: drop it for good
    assert "stage" in s.skipped and engine.step(s).slot != "stage"


def test_valid_direct_answers_are_typed():
    from app.elicitation.answers import validate

    assert validate("stage", "we have a prototype") == "prototype"
    assert validate("district", "Trichy") == "tiruchirappalli"
    assert validate("team_size", "three of us") == 3
    assert validate("team_size", "yes") is None
    assert validate("problem", "Chennai") is None
    assert validate("stage", "skip") is None
