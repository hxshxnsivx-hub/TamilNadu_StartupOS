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
    breakeven = next(lv for lv in c["levers"] if "breakeven_units_per_month" in lv)
    assert breakeven["breakeven_units_per_month"] == 60000 / (12 - 4)
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
    assert p["domain"] is None and "No domain matches" in p["domain_note"]
    assert all(m["from"] == "common" for m in p["roadmap"]["milestones"])
    assert "Apply for seed grants" in _titles(p)


# --- Deep packs beyond tea -----------------------------------------------------

BANANA = load_packs()["banana_value_added"]
PUMPS = load_packs()["pump_controllers"]


def test_banana_yield_drives_cost_and_kinds_follow_frying():
    line, unknown = resolve(BANANA, ["chips", "flour", "health mix"])
    assert not unknown
    assert {v.key: v.kind for v in line} == {
        "chips": "fried snack",
        "flour": "dried product",
        "health_mix": "dried product",
    }
    flour = next(v for v in line if v.key == "flour")
    base = cost_sheet(BANANA, [flour], monthly_packs=1000)["rows"][0]["ingredients"]
    better = cost_sheet(
        BANANA, [flour], monthly_packs=1000, overrides={}, prices={"green_banana": 22}
    )["rows"][0]["ingredients"]
    assert base == better  # same price, same cost
    # 200 g of flour at 5.5 kg raw per kg and ₹22/kg, plus 6% wastage
    assert abs(base - 0.2 * 5.5 * 22 * 1.06) < 0.01
    assert {e["key"] for e in free_extensions(BANANA, line)} == {"dried_figs"}


def test_banana_roadmap_adds_frying_oil_only_for_fried_products():
    fried = build_plan(
        "banana chips", {"stage": "idea"}, domain="banana_value_added", variants=["chips"]
    )
    dried = build_plan(
        "banana flour", {"stage": "idea"}, domain="banana_value_added", variants=["flour"]
    )

    def deliverables(p, mid):
        return next(m for m in p["roadmap"]["milestones"] if m["id"] == mid)["deliverables"]

    assert any("Frying-oil" in d for d in deliverables(fried, "b_trials"))
    assert not any("Frying-oil" in d for d in deliverables(dried, "b_trials"))
    assert any("Drying method" in d for d in deliverables(dried, "b_trials"))


def test_pump_controllers_cost_by_bill_of_materials_and_flag_connected():
    line, _ = resolve(PUMPS, ["dry run", "gsm remote"])
    kinds = {v.key: v.kind for v in line}
    assert kinds == {"dry_run": "standalone starter", "gsm_remote": "connected controller"}
    rows = {r["key"]: r for r in cost_sheet(PUMPS, line, monthly_packs=300)["rows"]}
    dry = PUMPS.recipes["dry_run"]["bom"]
    expected = sum(q * PUMPS.ingredients[k]["example_price_per_unit"] for k, q in dry.items())
    assert abs(rows["dry_run"]["ingredients"] - expected * 1.03) < 0.01
    plan = build_plan(
        "gsm starter",
        {"stage": "idea"},
        domain="pump_motor_controllers",
        variants=["gsm remote"],
        production_mode="co_packer",
    )
    cert = next(m for m in plan["roadmap"]["milestones"] if m["id"] == "p_cert")
    assert any("MTCTE" in d for d in cert["deliverables"])
    assert plan["domain"]["id"] == "pump_controllers"
    assert plan["domain_card"]["id"] == "pump_motor_controllers"


# ---- deep packs for the strongest district fits (Madurai, Coimbatore, Tiruppur) ----


@pytest.mark.parametrize(
    "text,pack",
    [
        ("export Madurai malli jasmine to Singapore", "jasmine_postharvest"),
        ("virgin coconut oil unit in Pollachi", "coconut_products"),
        ("printed t-shirts made through Tiruppur job work", "knitwear_small_batch"),
        ("banana chips fried in coconut oil", "banana_value_added"),
    ],
)
def test_new_packs_are_detected_without_stealing_others(text, pack):
    assert detect_pack(text) == pack


def test_new_packs_link_to_their_registry_cards():
    for domain in ("jasmine_postharvest", "coconut_products", "knitwear_small_batch"):
        plan = build_plan(domain.replace("_", " "), {"stage": "idea"}, domain=domain)
        assert plan["domain"]["id"] == domain and plan["domain_card"]["id"] == domain
        assert plan["costs"]["rows"], domain


def test_variant_keys_with_underscores_resolve():
    plan = build_plan("jasmine tea", {}, domain="jasmine_postharvest", variants=["jasmine_tea"])
    assert plan["unknown_variants"] == [] and plan["variants"][0]["kind"] == "food product"


def test_jasmine_milestones_follow_the_products():
    fresh = build_plan(
        "jasmine", {}, domain="jasmine_postharvest", variants=["fresh_export"], channels=["export"]
    )
    concrete = build_plan("jasmine", {}, domain="jasmine_postharvest", variants=["concrete"])
    tea = build_plan("jasmine", {}, domain="jasmine_postharvest", variants=["jasmine_tea"])
    titles = lambda p: {m["title"] for m in p["roadmap"]["milestones"]}  # noqa: E731
    assert "Cold chain and dispatch" in titles(fresh) and "Cold chain and dispatch" not in titles(
        tea
    )
    assert "Set up or contract extraction" in titles(concrete)
    assert (
        concrete["costs"]["rows"][0]["cogs"] > fresh["costs"]["rows"][0]["cogs"] * 50
    )  # ~350 kg/kg


def test_coconut_kinds_and_production_mode():
    own = build_plan(
        "coconut",
        {},
        domain="coconut_products",
        variants=["shell_charcoal"],
        production_mode="own_unit",
    )
    contract = build_plan(
        "coconut",
        {},
        domain="coconut_products",
        variants=["coconut_sugar"],
        production_mode="co_packer",
    )
    assert own["variants"][0]["kind"] == "shell product"
    assert contract["variants"][0]["kind"] == "neera product"
    own_titles = {m["title"] for m in own["roadmap"]["milestones"]}
    contract_titles = {m["title"] for m in contract["roadmap"]["milestones"]}
    assert "Set up a small processing unit" in own_titles
    assert "Pilot batch with a contract processor" in contract_titles


def test_knitwear_costs_by_the_piece_with_a_lighter_fabric_lever():
    plan = build_plan(
        "knitwear", {}, domain="knitwear_small_batch", variants=["basic_tee", "organic_tee"],
        monthly_packs=2000,
    )  # fmt: skip
    rows = {r["key"]: r["cogs"] for r in plan["costs"]["rows"]}
    assert rows["organic_tee"] > rows["basic_tee"]  # certified fabric costs more
    assert plan["costs"]["unit"] == "piece"
    lighter = [lv for lv in plan["costs"]["levers"] if "lighter fabric" in lv["lever"]]
    assert lighter and lighter[0]["saves_per_pack"] > 0
    assert {v["kind"] for v in plan["variants"]} == {"plain garment", "organic garment"}
