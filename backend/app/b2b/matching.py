"""B2B edge-weight matching (design 2.3 · Graph Engine scoring).

Edge weight blends four components with the canonical 40/30/20/10 weighting, then
trust adjusts the result ±20% (design Req 3.4.8). Spec similarity uses the
Embedding Service (offline hash provider in dev; BGE-M3 in prod). Everything else
is deterministic arithmetic, so ranking is fully testable.
"""

from __future__ import annotations

from app.b2b.models import DemandRequest, Match, MatchBreakdown, SupplyProfile
from app.b2b.seed import SEED_SUPPLY
from app.services.embeddings import EmbeddingService, get_embedding_service

W_SPEC, W_PRICE, W_CAPACITY, W_GEO = 0.40, 0.30, 0.20, 0.10


def _price_fit(budget: float, price: float) -> int:
    if budget <= 0:
        return 50
    ratio = price / budget
    if ratio <= 1.0:
        return 100
    return max(0, round(100 - (ratio - 1.0) * 200))


def _capacity_fit(qty: int, supply: SupplyProfile) -> int:
    if qty > supply.max_capacity:
        return round(supply.max_capacity / qty * 100)
    if qty < supply.min_order:
        return round(qty / supply.min_order * 100)
    return 100


def _geo(demand: DemandRequest, supply: SupplyProfile) -> int:
    if demand.district and demand.district == supply.district:
        return 100
    if demand.state and demand.state == supply.state:
        return 70
    return 40


def _trust_factor(trust: int) -> float:
    if trust > 80:
        return 1.2
    if trust < 30:
        return 0.8
    return 1.0


async def score_match(demand: DemandRequest, supply: SupplyProfile, svc: EmbeddingService) -> Match:
    dv = await svc.embed_one(demand.spec, kind="query")
    sv = await svc.embed_one(supply.spec, kind="passage")
    cos = EmbeddingService.cosine_similarity(dv, sv)
    spec = max(0, min(100, round((cos + 1) / 2 * 100)))

    price = _price_fit(demand.budget_per_unit, supply.unit_price)
    capacity = _capacity_fit(demand.quantity, supply)
    geo = _geo(demand, supply)

    base = round(W_SPEC * spec + W_PRICE * price + W_CAPACITY * capacity + W_GEO * geo)
    weight = min(100, round(base * _trust_factor(supply.trust_score)))

    return Match(
        supply=supply,
        weight=weight,
        base_weight=base,
        breakdown=MatchBreakdown(spec, price, capacity, geo),
    )


async def match_demand(
    demand: DemandRequest, supply: list[SupplyProfile] | None = None
) -> list[Match]:
    supply = supply if supply is not None else SEED_SUPPLY
    svc = get_embedding_service()
    candidates = [s for s in supply if s.category == demand.category]
    matches = [await score_match(demand, s, svc) for s in candidates]
    matches.sort(key=lambda m: m.weight, reverse=True)
    return matches
