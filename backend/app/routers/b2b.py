"""B2B matching endpoint (Task 3.2/3.4) — stateless supplier matching."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.b2b.allocate import Line, allocate, pair
from app.b2b.decompose import build_supply_map
from app.b2b.directory import suppliers_for
from app.b2b.matching import match_demand
from app.b2b.models import DemandRequest, Match, SupplyProfile, Tier
from app.b2b.seed import SEED_SUPPLY
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
            nearby_makers=suppliers_for(
                sl.line.category, district=body.district.lower() or None, limit=3
            )["suppliers"],
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


# ---- real suppliers, order splitting and one-to-one pairing ------------------------


class DirectoryIn(BaseModel):
    category: str = Field(min_length=2, max_length=40)
    pin: str | None = Field(default=None, pattern=r"^6\d{5}$")
    district: str | None = Field(default=None, pattern=r"^[a-z]+$")
    limit: int = Field(default=10, ge=1, le=50)


@router.post("/directory")
async def directory(body: DirectoryIn) -> dict:
    """Real Tamil Nadu companies registered for this kind of supply, nearest first."""
    return suppliers_for(body.category, pin=body.pin, district=body.district, limit=body.limit)


class QuoteIn(BaseModel):
    """A supplier with a known price and capacity: a quote the founder received."""

    id: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    category: str
    unit_price: float = Field(gt=0)
    max_capacity: int = Field(gt=0)
    min_order: int = Field(default=1, ge=1)
    district: str = ""
    trust_score: int = Field(default=50, ge=0, le=100)


class LineIn(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    category: str
    quantity: int = Field(gt=0, le=10_000_000)
    max_unit_price: float | None = Field(default=None, gt=0)
    district: str | None = None


class AllocateIn(BaseModel):
    lines: list[LineIn] = Field(min_length=1, max_length=20)
    quotes: list[QuoteIn] = Field(default_factory=list, max_length=100)
    # the invented example suppliers (app/b2b/seed.py): tests and demos only
    include_catalogue: bool = False
    max_suppliers_per_line: int = Field(default=2, ge=1, le=5)


def _supply(q: QuoteIn) -> SupplyProfile:
    return SupplyProfile(
        q.id, q.name, q.category, Tier.T1_MATERIALS, "", q.unit_price, q.max_capacity,
        q.min_order, q.district, "Tamil Nadu", trust_score=q.trust_score,
    )  # fmt: skip


@router.post("/allocate")
async def allocate_orders(body: AllocateIn) -> dict:
    """Split each line's monthly quantity across suppliers (CP-SAT), with reasons for
    any shortfall."""
    suppliers = [_supply(q) for q in body.quotes]
    if body.include_catalogue:
        taken = {s.id for s in suppliers}
        suppliers += [s for s in SEED_SUPPLY if s.id not in taken]
    lines = [Line(x.id, x.category, x.quantity, x.max_unit_price, x.district) for x in body.lines]
    return allocate(lines, suppliers, body.max_suppliers_per_line)


class PairIn(BaseModel):
    demands: list[MatchIn] = Field(min_length=1, max_length=50)
    quotes: list[QuoteIn] = Field(default_factory=list, max_length=100)
    include_catalogue: bool = False  # invented examples: tests and demos only


@router.post("/pair")
async def pair_partners(body: PairIn) -> dict:
    """One supplier per demand, one demand per supplier, maximising total fit."""
    suppliers = [_supply(q) for q in body.quotes]
    if body.include_catalogue:
        suppliers += SEED_SUPPLY
    demands = [
        DemandRequest(d.category, d.spec, d.quantity, d.budget_per_unit, d.district, d.state)
        for d in body.demands
    ]
    return pair(demands, suppliers)
