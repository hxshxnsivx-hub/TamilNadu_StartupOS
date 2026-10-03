"""Bank loan routing endpoints — rails, scheme matching, branch allocation by pin code."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Query

from app.banking.allocate import allocate
from app.banking.branches import get_branch_index
from app.banking.matcher import match
from app.banking.models import BankScheme, Branch, LoanNeed
from app.banking.router import RailDecision, decide
from app.models.banking_schemas import (
    AllocateIn,
    AllocateOut,
    BranchesOut,
    BranchOut,
    LoanNeedIn,
    MatchOut,
    OptionOut,
    RailOut,
    RejectedOut,
    SchemeOut,
    StepOut,
)

router = APIRouter(prefix="/api/v1/banking", tags=["banking"])

_DISTANCE_NOTE = (
    "Distances are straight-line, between pin-code centres (about ±2–3 km). "
    "Only the five pilot districts are indexed."
)


def _scheme(s: BankScheme) -> SchemeOut:
    return SchemeOut(
        id=s.id,
        bank=s.bank,
        name=s.name,
        category=s.category,
        min_lakh=s.min_lakh,
        max_lakh=s.max_lakh,
        collateral=s.collateral,
        pricing=s.pricing,
        for_whom=s.for_whom,
        digital=s.digital,
        details=list(s.details),
        source_url=s.source_url,
        confidence=s.confidence,
    )


def _branch(b: Branch, km: float) -> BranchOut:
    return BranchOut(
        ifsc=b.ifsc, bank=b.bank, type=b.type, branch=b.branch, address=b.address, pin=b.pin, km=km
    )


def _rail(r: RailDecision) -> RailOut:
    return RailOut(
        primary=r.primary,
        also=r.also,
        collateral_route=r.collateral_route,
        guarantee_options=r.guarantee_options,
        steps=[StepOut(question=s.question, answer=s.answer) for s in r.steps],
    )


def _need(n: LoanNeedIn) -> LoanNeed:
    return LoanNeed(**n.model_dump())


@router.get("/branches", response_model=BranchesOut)
async def branches(
    pin: str = Query(pattern=r"^[1-9]\d{5}$"),
    radius_km: float = Query(default=10.0, gt=0, le=30),
) -> BranchesOut:
    """Bank branches near a pin code, nearest first, with a count per kind of bank."""
    index = get_branch_index()
    near = index.nearby(pin, radius_km)
    return BranchesOut(
        pin=pin,
        located=index.locate(pin) is not None,
        radius_km=radius_km,
        count=len(near),
        by_type=dict(Counter(b.type for b, _ in near)),
        branches=[_branch(b, km) for b, km in near],
        note=_DISTANCE_NOTE,
    )


@router.post("/match", response_model=MatchOut)
async def match_schemes(body: LoanNeedIn) -> MatchOut:
    """Bank loan schemes that fit, guarantees that can sit on top, and reasons for the rest."""
    need = _need(body)
    res = match(need)
    return MatchOut(
        rail=_rail(decide(need)),
        loans=[_scheme(m.scheme) for m in res.loans],
        guarantees=[_scheme(m.scheme) for m in res.guarantees],
        rejected=[RejectedOut(scheme=_scheme(m.scheme), reasons=m.reasons) for m in res.rejected],
    )


@router.post("/allocate", response_model=AllocateOut)
async def allocate_loan(body: AllocateIn) -> AllocateOut:
    """Ranked (scheme, nearest branch) options for a founder's pin code, with the rail to take."""
    a = allocate(_need(body.need), body.pin, body.radius_km, body.limit)
    return AllocateOut(
        rail=_rail(a.rail),
        pin_located=a.pin_located,
        options=[
            OptionOut(
                scheme=_scheme(o.scheme),
                branch=_branch(o.branch, o.km) if o.branch else None,
                channel=o.channel,
                score=o.score,
                signals=o.signals,
            )
            for o in a.options
        ],
        guarantees=[_scheme(g) for g in a.guarantees],
        signals_used=a.signals_used,
        signals_missing=a.signals_missing,
        note=_DISTANCE_NOTE
        + " Branch track record and speed are not scored yet; they need sanction data.",
    )
