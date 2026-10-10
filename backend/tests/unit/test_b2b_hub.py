"""B2B hub: real-company directory, CP-SAT order splitting, bipartite pairing."""

from __future__ import annotations

from app.b2b.allocate import Line, allocate, pair
from app.b2b.directory import CATEGORY_NIC, suppliers_for
from app.b2b.models import DemandRequest, SupplyProfile, Tier
from httpx import AsyncClient


def _s(id_, category, price, cap, min_order=1, district="Tiruppur", trust=50):
    return SupplyProfile(id_, id_, category, Tier.T1_MATERIALS, "", price, cap, min_order,
                         district, "Tamil Nadu", trust_score=trust)  # fmt: skip


def test_directory_returns_real_makers_nearest_first():
    r = suppliers_for("pump", pin="641004", district="coimbatore", limit=5)
    assert r["known"] and r["total"] > 0 and r["source"].startswith("MCA")
    rows = r["suppliers"]
    assert all(s["activity_code"].startswith(("2912", "51")) for s in rows)
    makers = [s for s in rows if s["kind"] == "maker"]
    assert makers and makers[0]["district"] == "coimbatore"
    kms = [s["km"] for s in makers if s["km"] is not None]
    assert kms == sorted(kms)


def test_directory_says_when_a_category_is_not_mapped():
    r = suppliers_for("spaceship")
    assert r["known"] is False and r["suppliers"] == []


def test_every_mapped_category_finds_someone():
    for category in CATEGORY_NIC:
        assert suppliers_for(category, limit=1)["total"] > 0, category


def test_allocation_fills_cheapest_first_and_respects_capacity():
    sup = [
        _s("cheap", "yarn", 170, 3000),
        _s("mid", "yarn", 180, 10000),
        _s("dear", "yarn", 210, 8000),
    ]
    r = allocate([Line("a", "yarn", 12000, 200)], sup)
    splits = {x["supplier_id"]: x["units"] for x in r["lines"][0]["splits"]}
    assert r["status"] == "optimal" and splits == {"cheap": 3000, "mid": 9000}
    assert r["lines"][0]["unmet"] == 0 and r["total_cost"] == 3000 * 170 + 9000 * 180


def test_supplier_capacity_is_shared_across_lines():
    sup = [_s("only", "yarn", 100, 5000)]
    r = allocate([Line("a", "yarn", 4000), Line("b", "yarn", 4000)], sup)
    placed = sum(x["units"] for ln in r["lines"] for x in ln["splits"])
    assert placed == 5000 and sum(ln["unmet"] for ln in r["lines"]) == 3000


def test_shortfalls_come_with_reasons():
    sup = [_s("dear", "yarn", 250, 9000), _s("big_moq", "dye", 50, 9000, min_order=1000)]
    r = allocate([Line("a", "yarn", 100, 200), Line("b", "dye", 10), Line("c", "foam", 5)], sup)
    why = {ln["line"]: " ".join(ln["why_unmet"]) for ln in r["lines"]}
    assert "above your ₹200" in why["a"]
    assert "minimum order above your quantity" in why["b"]
    assert "use the directory" in why["c"]


def test_minimum_orders_and_supplier_limit_hold():
    sup = [_s(f"s{i}", "pcb", 100 + i, 1000, min_order=200) for i in range(4)]
    r = allocate([Line("a", "pcb", 2500)], sup, max_suppliers_per_line=3)
    splits = r["lines"][0]["splits"]
    assert len(splits) <= 3 and all(x["units"] >= 200 for x in splits)


def test_pairing_is_one_to_one_and_maximises_fit():
    sup = [_s("near", "yarn", 180, 5000, district="Tiruppur", trust=85),
           _s("far", "yarn", 180, 5000, district="Salem")]  # fmt: skip
    demands = [
        DemandRequest("yarn", "", 3000, 200, "Tiruppur", "Tamil Nadu"),
        DemandRequest("yarn", "", 3000, 200, "Salem", "Tamil Nadu"),
    ]
    r = pair(demands, sup)
    chosen = {p["demand"]: p["supplier_id"] for p in r["pairs"]}
    assert chosen == {0: "near", 1: "far"} and r["unpaired"] == []
    assert len({p["supplier_id"] for p in r["pairs"]}) == len(r["pairs"])


async def test_hub_endpoints(client: AsyncClient):
    r = await client.post("/api/v1/b2b/directory", json={"category": "packaging", "pin": "600032"})
    assert r.status_code == 200 and r.json()["suppliers"]
    r = await client.post(
        "/api/v1/b2b/allocate",
        json={"lines": [{"id": "a", "category": "yarn", "quantity": 12000, "max_unit_price": 215}],
              "quotes": [{"id": "q1", "name": "Quote", "category": "yarn", "unit_price": 175,
                          "max_capacity": 3000}]},
    )  # fmt: skip
    assert r.status_code == 200 and r.json()["lines"][0]["unmet"] == 0
    r = await client.post(
        "/api/v1/b2b/decompose", json={"product": "smart sensor device", "district": "Chennai"}
    )
    assert any(line["nearby_makers"] for line in r.json()["supply_map"])
