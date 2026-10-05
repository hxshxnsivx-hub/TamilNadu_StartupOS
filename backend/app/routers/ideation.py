"""Ideation, orchestrator-routing and completeness-preview endpoints (Task 1.9).

These are stateless (no database), so "describe an idea → get a roadmap" works
without any external service. Persistence (linking roadmaps to founders) is added
when the profile/startup DB endpoints land.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models.ideation_schemas import (
    CategoryOut,
    CompletenessIn,
    CompletenessOut,
    DomainOut,
    HybridOut,
    IdeaIn,
    IdeaOut,
    MilestoneOut,
    PlanIn,
    PlanOut,
    RoadmapOut,
    RouteIn,
    RouteOut,
    SchemeTagOut,
    TimelineOut,
)
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.state import ConversationState
from app.planner import registry
from app.planner.packs import COMMON, load_packs
from app.planner.plan import build_plan
from app.research.scan import scan
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


@router.get("/ideation/domains", response_model=list[DomainOut])
async def domains() -> list[DomainOut]:
    """Product domains with their own questions, variants and roadmap steps."""
    return [
        DomainOut(
            id=p.id,
            label=p.label,
            about=p.about,
            questions=p.questions,
            starting_variants=[r["label"] for r in p.recipes.values()],
        )
        for p in load_packs().values()
        if p.id != COMMON
    ]


@router.post("/ideation/plan", response_model=PlanOut)
async def plan(body: PlanIn) -> PlanOut:
    """A specific plan from the founder's answers: variants, costs and a roadmap that responds."""
    if (
        body.domain
        and body.domain not in load_packs()
        and body.domain not in registry.load()["domains"]
    ):
        raise HTTPException(status_code=422, detail=f"Unknown domain: {body.domain}")
    return PlanOut(
        **build_plan(
            body.text,
            body.slots,
            domain=body.domain,
            variants=body.variants,
            fmt=body.format,
            production_mode=body.production_mode,
            channels=body.channels,
            monthly_packs=body.monthly_packs,
            prices=body.prices,
            costing=body.costing,
            confidence=body.confidence,
        )
    )


_DISTRICT = Query(default=None, pattern="^(chennai|coimbatore|tiruppur|madurai|tiruchirappalli)$")


@router.get("/ideation/categories", response_model=list[CategoryOut])
async def categories() -> list[CategoryOut]:
    """StartupTN policy categories, with how many product domains each holds."""
    reg = registry.load()
    return [
        CategoryOut(
            id=c["id"],
            label=c["label"],
            kind=c["kind"],
            neighbours=c["neighbours"],
            domains=sum(1 for d in reg["domains"].values() if d["category"] == c["id"]),
        )
        for c in reg["categories"].values()
    ]


@router.get("/ideation/registry")
async def domain_registry(
    category: str | None = Query(default=None), district: str | None = _DISTRICT
) -> list[dict]:
    """Product domains, best fit for the district first, with schemes, licences and trends."""
    if category and category not in registry.load()["categories"]:
        raise HTTPException(status_code=422, detail=f"Unknown category: {category}")
    return [registry.card(d, district) for d in registry.domains(category, district)]


@router.get("/ideation/registry/{domain_id}")
async def domain_card(domain_id: str, district: str | None = _DISTRICT) -> dict:
    d = registry.load()["domains"].get(domain_id)
    if d is None:
        raise HTTPException(status_code=404, detail=f"No domain {domain_id}")
    return registry.card(d, district)


@router.get("/ideation/hybrids", response_model=list[HybridOut])
async def hybrid_products(
    domain: str | None = Query(default=None),
    district: str | None = _DISTRICT,
    neighbours_only: bool = True,
    limit: int = Query(default=20, ge=1, le=200),
) -> list[HybridOut]:
    """Cross-bred products: a domain plus a product its kind of business uses."""
    if domain and domain not in registry.load()["domains"]:
        raise HTTPException(status_code=404, detail=f"No domain {domain}")
    return [HybridOut(**h) for h in registry.hybrids(domain, district, neighbours_only, limit)]


class ScanIn(BaseModel):
    text: str = Field(min_length=10, max_length=4000)
    # parts of the idea to check one by one (the agent's language model can supply these)
    elements: list[str] = Field(default_factory=list, max_length=8)
    # search terms written by the agent's language model, replacing the built-in lexicon
    queries: dict[str, str] | None = None


@router.post("/ideation/scan")
async def scan_idea(body: ScanIn) -> dict:
    """Prior art for any idea: associated domains, papers, trials, open projects, patents,
    local players, element-by-element checks and what to discuss, with source coverage."""
    return await scan(body.text, elements=body.elements, queries=body.queries)
