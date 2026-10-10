"""Funding readiness endpoint (Task 4.7) — stateless six-dimension assessment."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import AppError
from app.funding.gaps import analyze_gaps
from app.funding.investor_match import Investor, match_investors
from app.funding.pipeline import (
    STAGES,
    PipelineEntry,
    advance,
    kanban,
    next_stages,
    pipeline_metrics,
)
from app.funding.readiness import score_readiness
from app.models.funding_schemas import (
    EligibleInvestorOut,
    IneligibleInvestorOut,
    InvestorMatchIn,
    InvestorMatchOut,
    InvestorOut,
    PipelineAdvanceIn,
    PipelineAdvanceOut,
    PipelineBoardIn,
    PipelineBoardOut,
    ReadinessIn,
    ReadinessOut,
    RecommendationOut,
)

router = APIRouter(prefix="/api/v1/funding", tags=["funding"])


def _investor_out(inv: Investor) -> InvestorOut:
    return InvestorOut(
        id=inv.id,
        name=inv.name,
        type=inv.type,
        min_ticket=inv.min_ticket,
        max_ticket=inv.max_ticket,
        track_record_score=inv.track_record_score,
        thesis=inv.thesis,
        ticket_known=inv.ticket_known,
        source_url=inv.source_url,
    )


@router.post("/readiness", response_model=ReadinessOut)
async def readiness(body: ReadinessIn) -> ReadinessOut:
    """Score funding readiness across six dimensions and return a ranked gap plan."""
    result = score_readiness(body.profile)
    gaps = analyze_gaps(result)
    return ReadinessOut(
        overall=result.overall,
        band=result.band,
        dimensions=result.dimensions,
        gaps=[
            RecommendationOut(
                dimension=g.dimension,
                action=g.action,
                impact=g.impact_label,
                impact_points=g.impact_points,
                effort_weeks=g.effort_weeks,
            )
            for g in gaps
        ],
    )


@router.post("/investors/match", response_model=InvestorMatchOut)
async def investors_match(body: InvestorMatchIn) -> InvestorMatchOut:
    """Match investors whose hard constraints the startup meets, ranked by fit."""
    res = match_investors(body.startup, body.funding_need, body.readiness_overall)
    return InvestorMatchOut(
        total_checked=res.total_checked,
        eligible=[
            EligibleInvestorOut(investor=_investor_out(e.investor), fit=e.fit) for e in res.eligible
        ],
        ineligible=[
            IneligibleInvestorOut(investor=_investor_out(i.investor), reasons=i.reasons)
            for i in res.ineligible
        ],
    )


@router.post("/pipeline/advance", response_model=PipelineAdvanceOut)
async def pipeline_advance(body: PipelineAdvanceIn) -> PipelineAdvanceOut:
    """Move an investor relationship to the next stage, validating the transition."""
    try:
        entry = PipelineEntry.from_dict(body.entry.model_dump())
        moved = advance(entry, body.to_stage, body.at)
    except ValueError as exc:
        raise AppError(
            "INVALID_PIPELINE_TRANSITION",
            str(exc),
            status_code=422,
            suggestions=[
                f"Allowed from here: {', '.join(next_stages(body.entry.stage)) or 'none'}"
            ],
        ) from exc
    return PipelineAdvanceOut(entry=moved.to_dict(), next_stages=next_stages(moved.stage))


@router.post("/pipeline/board", response_model=PipelineBoardOut)
async def pipeline_board(body: PipelineBoardIn) -> PipelineBoardOut:
    """Return the pipeline as Kanban columns plus conversion / value metrics."""
    try:
        entries = [PipelineEntry.from_dict(e.model_dump()) for e in body.entries]
    except ValueError as exc:
        raise AppError("INVALID_PIPELINE_ENTRY", str(exc), status_code=422) from exc
    metrics = pipeline_metrics(entries)
    return PipelineBoardOut(
        stages=STAGES,
        columns=kanban(entries),
        metrics=metrics.__dict__,
    )
