"""Scheme eligibility endpoint (Task 2.6) — stateless, rules-based."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.scheme_schemas import (
    EligibilityIn,
    EligibilityOut,
    IneligibleOut,
    RankedSchemeOut,
    RecommendIn,
    RecommendOut,
    SchemeOut,
)
from app.schemes.engine import check_eligibility
from app.schemes.models import Scheme
from app.schemes.swarm import SchemeSwarm

router = APIRouter(prefix="/api/v1/schemes", tags=["schemes"])
_swarm = SchemeSwarm()


def _scheme_out(s: Scheme) -> SchemeOut:
    return SchemeOut(
        id=s.id,
        name=s.name,
        type=s.type.value,
        agency=s.agency,
        level=s.level,
        min_funding=s.min_funding,
        max_funding=s.max_funding,
        benefits=s.benefits,
        source_url=s.source_url,
        last_verified=s.last_verified,
        unmodelled_notes=s.unmodelled_notes,
    )


@router.post("/eligibility", response_model=EligibilityOut)
async def eligibility(body: EligibilityIn) -> EligibilityOut:
    """Return schemes the profile is proven eligible for, plus reasons for the rest."""
    res = check_eligibility({"founder": body.founder, "startup": body.startup})
    return EligibilityOut(
        total_checked=res.total_checked,
        eligible=[_scheme_out(s) for s in res.eligible],
        ineligible=[
            IneligibleOut(scheme=_scheme_out(i.scheme), reasons=i.reasons) for i in res.ineligible
        ],
    )


@router.post("/recommend", response_model=RecommendOut)
async def recommend(body: RecommendIn) -> RecommendOut:
    """Eligible schemes ranked by relevance + approval-likelihood, with reasons."""
    rec = _swarm.recommend(
        {"founder": body.founder, "startup": body.startup}, funding_need=body.funding_need
    )
    return RecommendOut(
        total_checked=rec.total_checked,
        ranked_eligible=[
            RankedSchemeOut(
                scheme=_scheme_out(r.scheme),
                relevance=r.relevance,
                likelihood=r.likelihood,
                why=r.why,
            )
            for r in rec.ranked_eligible
        ],
        ineligible=[
            IneligibleOut(scheme=_scheme_out(i.scheme), reasons=i.reasons) for i in rec.ineligible
        ],
    )
