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


def test_model_seats_share_a_cached_prefix_and_fall_back_on_failure(monkeypatch):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "k")
    sent = []

    def handle(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        sent.append(body)
        if "Technical" in body["messages"][0]["content"]:
            return httpx.Response(529, json={"error": "overloaded"})
        reply = {"stance": "support", "scores": {"need": 4}, "confidence": 0.9,
                 "claims": [{"text": "23 trials.", "evidence": ["trials:total"]}]}  # fmt: skip
        return httpx.Response(200, json={"content": [{"type": "text", "text": json.dumps(reply)}],
                                         "usage": {"input_tokens": 10}})  # fmt: skip

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:
            return await convene(IDEA, {}, scan=SCAN, novelty=NOVELTY, client=c)

    r = asyncio.run(go())
    assert len(sent) == 7 and r["basis"] == "model" and r["fallback_seats"] == ["technical"]
    systems = {json.dumps(b["system"]) for b in sent}
    assert len(systems) == 1  # identical prefix for every seat
    assert sent[0]["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert r["usage"]["input_tokens"] == 60
    basis = {o["seat"]: o["basis"] for o in r["opinions"]}
    assert basis["technical"] == "rules" and basis["customer"] == "model"


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
    assert "subscriptions" in pack.items["novelty:lever:0"]["text"]
