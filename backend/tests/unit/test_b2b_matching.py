"""Unit tests for B2B edge-weight matching."""

from app.b2b.matching import _capacity_fit, _geo, _price_fit, match_demand
from app.b2b.models import DemandRequest, SupplyProfile, Tier

M = Tier.T1_MATERIALS


def _supply(**kw) -> SupplyProfile:
    base = dict(
        id="x",
        name="X",
        category="yarn",
        tier=M,
        spec="yarn",
        unit_price=100.0,
        max_capacity=10_000,
        min_order=100,
        district="Erode",
        state="Tamil Nadu",
    )
    base.update(kw)
    return SupplyProfile(**base)


# ── component functions (deterministic) ──────────────────────────────────────
def test_price_fit():
    assert _price_fit(200, 180) == 100  # under budget
    assert _price_fit(200, 200) == 100  # at budget
    assert _price_fit(100, 150) < 100  # over budget penalised
    assert _price_fit(100, 300) == 0  # way over → floored


def test_capacity_fit():
    s = _supply(max_capacity=5000, min_order=500)
    assert _capacity_fit(1000, s) == 100  # within band
    assert _capacity_fit(10000, s) == 50  # exceeds capacity (5000/10000)
    assert _capacity_fit(250, s) == 50  # below min order (250/500)


def test_geo():
    d = DemandRequest("yarn", "y", 100, 100, "Tiruppur", "Tamil Nadu")
    assert _geo(d, _supply(district="Tiruppur", state="Tamil Nadu")) == 100
    assert _geo(d, _supply(district="Salem", state="Tamil Nadu")) == 70
    assert _geo(d, _supply(district="Pune", state="Maharashtra")) == 40


# ── end-to-end matching ──────────────────────────────────────────────────────
async def test_match_ranks_closer_cheaper_higher_trust_first():
    d = DemandRequest("yarn", "combed cotton yarn 40s count", 2000, 190, "Tiruppur", "Tamil Nadu")
    matches = await match_demand(d)
    assert len(matches) == 2  # only the two yarn suppliers
    assert matches[0].supply.id == "y1"  # Tiruppur, cheaper, trust 85 → top
    assert all(0 <= m.weight <= 100 for m in matches)


async def test_category_filter():
    d = DemandRequest("pcb", "2-layer FR4 PCB", 100, 200, "Coimbatore", "Tamil Nadu")
    matches = await match_demand(d)
    assert {m.supply.category for m in matches} == {"pcb"}


async def test_unknown_category_returns_nothing():
    d = DemandRequest("spaceship", "warp core", 1, 1000, "Chennai", "Tamil Nadu")
    assert await match_demand(d) == []


async def test_high_trust_boosts_weight():
    d = DemandRequest("yarn", "combed cotton yarn 40s count", 2000, 190, "Tiruppur", "Tamil Nadu")
    matches = await match_demand(d)
    y1 = next(m for m in matches if m.supply.id == "y1")
    assert y1.weight >= y1.base_weight  # trust 85 → ×1.2 boost
