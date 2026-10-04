"""Unit tests for domain-aware planning: packs, variants, costs and the roadmap."""

from __future__ import annotations

import itertools

import pytest
from app.planner.costing import cost_sheet, fssai_tier
from app.planner.packs import detect_pack, load_packs
from app.planner.plan import build_plan
from app.planner.variants import free_extensions, resolve, shared_ingredients
from app.swarms.roadmap.milestones import topological_order

TEA = load_packs()["tea_infusions"]
LINE = ["mint", "mint lemon", "mint strawberry", "lemon raspberry", "mint hibiscus"]


def _plan(slots=None, **kw):
    base = {"district": "Coimbatore", "stage": "idea", "funding_route": "debt"}
    base.update(slots or {})
    kw.setdefault("variants", LINE)
    kw.setdefault("channels", ["online", "retail"])
    kw.setdefault("monthly_packs", 1500)
    return build_plan("a tea brand", base, **kw)


def _titles(p):
    return [m["title"] for m in p["roadmap"]["milestones"]]


def test_domain_detected_from_the_founders_words():
    assert detect_pack("I want to sell mint hibiscus tea in Madurai") == "tea_infusions"
    assert detect_pack("an app to book auto rickshaws") is None


def test_variants_resolve_in_any_word_order_and_unknowns_are_reported():
    found, unknown = resolve(TEA, ["lemon mint", "Mint Hibiscus tea", "rose cardamom"])
    assert [v.key for v in found] == ["mint_lemon", "mint_hibiscus"]
    assert unknown == ["rose cardamom"]


def test_herbal_blends_are_infusions_and_shared_buying_is_found():
    line, _ = resolve(TEA, LINE)
    kinds = {v.key: v.kind for v in line}
    assert kinds["mint_hibiscus"] == "herbal infusion" and kinds["mint"] == "tea"
    top = shared_ingredients(TEA, line)[0]
    assert top["key"] == "mint" and top["count"] == 4
    assert {e["key"] for e in free_extensions(TEA, line)} == {"lemongrass_mint", "hibiscus_lemon"}


def test_cost_levers_are_computed_not_asserted():
    line, _ = resolve(TEA, LINE)
    c = cost_sheet(TEA, line, monthly_packs=1500)
    by = {r["key"]: r for r in c["rows"]}
    for r in c["rows"]:
        assert (
            r["ingredients"]
            < r["cogs"]
            < r["ex_factory"]
            < r["distributor"]
            < r["retail_before_gst"]
        )
    breakeven = next(lv for lv in c["levers"] if "breakeven_packs_per_month" in lv)
    assert breakeven["breakeven_packs_per_month"] == 60000 / (12 - 4)
    lighter = [lv for lv in c["levers"] if "fewer fruit pieces" in lv["lever"]]
    assert len(lighter) == 2 and all(lv["saves_per_pack"] > 0 for lv in lighter)
    assert "mint" in c["example_prices_used"]
    # Your own quote replaces the example price and is no longer flagged.
    mine = cost_sheet(TEA, line, prices={"mint": 200}, monthly_packs=1500)
    assert "mint" not in mine["example_prices_used"]
    assert {r["key"]: r for r in mine["rows"]}["mint"]["cogs"] < by["mint"]["cogs"]


def test_fssai_tier_by_turnover():
    assert fssai_tier(10) == "basic registration"
    assert fssai_tier(150) == "State licence"
    assert fssai_tier(5000) == "Central licence"
    assert fssai_tier(None) == "registration or licence"


def test_the_same_idea_gives_different_roadmaps_to_different_founders():
    first_timer = _plan({"founder_years": 1, "team_size": 2}, production_mode="co_packer")
    veteran = _plan(
        {"founder_years": 12, "team_size": 4, "stage": "mvp", "funding_route": "equity",
         "geo_scope": "export"},
        production_mode="own_unit",
        variants=["mint", "mint lemon"],
    )  # fmt: skip
    a, b = _titles(first_timer), _titles(veteran)
    assert a != b
    assert "Contract a co-packer and run a pilot batch" in a
    assert "Set up a small blending and packing unit" in b
    assert "Raise a scheme-linked bank loan" in a and "Raise from angels" in b
    assert "Export readiness" in b and "Export readiness" not in a
    assert "Bench-blend the recipes" not in b  # an MVP-stage founder has done this


def test_conditional_deliverables_follow_the_answers():
    def deliverables(p, mid):
        return next(m for m in p["roadmap"]["milestones"] if m["id"] == mid)["deliverables"]

    with_herbal = deliverables(_plan(), "t_compliance")
    tea_only = deliverables(_plan(variants=["mint", "mint lemon"]), "t_compliance")
    assert any("infusions, not tea" in d for d in with_herbal)
    assert not any("infusions, not tea" in d for d in tea_only)
    regs = deliverables(_plan({"funding_route": "equity"}), "c_registrations")
    assert any("DPIIT" in d for d in regs)
    assert not any("DPIIT" in d for d in deliverables(_plan(), "c_registrations"))


@pytest.mark.parametrize(
    "stage,route,mode,channels",
    list(
        itertools.product(
            ["idea", "prototype", "mvp", "revenue"],
            ["debt", "equity", "grant"],
            ["co_packer", "own_unit"],
            [["online"], ["retail", "horeca"]],
        )
    ),
)
def test_roadmap_stays_within_bounds_and_in_dependency_order(stage, route, mode, channels):
    p = _plan({"stage": stage, "funding_route": route}, production_mode=mode, channels=channels)
    ms = p["roadmap"]["milestones"]
    assert 5 <= len(ms) <= 15
    ids = {m["id"] for m in ms}
    assert all(d in ids for m in ms for d in m["depends_on"])
    pos = {m["id"]: i for i, m in enumerate(topological_order_like(ms))}
    assert all(pos[d] < pos[m["id"]] for m in ms for d in m["depends_on"])


def topological_order_like(ms):
    from app.swarms.roadmap.models import Milestone, Phase, Timeline

    objs = [
        Milestone(m["id"], Phase(m["phase"]), m["title"], [], Timeline(1, 1, 2), m["depends_on"])
        for m in ms
    ]
    order = topological_order(objs)
    by = {m["id"]: m for m in ms}
    return [by[i] for i in order]


def test_office_waits_do_not_shrink_with_team_size_but_work_does():
    solo = _plan({"team_size": 1, "founder_years": 1})
    team = _plan({"team_size": 8, "founder_years": 1})

    def realistic(p, mid):
        return next(m for m in p["roadmap"]["milestones"] if m["id"] == mid)["months"]["realistic"]

    assert realistic(solo, "t_compliance") == realistic(team, "t_compliance")  # FSSAI and lab
    assert realistic(team, "c_customers") <= realistic(solo, "c_customers")


def test_fewer_confident_answers_widen_the_band():
    sure = _plan(confidence=0.9)
    unsure = _plan(confidence=0.3)
    for a, b in zip(sure["roadmap"]["milestones"], unsure["roadmap"]["milestones"], strict=True):
        assert b["months"]["pessimistic"] >= a["months"]["pessimistic"]


def test_missing_pack_answers_become_the_next_questions():
    p = build_plan("a tea brand", {"stage": "idea"})
    assert {q["slot"] for q in p["next_questions"]} >= {"variants", "production_mode", "channels"}
    # Only what the founder has not answered yet is asked.
    assert {q["slot"] for q in _plan()["next_questions"]} == {"format", "production_mode"}


def test_unknown_products_get_the_common_spine_and_say_so():
    p = build_plan("an app to book auto rickshaws", {"stage": "idea", "funding_route": "grant"})
    assert p["domain"] is None and "No domain pack" in p["domain_note"]
    assert all(m["from"] == "common" for m in p["roadmap"]["milestones"])
    assert "Apply for seed grants" in _titles(p)
