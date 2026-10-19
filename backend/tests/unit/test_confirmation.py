"""Confirmation that shows where each fact came from, and corrections that stick (task 1.1.2).

Arena findings covered: R005 (the reply to the restatement ignored negation),
R025 (a later extraction replaced the founder's answer), R051 (skipped slots
vanished from the restatement) and R154 (facts the roadmap uses were never
restated).
"""

from __future__ import annotations

import asyncio

from app.agents import ideation as agent
from app.agents import tools
from app.elicitation import engine
from app.elicitation.confirmation import corrections, polarity, strip_negated
from app.elicitation.selector import Q_MAX
from app.elicitation.session import SessionState, Source
from app.elicitation.slots import REQUIRED_BY_MODE, EntryMode, FundingRoute, Sector

ANSWERS = {
    "problem": "weavers cannot reach buyers outside the district",
    "solution": "a shared dyeing and finishing unit",
    "sector": "textile",
    "product_form": "physical",
    "beneficiary": "small weavers who sell locally",
    "district": "Erode",
    "stage": "prototype",
    "capital_band": "10L_50L",
    "funding_route": "debt",
    "motivation": "income",  # the WHY finger (R113)
}


def _confirming(profile: dict | None = None):
    """A session that answered every question and now sees the restatement."""
    s = engine.start("u1", profile=profile)
    engine.observe(s, "I want to start a finishing unit")  # the sector is asked, then answered
    for _ in range(20):
        act = engine.step(s)
        if act.kind != "ask":
            break
        engine.observe(s, ANSWERS.get(act.slot, "skip"), answering=act.slot)
    assert act.kind == "confirm" and s.state is SessionState.CONFIRMING
    return s, act


# ---- reading the reply (R005) ----------------------------------------------------------


def test_polarity_reads_negation():
    assert polarity("that's not right") is False
    assert polarity("No, that is not correct") is False
    assert polarity("yes, that's right") is True
    assert polarity("correct") is True
    assert polarity("no changes, go ahead") is True
    assert polarity("hmm, what about the cost") is None
    assert polarity("theek hai") is True
    assert polarity("not really") is False
    assert polarity("no, not quite") is False


def test_negated_phrases_are_removed_before_reading_facts():
    assert "madurai" not in strip_negated("No, I am in Salem not Madurai").lower()
    got = {e.key: e.value for e in corrections("No, I am in Salem not Madurai")}
    assert got.get("district") == "salem"
    got = {e.key: e.value for e in corrections("No, it is not agriculture, it is electronics")}
    assert got.get("sector") is Sector.ELECTRONICS
    got = {e.key: e.value for e in corrections("Madurai illai, Salem")}
    assert got.get("district") == "salem"


def test_a_long_reply_is_never_read_as_the_problem():
    """The loose positional guess (0.55) must not replace the problem at confirmation."""
    keys = {e.key for e in corrections("No, I am in Salem not Madurai, please change it")}
    assert "problem" not in keys


def test_not_right_does_not_confirm():
    s, act = _confirming()
    nxt = engine.reply(s, "that's not right")
    assert nxt.kind != "generate"
    assert s.state is not SessionState.GENERATING
    # nothing was corrected, so the founder is asked what to change, not shown the same text
    assert nxt.kind == "ask" and nxt.slot is None and nxt.question
    assert s.state is SessionState.CONFIRMING


def test_yes_with_a_correction_applies_it_and_restates():
    s, act = _confirming()
    nxt = engine.reply(s, "yes but the district is Salem not Erode")
    assert s.slots["district"].value == "salem"
    assert s.slots["district"].source is Source.ANSWER
    assert nxt.kind == "confirm" and "Salem" in (nxt.objective or "")
    assert "Erode" not in (nxt.objective or "")


def test_no_with_a_correction_stores_the_right_value():
    s, _ = _confirming()
    engine.reply(s, "No, I am in Salem not Madurai")
    assert s.slots["district"].value == "salem"


def test_a_plain_yes_confirms():
    s, _ = _confirming()
    assert engine.reply(s, "yes").kind == "generate"
    assert s.state is SessionState.GENERATING


def test_after_what_to_change_the_next_reply_is_read_as_a_correction():
    s, _ = _confirming()
    engine.reply(s, "that's wrong")
    nxt = engine.reply(s, "the money is from my own savings")
    assert s.slots["funding_route"].value.value == "self"
    assert nxt.kind == "confirm"


def test_agent_turn_does_not_confirm_on_not_right():
    s, _ = agent.new_session("Meena")
    s.elicitation, _ = _confirming()
    act = agent._advance(s, "that's not right")
    assert act.kind != "generate"
    act = agent._advance(s, "yes, but we are in Salem")
    assert s.elicitation.slots["district"].value == "salem" and act.kind == "confirm"


def test_an_aside_in_a_long_reply_does_not_replace_an_answer():
    """R025 at confirmation: a passing mention of a school is not a sector correction."""
    s, _ = _confirming()
    assert s.slots["sector"].value is Sector.TEXTILE
    assert s.slots["sector"].source is Source.ANSWER
    engine.reply(s, "Well, overall okay I guess, my wife works in a school so time is tight")
    assert s.slots["sector"].value is Sector.TEXTILE
    assert s.slots["sector"].source is Source.ANSWER
    assert "sector" not in s.locked
    assert s.rivals["sector"].value is Sector.EDUCATION  # kept as a rival, not stored


def test_naming_the_slot_anchors_a_correction_in_a_long_reply():
    s, _ = _confirming()
    engine.reply(s, "Well overall it is fine I guess, though the sector is really food processing")
    assert s.slots["sector"].value is Sector.FOOD and "sector" in s.locked


def test_yes_but_team_size_is_read_not_confirmed():
    """Team size is restated (R154), so it must be correctable there too."""
    s, _ = _confirming()
    nxt = engine.reply(s, "yes but team is 3")
    assert nxt.kind != "generate" and s.state is not SessionState.GENERATING
    assert s.slots["team_size"].value == 3 and "team_size" in s.locked
    s, _ = _confirming()
    engine.reply(s, "yes but we are a team of 3")
    assert s.slots["team_size"].value == 3


def test_a_timeline_or_someone_elses_years_is_not_experience():
    for text in (
        "yes, and I want it running in 2 years",
        "yes but we plan to launch in 2 years",
        "yes but I have been thinking about this for 3 years",
        "yes, though my brother has 10 years of experience in agriculture",
    ):
        s, _ = _confirming()
        engine.reply(s, text)
        assert "founder_years" not in s.slots, text
        assert "founder_years" not in s.locked, text


def test_the_founders_own_experience_is_read():
    s, _ = _confirming()
    engine.reply(s, "yes but I have 6 years of experience")
    assert s.slots["founder_years"].value == 6 and "founder_years" in s.locked


def test_an_aside_after_but_does_not_replace_an_answer():
    """'Yes, but ...' introducing someone else's story corrects nothing."""
    for text in ("yes, but my wife works in a school", "yes but I am a farmer's son"):
        s, _ = _confirming()
        nxt = engine.reply(s, text)
        assert s.slots["sector"].value is Sector.TEXTILE, text
        assert s.slots["sector"].source is Source.ANSWER and "sector" not in s.locked, text
        assert "sector" in s.rivals, text
        # nothing was corrected, and a 'but' is not a plain yes
        assert nxt.kind == "ask" and nxt.question == engine.WHAT_TO_CHANGE, text


def test_yes_but_with_the_fact_alone_is_a_correction():
    s, _ = _confirming()
    engine.reply(s, "yes, but it's a food business")
    assert s.slots["sector"].value is Sector.FOOD and "sector" in s.locked


def test_yes_but_with_nothing_readable_asks_what_to_change():
    s, _ = _confirming()
    nxt = engine.reply(s, "yes, but one thing is off")
    assert nxt.kind == "ask" and nxt.question == engine.WHAT_TO_CHANGE
    assert s.state is SessionState.CONFIRMING


# ---- corrections stick (1.1.2.3) ---------------------------------------------------------


def test_a_corrected_slot_is_locked():
    s, _ = _confirming()
    engine.reply(s, "no, the district is Salem")
    assert "district" in s.locked
    s.put("district", "madurai", 0.95, Source.EXTRACTED)
    s.put("district", "madurai", 0.95, Source.ANSWER)
    assert s.slots["district"].value == "salem"
    assert s.rivals["district"].value == "madurai"  # kept, not silently dropped


def test_a_correction_refunds_one_question():
    """With the budget spent, a correction still leaves room for exactly one question."""
    s = engine.start("u1")
    engine.observe(s, "hello")
    for _ in range(Q_MAX + 2):
        act = engine.step(s)
        if act.kind != "ask":
            break
        engine.observe(s, "hmm", answering=None)
    assert act.kind == "confirm" and s.turn_no >= Q_MAX
    nxt = engine.reply(s, "no, we are in Salem")
    assert s.slots["district"].value == "salem"
    assert nxt.kind == "ask" and nxt.slot in REQUIRED_BY_MODE[EntryMode.IDEA]
    engine.observe(s, "hmm", answering=nxt.slot)
    assert engine.step(s).kind == "confirm"  # the refunded question is used up


# ---- source rank before confidence (R025) -----------------------------------------------


def test_a_later_aside_does_not_replace_a_direct_answer():
    s = engine.start("u1")
    engine.observe(s, "electronics", answering="sector")
    assert s.slots["sector"].value is Sector.ELECTRONICS
    engine.observe(s, "Of course, we will also offer it to farm schools")
    assert s.slots["sector"].value is Sector.ELECTRONICS
    assert s.slots["sector"].source is Source.ANSWER
    assert s.rivals["sector"].value is Sector.AGRI


def test_a_model_note_does_not_replace_a_profile_fact():
    s = engine.start("u1", profile={"district": "Erode"})
    s.record(user_text="my brother is in Madurai")
    out = asyncio.run(tools.run_tool("note_fact", {"key": "district", "value": "madurai"}, s, {}))
    assert out["kept"] == "district"  # reported truthfully (R053), not "recorded"
    assert s.slots["district"].value == "erode"
    assert s.slots["district"].source is Source.PROFILE


def test_an_extraction_still_replaces_a_weaker_extraction():
    s = engine.start("u1")
    s.put("stage", "idea", 0.55, Source.EXTRACTED)
    s.put("stage", "prototype", 0.85, Source.EXTRACTED)
    assert s.slots["stage"].value == "prototype"


# ---- the restatement (1.1.2.1, 1.1.2.2, R051, R154) -------------------------------------


def test_restatement_labels_where_each_fact_came_from():
    s = engine.start("u1", profile={"stage": "prototype"})
    s.put("district", "erode", 0.90, Source.ANSWER)
    s.put("funding_route", FundingRoute.DEBT, 0.85, Source.EXTRACTED)
    text = engine.restate(s)
    told = text.split("You told me:")[1].split(".")[0]
    profile = text.split("From your profile:")[1].split(".")[0]
    assumed = text.split("I assumed:")[1].split(".")[0]
    assert "Erode" in told
    assert "prototype" in profile
    assert "loan" in assumed


def test_restatement_names_roadmap_facts_that_were_not_answered():
    """Team size and experience scale every milestone (R154)."""
    s = engine.start("u1", profile={"founder_years": "5"})
    s.put("team_size", 3, 0.8, Source.EXTRACTED)  # a model note
    text = engine.restate(s)
    assert "a team of 3" in text.split("I assumed:")[1]
    assert "5 years" in text.split("From your profile:")[1]


def test_restatement_says_what_a_skipped_slot_will_be_assumed_as():
    s = engine.start("u1")
    engine.observe(s, "a textile finishing unit for weavers")
    s.skip("stage")
    s.skip("capital_band")
    text = engine.restate(s)
    assert "You skipped your stage and budget" in text
    skipped = text.split("You skipped")[1].split(".")[0]
    assert "I will assume" in skipped and "idea stage" in skipped
    assert "don't know" in text  # the gaps that were never asked are still named


def test_restatement_shortens_the_problem():
    s = engine.start("u1")
    long = (
        "I want to start a banana chips and banana flour unit in Tiruchirappalli using B-grade"
        " fruit bought directly from Thottiyam farmers at a fair price every season"
    )
    s.put("problem", long, 0.85, Source.EXTRACTED)
    text = engine.restate(s)
    assert long not in text
    assert "You want to start a banana chips and banana flour unit in Tiruchirappalli" in text
    assert "problem: I want to" not in text


def test_restatement_does_not_repeat_the_beneficiary_as_the_problem():
    s = engine.start("u1")
    s.put("problem", "small weavers who sell locally", 0.85, Source.EXTRACTED)
    s.put("beneficiary", "small weavers who sell locally", 0.90, Source.ANSWER)
    text = engine.restate(s)
    assert text.lower().count("small weavers who sell locally") == 1
