"""The advocate council: evidence IDs, cited opinions, the vote, synthesis, model seats."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from app.agents.council import convene
from app.agents.council import evidence as ev
from app.agents.council.seats import BY_ID, Opinion, validate
from app.agents.council.vote import idea_type, vote, weights_for
from app.core.config import get_settings

IDEA = "communication for paralysed patients through brain waves to change medication"
SCAN = {
    "associated_domains": {"fields": [{"name": "Medicine", "share_pct": 40}]},
    "vanigam_categories": ["health_bio"],
    "papers": {"total": 215, "most_relevant": [{"title": "AAC BCI review", "year": 2022}]},
    "trials": {"total": 23, "items": [{"id": "NCT01234567", "title": "BCI speech"}]},
    "projects": {"total": 702, "items": [{"name": "lab/eeg-bci", "stars": 169}]},
    "patents": {"total": 0, "items": []},
    "local": {
        "status": "ok",
        "scope": "the 654 startups on the Tamil Nadu Startup Map in Chennai and Madurai",
        "startups": [],
        "registry_domains": [],
    },
    "coverage": [{"source": "patents", "status": "no_key", "note": "add key"}],
}
NOVELTY = {
    "statement": {"type": "combination", "text": "Together, I found only 19."},
    "pairs": [
        {"a": "brain waves", "b": "nurse call", "a_papers": 760191, "b_papers": 980,
         "papers": 19, "gap": True},
    ],  # fmt: skip
    "context": {"searched": False},
    "levers": [{"kind": "combine", "text": "Join brain waves with nurse call.", "because": "19"}],
}


@pytest.fixture(autouse=True)
def _no_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")


def _pack():
    return ev.build(IDEA, SCAN, NOVELTY, "chennai")


def test_every_fact_gets_a_stable_id():
    ids = _pack().ids
    for i in ("trial:NCT01234567", "repo:lab/eeg-bci", "paper:0", "novelty:pair:0",
              "novelty:statement", "coverage:patents", "local:none", "field:medicine"):  # fmt: skip
        assert i in ids


def test_uncited_claims_are_dropped_and_blockers_need_evidence():
    raw = {
        "stance": "oppose",
        "scores": {"need": 9, "feasibility": 2, "made_up": 3},
        "confidence": 0.8,
        "claims": [
            {"text": "Trials exist.", "evidence": ["trial:NCT01234567"]},
            {"text": "Invented fact.", "evidence": ["paper:999"]},
        ],
        "blocker": {"text": "No market.", "evidence": ["nowhere:1"]},
    }
    op = validate(raw, BY_ID["customer"], _pack().ids, "model")
    assert [c.text for c in op.claims] == ["Trials exist."] and op.dropped_claims == 1
    assert op.blocker is None  # uncited blocker cannot veto
    assert op.scores == {"need": 5, "feasibility": 2}  # clamped, unknown criteria removed


def test_devil_cannot_support():
    raw = {"stance": "support", "scores": {"need": 4}, "confidence": 0.5, "claims": []}
    op = validate(raw, BY_ID["devil"], set(), "model")
    assert op.stance == "conditional" and op.confidence == 0.25  # no backed claims: halved


def test_weights_follow_the_idea_type_and_the_founder():
    assert idea_type(["health_bio"], {}) == "health_device"
    assert idea_type([], {"product_form": "software"}) == "software"
    # R035: the founder's sector and form come before categories read off papers
    assert idea_type(["health_bio", "agriculture"], {"sector": "food"}) == "food"
    assert idea_type(["saas"], {"sector": "textile", "product_form": "physical"}) == "hardware"
    assert idea_type(["saas"], {"product_form": "physical"}) == "hardware"
    assert idea_type(["agriculture"], {"sector": "other"}) == "agri"  # 'other' says nothing
    assert idea_type(["saas"], {"sector": "education"}) == "software"  # not a goods sector
    w, why = weights_for("hardware", {"capital_band": "under_2L", "founder_skills": ["sales"]})
    assert round(sum(w.values())) == 100 and len(why) == 2
    w2, _ = weights_for("hardware", {"founder_skills": ["electronics engineer"]})
    assert w["technical"] > w2["technical"] - 1  # no tech skill raises technical


def _op(seat, stance, scores, blocker=False, ask=None):
    return Opinion(
        seat=seat, stance=stance, scores=scores, confidence=0.8,
        claims=[{"text": "a claim", "evidence": ["a"]}],
        blocker={"text": "fatal", "evidence": ["a"]} if blocker else None, ask_founder=ask,
    )  # fmt: skip


def test_a_cited_blocker_vetoes_a_high_average():
    ops = [_op(s, "support", {"need": 5, "feasibility": 5}) for s in BY_ID if s != "regulatory"]
    assert vote(ops, "hardware", {})["band"] == "strong"
    ops.append(_op("regulatory", "oppose", {"compliance": 4}, blocker=True))
    v = vote(ops, "hardware", {})
    assert v["band"] == "weak" and v["blockers"][0]["seat"] == "regulatory"


def test_biggest_disagreement_becomes_the_question():
    ops = [
        _op("customer", "support", {"need": 5}, ask="Who pays?"),
        _op("devil", "oppose", {"need": 1}, ask="Will anyone pay at all?"),
        _op("technical", "support", {"feasibility": 4}),
    ]
    v = vote(ops, "hardware", {})
    assert v["ask_about"] == "need" and v["question"] == "Will anyone pay at all?"
    assert v["missing_seats"] == ["cost", "funding", "prior_art", "regulatory"]


def test_offline_council_runs_every_seat_from_rules():
    r = asyncio.run(convene(IDEA, {"sector": "health"}, scan=SCAN, novelty=NOVELTY))
    assert r["basis"] == "rules" and len(r["opinions"]) == 7
    assert all(c["evidence"] for o in r["opinions"] for c in o["claims"])
    assert r["vote"]["idea_type"] == "health_device" and r["synthesis"]["voice_brief"]
    assert r["vote"]["variants"][0]["as_described"]  # the founder's idea is always an option


def test_partial_rerun_keeps_the_other_seats():
    first = asyncio.run(convene(IDEA, {}, scan=SCAN, novelty=NOVELTY))
    again = asyncio.run(
        convene(IDEA, {}, scan=SCAN, novelty=NOVELTY, seats=("cost",), previous=first["opinions"])
    )
    assert len(again["opinions"]) == 7 and again["fallback_seats"] == ["cost"]


def _reply(opinions: list[dict]) -> httpx.Response:
    text = json.dumps({"opinions": opinions})
    return httpx.Response(200, json={"content": [{"type": "text", "text": text}],
                                     "usage": {"input_tokens": 10}})  # fmt: skip


def test_one_model_call_answers_for_every_seat(monkeypatch):
    """R175: one request per panel run, not seven; a seat the reply leaves out falls
    back to its rules, and the shared evidence is still marked for caching."""
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "k")
    sent = []

    def handle(req: httpx.Request) -> httpx.Response:
        sent.append(json.loads(req.content))
        op = {"stance": "support", "scores": {"need": 4}, "confidence": 0.9,
              "claims": [{"text": "23 trials.", "evidence": ["trials:total"],
                          "criterion": "compliance"}]}  # fmt: skip
        return _reply([{**op, "seat": s} for s in BY_ID if s != "technical"])

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:
            return await convene(IDEA, {}, scan=SCAN, novelty=NOVELTY, client=c)

    r = asyncio.run(go())
    assert len(sent) == 1 and r["basis"] == "model" and r["fallback_seats"] == ["technical"]
    assert sent[0]["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert all(seat in sent[0]["messages"][0]["content"] for seat in BY_ID)
    assert r["usage"]["input_tokens"] == 10
    basis = {o["seat"]: o["basis"] for o in r["opinions"]}
    assert basis["technical"] == "rules" and basis["customer"] == "model"


def test_a_failed_panel_call_falls_back_to_rules_and_trips_the_breaker(monkeypatch):
    """R175: a quota error is recorded on the provider's breaker, so a spent quota
    stops costing a wait on every panel run."""
    from app.agents import providers

    monkeypatch.setattr(get_settings(), "anthropic_api_key", "k")
    breaker = providers.PROVIDERS["anthropic"].breaker
    monkeypatch.setattr(breaker, "failures", type(breaker.failures)())
    monkeypatch.setattr(breaker, "open_until", 0.0)

    async def go():
        transport = httpx.MockTransport(lambda req: httpx.Response(429, json={}))
        async with httpx.AsyncClient(transport=transport) as c:
            return await convene(IDEA, {}, scan=SCAN, novelty=NOVELTY, client=c)

    r = asyncio.run(go())
    assert r["basis"] == "rules" and len(r["opinions"]) == 7
    assert len(breaker.failures) == 1
    breaker.succeed()


LEVERS = [
    {"kind": "combine", "facts": {"a": "brain waves", "b": "nurse call", "papers": 19}},
    {"kind": "combine", "facts": {"a": "brain waves", "b": "speech", "papers": 0}},
    {
        "kind": "localise",
        "facts": {"india_papers": 52, "world_papers": 1118, "tn_scope": "the 654 startups"},
    },  # fmt: skip
    {"kind": "re-target", "facts": {"who": "elderly", "papers": 3}},
    {"kind": "regulatory route", "facts": {"trials": 23}},
    {"kind": "business model", "facts": {}},
]


def test_every_lever_reaches_the_panel_with_a_stable_id():
    """R110, R041: no cap of four, and each lever's id is a hash of its kind and
    facts, the same whatever its place or wording."""
    from app.research import levers

    pack = ev.build(IDEA, SCAN, {**NOVELTY, "levers": LEVERS}, None)
    assert len(pack.levers) == len(LEVERS)
    ids = [lv["id"] for lv in pack.levers]
    assert len(set(ids)) == len(ids) and all(f"novelty:lever:{i}" in pack.ids for i in ids)
    reworded = {**LEVERS[5], "text": "something else"}
    assert levers.lever_id(reworded) == levers.lever_id(LEVERS[5]) == ids[5]
    again = ev.build(IDEA, SCAN, {**NOVELTY, "levers": LEVERS[::-1]}, None)
    assert [lv["id"] for lv in again.levers] == ids[::-1]


def test_the_seats_score_the_levers_and_the_vote_orders_them():
    """1.3.1: the regulatory route for a medical product and the pair no paper covers
    rank above the levers in front of them; the prior-art variant is its best lever,
    not lever 0."""
    r = asyncio.run(
        convene(IDEA, {"sector": "health"}, scan=SCAN, novelty={**NOVELTY, "levers": LEVERS})
    )
    order, scores = r["vote"]["lever_order"], r["vote"]["lever_scores"]
    kinds = {lv["id"]: (lv["kind"], (lv["facts"] or {}).get("papers")) for lv in
             ev.build(IDEA, SCAN, {**NOVELTY, "levers": LEVERS}, None).levers}  # fmt: skip
    assert len(order) == len(LEVERS) and set(order) == set(kinds)
    assert kinds[order[0]] == ("regulatory route", None)
    assert order.index(_id(kinds, "combine", 0)) < order.index(_id(kinds, "combine", 19))
    assert {"prior_art", "customer"} <= set(scores[_id(kinds, "combine", 0)]["seats"])
    prior = next(o for o in r["opinions"] if o["seat"] == "prior_art")
    assert "brain waves with speech" in prior["variant"]


def _id(kinds: dict, kind: str, papers) -> str:
    return next(i for i, k in kinds.items() if k == (kind, papers))


def test_a_lever_no_seat_scored_comes_last_in_its_place():
    ops = [
        Opinion(seat="customer", stance="support", scores={"need": 4}, confidence=0.5,
                levers={"b": 4, "c": 5}),
        Opinion(seat="prior_art", stance="support", scores={"differentiation": 4},
                confidence=0.5, levers={"b": 2}),
    ]  # fmt: skip
    v = vote(ops, "hardware", {}, ["a", "b", "c", "d"])
    assert v["lever_order"] == ["c", "b", "a", "d"]
    assert set(v["lever_scores"]) == {"b", "c"}


def test_lever_scores_must_name_levers_in_the_pack():
    pack = ev.build(IDEA, SCAN, {**NOVELTY, "levers": LEVERS[:2]}, None)
    lid = pack.levers[0]["id"]
    raw = {"stance": "support", "scores": {"need": 4}, "confidence": 0.5,
           "levers": {f"novelty:lever:{lid}": 9, "made-up": 3}}  # fmt: skip
    assert validate(raw, BY_ID["customer"], pack.ids, "model").levers == {lid: 5}


def test_a_seat_question_is_not_asked_once_its_slot_is_known():
    """R056: offline, the customer seat's 'who pays' repeated the beneficiary question.
    With the beneficiary known, the panel asks about its weakest point instead."""
    ops = [
        Opinion(seat="customer", stance="conditional", scores={"need": 2}, confidence=0.5,
                ask_founder="Who exactly would pay?", ask_covers="beneficiary"),
        Opinion(seat="devil", stance="conditional", scores={"need": 2}, confidence=0.5,
                ask_founder="Has anyone told you they would pay?"),
        Opinion(seat="technical", stance="support", scores={"feasibility": 4}, confidence=0.5,
                ask_founder="What have you built?", ask_covers="stage"),
    ]  # fmt: skip
    v = vote(ops, "hardware", {})
    assert v["ask_about"] is None  # nobody disagrees: the weakest criterion's low seat asks
    assert v["question_from"] == "customer" and v["question_covers"] == "beneficiary"
    v = vote(ops, "hardware", {"beneficiary": "coconut farmers"})
    assert v["question"] == "Has anyone told you they would pay?"  # still about the need
    rules = asyncio.run(convene(IDEA, {"beneficiary": "paralysed patients"}, scan=SCAN,
                                novelty=NOVELTY))  # fmt: skip
    assert rules["vote"]["question_from"] != "customer"


def test_add_dynamic_skips_a_question_whose_slot_is_filled():
    from app.elicitation import engine
    from app.elicitation.session import ElicitationSession, Source

    el = ElicitationSession(user_id="u")
    assert engine.add_dynamic(el, "Who pays?", "review panel", covers="beneficiary")
    assert engine._pending_dynamic(el) is not None
    el.put("beneficiary", "farmers", 0.9, Source.ANSWER)
    assert engine._pending_dynamic(el) is None  # filled before its turn: not asked
    assert engine.add_dynamic(el, "Who uses it?", "review panel", covers="beneficiary") is None


def test_the_synthesis_quotes_only_a_claim_about_that_criterion():
    """R106: the weakest point was given the domain's neutral 'names its usual buyers'
    as its reason; a claim about another criterion is never the reason either."""
    r = asyncio.run(convene("solar dryer for copra farmers", {}, scan=SCAN, novelty=None))
    assert not any("names its usual buyers" in line for line in r["synthesis"]["voice_brief"])
    ops = [
        Opinion(seat="customer", stance="oppose", scores={"need": 1}, confidence=0.8,
                claims=[{"text": "Patents exist.", "evidence": ["a"], "criterion": "compliance"}]),
        Opinion(seat="technical", stance="support", scores={"feasibility": 5}, confidence=0.8,
                claims=[{"text": "Open code exists.", "evidence": ["a"],
                         "criterion": "feasibility"}]),
    ]  # fmt: skip
    from app.agents.council.synthesis import synthesise

    pack = ev.EvidencePack()
    pack.add("a", "field", "Patents exist. Open code exists.")
    lines = synthesise(vote(ops, "hardware", {}), ops, pack)["voice_brief"]
    assert any("open code exists" in line for line in lines)
    assert not any("patents exist" in line.lower() for line in lines)


def test_a_claim_criterion_outside_criteria_is_cleared():
    raw = {
        "stance": "support",
        "scores": {"need": 4},
        "confidence": 0.5,
        "claims": [{"text": "23 trials.", "evidence": ["trials:total"], "criterion": "vibes"}],
    }
    op = validate(raw, BY_ID["customer"], _pack().ids, "model")
    assert op.claims[0].criterion is None


def test_no_technical_bump_for_unknown_or_technical_skills():
    """R156: unknown skills are not 'no technical skill', and a Python developer has one."""
    for slots in ({}, {"founder_skills": []}, {"founder_skills": ["python developer"]}):
        _, why = weights_for("software", slots)
        assert not any("technical" in w for w in why), slots
    _, why = weights_for("software", {"founder_skills": ["sales", "accounts"]})
    assert why == ["none of the founder's stated skills is technical: technical +5"]


def test_the_pack_uses_the_scans_one_domain():
    """R044: the panel's domain, licences and cost pack come from the domain the scan
    matched; a related domain the scan also listed is not the idea's own."""
    scan = {
        **SCAN,
        "matched_domain": None,
        "local": {**SCAN["local"], "registry_domains": [{"id": "banana_value_added"}]},
    }
    pack = ev.build("banana chips for export", scan, None, None)
    assert pack.domain_id is None and not any(i.startswith("pack:") for i in pack.ids)
    pack = ev.build("a small unit", {**SCAN, "matched_domain": "banana_value_added"}, None, None)
    assert pack.domain_id == "banana_value_added" and "pack:banana_value_added" in pack.ids


def test_a_loan_that_names_a_hospital_is_no_health_product():
    """R139: the same rule as the novelty lever; trials found are not enough."""
    emi = "hospital bill instalment loans for medical treatment"
    assert not ev.build(emi, SCAN, None, None, {"product_form": "software"}).health
    assert _pack().health  # brain waves and medication: a clinical product


def test_a_farm_app_gets_no_medical_advice_from_the_panel():
    """1.3.3: a crop-disease app by a founder in agriculture is no medical product, so no
    seat speaks of medical devices; a real one hears a variant fit for any medical
    product, not the communication aid that suited one brain-wave idea."""
    from app.agents.council import rules

    crop = "an app that diagnoses crop disease from leaf photos"
    pack = ev.build(crop, SCAN, None, None, {"sector": "agri", "product_form": "software"})
    assert not pack.health
    for seat in (rules.regulatory, rules.devil):
        assert "medical" not in json.dumps(seat(pack, {"sector": "agri"})).lower()
    reg = rules.regulatory(_pack(), {})
    assert "communication aid" not in reg["variant"] and "medical claims" in reg["variant"]


def test_the_panel_hears_levers_worded_for_the_founder():
    nov = {**NOVELTY, "levers": [{"kind": "business model", "facts": {}}]}
    pack = ev.build(IDEA, SCAN, nov, None, {"sector": "food"})
    lid = pack.levers[0]["id"]
    assert "subscriptions" in pack.items[f"novelty:lever:{lid}"]["text"]
