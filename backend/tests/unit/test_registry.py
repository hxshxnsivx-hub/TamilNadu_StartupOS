"""Unit tests for the domain registry, hybrids and risk analysis."""

from __future__ import annotations

from collections import Counter

from app.planner import registry
from app.planner.plan import build_plan
from app.planner.risks import PHASES, RISKS, adjusted_levels, by_phase

REG = registry.load()
DOMAINS = REG["domains"]


def test_registry_is_consistent():
    assert len(DOMAINS) == 50
    counts = Counter(d["category"] for d in DOMAINS.values())
    assert set(counts) == set(REG["categories"])  # every category has domains
    for d in DOMAINS.values():
        assert d["category"] in REG["categories"]
        assert set(d["needs"]) <= set(REG["capabilities"]), d["id"]
        assert set(d["offers"]) <= set(REG["capabilities"]), d["id"]
        assert set(d["regulatory"]) <= set(REG["regulatory"]), d["id"]
        assert set(d["serves"]) <= set(REG["categories"]), d["id"]
        assert set(d["risk"]) == set(REG["risk_types"]), d["id"]
        assert all(k in registry.DISTRICTS for k in d.get("districts", {})), d["id"]
        if d.get("theme"):
            assert d["theme"] in REG["themes"], d["id"]


def test_regulatory_items_carry_confidence_and_source():
    for item in REG["regulatory"].values():
        assert item["confidence"] in ("official", "secondary", "to_verify")
        assert item["source"].startswith("https://")


def test_schemes_follow_rules_and_carry_live_status():
    banana = {s["id"]: s for s in registry.schemes_for(DOMAINS["banana_value_added"])}
    assert {"tanseed", "pmfme", "needs"} <= set(banana)
    assert banana["tanseed"]["why"] == "matches the TANSEED theme 'Post Harvest Processing'"
    assert banana["pmfme"]["status"] == "lapsed_pending"  # from the catalogue, not hard-coded
    diagnostics = {s["id"] for s in registry.schemes_for(DOMAINS["phc_diagnostics"])}
    assert {"birac_big", "gem_runway"} <= diagnostics
    assert "pmfme" not in diagnostics


def test_detects_domain_from_founder_words():
    assert (
        registry.detect_domain("banana chips and banana flour from our farm")
        == "banana_value_added"
    )
    assert registry.detect_domain("hello") is None


def test_incubators_fall_back_to_other_districts_when_none_nearby():
    rows = registry.incubators_for(DOMAINS["banana_value_added"], "tiruchirappalli")
    assert rows and all(r.get("elsewhere") for r in rows)
    madurai = registry.incubators_for(DOMAINS["jasmine_postharvest"], "madurai")
    assert any("MABIF" in r["name"] for r in madurai)


def test_hybrids_pair_only_products_the_anchor_would_use():
    for h in registry.hybrids(limit=10**6):
        a, b = DOMAINS[h["anchor"]["id"]], DOMAINS[h["partner"]["id"]]
        assert a["category"] != b["category"]
        assert a["category"] in b["serves"]
        assert b["category"] in REG["categories"][a["category"]]["neighbours"]
        assert h["partner_supplies"]  # brings at least one capability the anchor needs
        assert a["id"] not in b.get("not_partner_for", [])
    jasmine = [h["partner"]["id"] for h in registry.hybrids("jasmine_postharvest", "madurai")]
    assert jasmine[0] == "cold_room_monitoring"
    poultry = [h["partner"]["id"] for h in registry.hybrids("poultry_health", limit=50)]
    assert "crop_disease_ai" not in poultry


def test_universal_schemes_do_not_count_as_gains():
    for h in registry.hybrids(limit=10**6):
        assert not {s["id"] for s in h["new_scheme_routes"]} & registry.UNIVERSAL_ROUTES


def test_founder_situation_adjusts_risk_with_reasons():
    banana = DOMAINS["banana_value_added"]
    lv, why = adjusted_levels(
        banana, {"capital_band": "2L_10L", "founder_years": 1, "team_size": 1}
    )
    assert lv["capital"] == banana["risk"]["capital"] + 1
    assert "₹10–50 lakh" in why["capital"]
    assert lv["execution"] == 3 and "solo" in why["execution"]
    exporter, why2 = adjusted_levels(banana, {"geo_scope": "export"})
    assert (
        exporter["regulatory"] == banana["risk"]["regulatory"] + 1
        and "export" in why2["regulatory"]
    )
    gov, why3 = adjusted_levels(DOMAINS["phc_diagnostics"], {})
    assert gov["receivables"] == 3 and "government" in why3["receivables"]


def test_risks_by_phase_are_ranked_and_actionable():
    risks = by_phase(DOMAINS["phc_diagnostics"], {"founder_years": 1})
    assert list(risks) == PHASES
    mvp = risks["MVP"]
    assert mvp[0]["score"] >= mvp[-1]["score"]
    assert {"regulatory", "technical"} <= {r["risk"] for r in mvp}
    for rows in risks.values():
        for r in rows:
            assert r["reduce"] and r["early_warning"] and r["risk"] in RISKS


def test_card_only_domain_gets_licences_milestone_and_risks():
    p = build_plan(
        "jasmine flower post-harvest for Madurai Malli growers",
        {"district": "Madurai", "stage": "idea", "funding_route": "debt", "capital_band": "2L_10L"},
    )
    assert p["domain"] is None and p["domain_card"]["id"] == "jasmine_postharvest"
    assert p["domain_card"]["district_fit"]["madurai"] == 3
    licences = next(m for m in p["roadmap"]["milestones"] if m["id"] == "c_compliance")
    assert any(d.startswith("GI authorised user") for d in licences["deliverables"])
    assert all(m["risks"] for m in p["roadmap"]["milestones"])
    assert p["risks_by_phase"]["MVP"][0]["label"] == "Running out of money"


def test_tea_founder_still_gets_the_deep_pack_and_the_card():
    p = build_plan("a tea brand with mint hibiscus", {"stage": "idea"}, variants=["mint hibiscus"])
    assert p["domain"]["id"] == "tea_infusions" and p["domain_card"]["id"] == "tea_infusions"
