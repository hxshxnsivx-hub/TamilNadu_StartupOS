"""Ideation, orchestrator-routing and completeness-preview endpoints (Task 1.9).

These are stateless (no database), so "describe an idea → get a roadmap" works
without any external service. Persistence (linking roadmaps to founders) is added
when the profile/startup DB endpoints land.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.models.ideation_schemas import (
    CompletenessIn,
    CompletenessOut,
    IdeaIn,
    IdeaOut,
    MilestoneOut,
    RoadmapOut,
    RouteIn,
    RouteOut,
    SchemeTagOut,
    TimelineOut,
)
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.state import ConversationState
from app.schemes.annotate import annotate_roadmap
from app.schemes.models import Scheme
from app.services.completeness import CompletenessInput, score_completeness
from app.swarms.roadmap import RoadmapSwarm
from app.swarms.roadmap.models import Roadmap

router = APIRouter(prefix="/api/v1", tags=["ideation"])

_orchestrator = Orchestrator()
_roadmap = RoadmapSwarm()


@router.post("/orchestrator/route", response_model=RouteOut)
async def route(body: RouteIn) -> RouteOut:
    """Classify a message and show which swarm would handle it."""
    state = ConversationState(user_id="anon", session_id="preview")
    d = _orchestrator.handle_turn(state, body.message)
    return RouteOut(
        intent=d.intent,
        swarm=d.swarm,
        confidence=d.confidence,
        action=d.action,
        matched=list(d.matched),
    )


def _scheme_tag(s: Scheme) -> SchemeTagOut:
    return SchemeTagOut(
        id=s.id, name=s.name, level=s.level, type=s.type.value, max_funding=s.max_funding
    )


def _to_out(rm: Roadmap, annotations: dict[str, list[Scheme]] | None = None) -> RoadmapOut:
    annotations = annotations or {}
    return RoadmapOut(
        idea=IdeaOut(
            problem=rm.idea.problem,
            solution=rm.idea.solution,
            target_market=rm.idea.target_market,
            value_proposition=rm.idea.value_proposition,
            differentiation=rm.idea.differentiation,
            domain=rm.idea.domain,
            missing_elements=rm.idea.missing_elements(),
        ),
        feasibility_score=rm.feasibility.score,
        feasibility_breakdown=rm.feasibility.breakdown,
        milestones=[
            MilestoneOut(
                id=m.id,
                phase=m.phase.value,
                title=m.title,
                deliverables=m.deliverables,
                timeline=TimelineOut(
                    optimistic=m.timeline.optimistic,
                    realistic=m.timeline.realistic,
                    pessimistic=m.timeline.pessimistic,
                ),
                depends_on=m.depends_on,
                critical=m.critical,
                schemes=[_scheme_tag(s) for s in annotations.get(m.id, [])],
            )
            for m in rm.milestones
        ],
        critical_path=rm.critical_path,
        clarifications=rm.clarifications,
    )


@router.post("/ideation/roadmap", response_model=RoadmapOut)
async def roadmap(body: IdeaIn) -> RoadmapOut:
    """Turn a free-text idea into a roadmap; annotate with schemes if a profile is given."""
    rm = _roadmap.generate(body.text)
    annotations = None
    if body.founder is not None:
        annotations = annotate_roadmap({"founder": body.founder, "startup": body.startup}, rm)
    return _to_out(rm, annotations)


@router.post("/profiles/completeness", response_model=CompletenessOut)
async def completeness(body: CompletenessIn) -> CompletenessOut:
    """Stateless completeness preview (mirrors the profile scorer)."""
    r = score_completeness(
        CompletenessInput(
            founder=body.founder,
            startup=body.startup,
            has_verified_documents=body.has_verified_documents,
        )
    )
    return CompletenessOut(
        score=r.score,
        tier=r.tier,
        missing_fields=r.missing_fields,
        verified_fields=r.verified_fields,
    )
