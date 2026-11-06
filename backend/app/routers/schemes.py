"""Scheme eligibility endpoint (Task 2.6) — stateless, rules-based."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.scheme_schemas import (
    EligibilityIn,
    EligibilityOut,
    IneligibleOut,
    NeedsInfoOut,
    RankedSchemeOut,
    RecommendIn,
    RecommendOut,
    SchemeOut,
)
from app.schemes.engine import NeedsInfoScheme, check_eligibility
from app.schemes.models import Scheme
from app.schemes.swarm import SchemeSwarm

router = APIRouter(prefix="/api/v1/schemes", tags=["schemes"])
_swarm = SchemeSwarm()

# A plain question for each founder-fact path a rule can leave unknown, so the
# screen can ask instead of refusing (F-B4-008). Unmapped paths fall back to the
# path itself; richer phrasing arrives with the typed FounderFacts contract (T04.2).
_QUESTIONS: dict[str, str] = {
    "founder.age": "How old are you?",
    "founder.date_of_birth": "What is your date of birth?",
    "founder.gender": "What is your gender?",
    "founder.social_category": "Which social category do you belong to (General/OBC/SC/ST)?",
    "founder.state": "Which state are you in?",
    "founder.district": "Which district are you in?",
    "startup.stage": "What stage is your startup at?",
    "startup.sector": "Which sector is your startup in?",
    "startup.is_registered": "Is your business registered yet?",
    "startup.incorporation_age_years": "How long ago was the business incorporated?",
    "startup.annual_turnover": "What is your annual turnover?",
    "startup.dpiit_recognized": "Do you have DPIIT recognition?",
}


def _questions_for(missing: list[str]) -> list[str]:
    return [_QUESTIONS.get(path, path) for path in missing]


def _needs_info_out(items: list[NeedsInfoScheme]) -> list[NeedsInfoOut]:
    return [
        NeedsInfoOut(
            scheme=_scheme_out(n.scheme),
            missing=n.missing,
            questions=_questions_for(n.missing),
        )
        for n in items
    ]


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
        needs_info=_needs_info_out(res.needs_info),
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
        needs_info=_needs_info_out(rec.needs_info),
        ineligible=[
            IneligibleOut(scheme=_scheme_out(i.scheme), reasons=i.reasons) for i in rec.ineligible
        ],
    )
