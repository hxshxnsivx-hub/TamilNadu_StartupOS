"""B2B matching endpoint (Task 3.2/3.4) — stateless supplier matching."""

from __future__ import annotations

from fastapi import APIRouter

from app.b2b.decompose import build_supply_map
from app.b2b.matching import match_demand
from app.b2b.models import DemandRequest, Match, Tier
from app.models.b2b_schemas import (
    BOMLineOut,
    BreakdownOut,
    DecomposeIn,
    DecomposeOut,
    MatchIn,
    MatchItemOut,
    MatchOut,
    SupplyMapLineOut,
    SupplyOut,
)

router = APIRouter(prefix="/api/v1/b2b", tags=["b2b"])


def _item(m: Match) -> MatchItemOut:
    s = m.supply
    return MatchItemOut(
        supply=SupplyOut(
            id=s.id,
            name=s.name,
            category=s.category,
            unit_price=s.unit_price,
            max_capacity=s.max_capacity,
            min_order=s.min_order,
            district=s.district,
            state=s.state,
            trust_score=s.trust_score,
            payment_mode=s.payment_mode,
        ),
        weight=m.weight,
        base_weight=m.base_weight,
        breakdown=BreakdownOut(
            spec_similarity=m.breakdown.spec_similarity,
            price_fit=m.breakdown.price_fit,
            capacity_fit=m.breakdown.capacity_fit,
            geo_proximity=m.breakdown.geo_proximity,
        ),
    )


@router.post("/match", response_model=MatchOut)
async def match(body: MatchIn) -> MatchOut:
    """Rank suppliers for a demand by weighted edge score (spec/price/capacity/geo + trust)."""
    tier = Tier(body.tier) if body.tier in Tier._value2member_map_ else Tier.T1_MATERIALS
    demand = DemandRequest(
        category=body.category.lower().strip(),
        spec=body.spec,
        quantity=body.quantity,
        budget_per_unit=body.budget_per_unit,
        district=body.district,
        state=body.state,
        tier=tier,
    )
    matches = await match_demand(demand)
    return MatchOut(
        category=demand.category,
        count=len(matches),
        matches=[_item(m) for m in matches],
    )


@router.post("/decompose", response_model=DecomposeOut)
async def decompose(body: DecomposeIn) -> DecomposeOut:
    """Break a product into a draft BOM and map each line to ranked suppliers."""
    smap = await build_supply_map(body.product, body.monthly_units, body.district, body.state)
    supply_map = [
        SupplyMapLineOut(
            line=BOMLineOut(
                category=sl.line.category,
                spec=sl.line.spec,
                qty_per_unit=sl.line.qty_per_unit,
                unit=sl.line.unit,
            ),
            gap=sl.gap,
            matches=[_item(m) for m in sl.matches],
        )
        for sl in smap
    ]
    return DecomposeOut(
        product=body.product,
        monthly_units=body.monthly_units,
        bom=[s.line for s in supply_map],
        supply_map=supply_map,
        gaps=sum(1 for s in supply_map if s.gap),
    )
