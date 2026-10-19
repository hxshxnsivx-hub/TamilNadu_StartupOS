"""Ideation, orchestrator-routing and completeness-preview endpoints (Task 1.9).

These are stateless (no database), so "describe an idea → get a roadmap" works
without any external service. Persistence (linking roadmaps to founders) is added
when the profile/startup DB endpoints land.
"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.agents import ideation as agent
from app.agents import providers
from app.agents.jobs import KINDS, board
from app.agents.store import VersionConflict, get_store
from app.agents.tools import compact_scan, council_brief
from app.core.stages import Stage
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


_Item = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class ProfileIn(BaseModel):
    """What the founder's profile already says, never asked again (R019, R081).

    Only these keys: the browser projects its profile onto them
    (frontend agentClient.profileForConversation), so caste category, phone
    and date of birth never leave it. Sizes and types are bounded here; each
    value then passes its slot's rules in engine.start, and one that fits no
    slot (a district outside Tamil Nadu, a domain with no sector) is asked.
    """

    model_config = ConfigDict(extra="forbid")

    district: str | None = Field(default=None, max_length=80)
    # the profile's startup domain, free text the slot maps onto a Sector
    sector: str | None = Field(default=None, max_length=120)
    stage: Stage | None = None
    founder_years: int | None = Field(default=None, ge=0, le=40)
    founder_skills: list[_Item] | None = Field(default=None, max_length=10)
    owned_assets: list[_Item] | None = Field(default=None, max_length=10)


class AgentStartIn(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    profile: ProfileIn | None = None
    # search nothing outside Vanigam for this conversation
    private: bool = False
    # the founder agrees that their incubator or programme may see this session in
    # aggregates of 5 or more founders (never the idea text or name)
    share_with_programme: bool = False


class AgentTurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    # the founder's language this turn (ta-IN, en-IN, hi-IN); the reply follows it
    language: str | None = Field(default=None, pattern=r"^(ta|en|hi)-IN$")
    # names this turn: the phone sends the same id again when the connection drops,
    # and gets the saved turn back instead of a second one (R038)
    client_turn_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{8,64}$")


_SESSION_ID = Path(pattern=r"^[0-9a-f]{32}$")
# One turn at a time per conversation in this process; the version check in the
# store covers several processes.
_turn_locks: dict[str, asyncio.Lock] = {}


async def _load(session_id: str) -> agent.AgentSession:
    s = await (await get_store()).get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return s


async def _save(s: agent.AgentSession) -> None:
    try:
        await (await get_store()).save(s)
    except VersionConflict as exc:
        raise HTTPException(
            status_code=409, detail="This conversation changed elsewhere; reload it"
        ) from exc


@router.post("/ideation/agent/sessions")
async def agent_start(body: AgentStartIn) -> dict:
    """Open an ideation conversation; the reply is the greeting."""
    s, greeting = agent.new_session(
        body.name,
        body.profile.model_dump(exclude_none=True, mode="json") if body.profile else None,
        private=body.private,
        share_with_programme=body.share_with_programme,
    )
    store = await get_store()
    await store.create(s)
    providers.warm_up()  # the local backup model loads while the founder reads and types
    return {
        "session_id": s.id,
        "reply": greeting,
        "action": {"kind": "ask", "slot": None},
        "saved": store.name == "database",
    }


@router.get("/ideation/agent/sessions/{session_id}")
async def agent_resume(session_id: str = _SESSION_ID) -> dict:
    """Where a conversation stands, to resume it on any device, with the results
    that finished while nobody was listening."""
    s = await _load(session_id)
    return agent.snapshot(s, {kind: await board.take(session_id, kind) for kind in KINDS})


@router.delete("/ideation/agent/sessions/{session_id}", status_code=204, response_class=Response)
async def agent_delete(session_id: str = _SESSION_ID) -> Response:
    """Delete a conversation with its transcript, evidence and roadmap."""
    if not await (await get_store()).delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    await board.forget(session_id)  # its background work and results go too
    return Response(status_code=204)


@router.post("/ideation/agent/sessions/{session_id}/turns")
async def agent_turn(body: AgentTurnIn, session_id: str = _SESSION_ID) -> dict:
    """One founder turn: the reply, the next question, and the evidence it rests on."""
    async with _turn_locks.setdefault(session_id, asyncio.Lock()):
        s = await _load(session_id)
        # checked under the lock, after loading: a retry waits for a slow original
        if (saved := agent.replay(s, body.client_turn_id)) is not None:
            return saved[-1]["data"]
        out = await agent.turn(
            s, body.text, language=body.language, client_turn_id=body.client_turn_id
        )
        await _save(s)
        return out


@router.post("/ideation/agent/sessions/{session_id}/turns/stream")
async def agent_turn_stream(body: AgentTurnIn, session_id: str = _SESSION_ID):
    """The same turn as server-sent events: ack, sentence…, tool, evidence, done.

    Only `sentence` events are meant for speech; each has passed the fact check.
    A turn is applied only if `done` arrives; a stream that ends without it was
    not saved, and the client sends it again with the same `client_turn_id`.
    A failure after the stream started is an `error` event with a `code`
    (`conflict`: changed elsewhere, reload; `failed`: the turn broke), since the
    status is already 200 by then (R159).
    """
    lock = _turn_locks.setdefault(session_id, asyncio.Lock())
    await lock.acquire()
    try:
        s = await _load(session_id)
    except HTTPException:
        lock.release()
        raise
    if (saved := agent.replay(s, body.client_turn_id)) is not None:
        lock.release()  # nothing to save: the turn was applied the first time

        async def again():
            for ev in saved:
                yield _sse(ev["event"], ev["data"])

        return StreamingResponse(again(), media_type="text/event-stream")

    async def events():
        try:
            async for ev in agent.turn_stream(
                s, body.text, language=body.language, client_turn_id=body.client_turn_id
            ):
                if ev["event"] == "done":
                    try:
                        await _save(s)
                    except HTTPException as exc:
                        yield _sse("error", {"code": "conflict", "detail": exc.detail})
                        return
                yield _sse(ev["event"], ev["data"])
        except Exception as exc:  # the stream has started; report, don't crash it
            yield _sse("error", {"code": "failed", "detail": f"turn failed: {type(exc).__name__}"})
        finally:
            lock.release()

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/ideation/agent/sessions/{session_id}/notices")
async def agent_notices(
    session_id: str = _SESSION_ID,
    limit: int = Query(default=0, ge=0, le=100),
):
    """Background work as it finishes (server-sent events), so the screen can show the
    evidence, novelty and review panel before the next turn: `evidence`, `novelty`,
    `council`. A comment line every 15 s keeps the connection open. `limit` ends the
    stream after that many notices (0: until the screen closes it).

    A (re)subscribe first sends the latest finished result of each kind, so work
    that finished while the connection was down is not lost (R143); the screen
    replaces its panels, so a repeat is harmless."""
    await _load(session_id)  # 404 for an unknown session
    q = board.subscribe(session_id)
    missed = [
        {"kind": kind, "payload": r} for kind in KINDS if (r := await board.take(session_id, kind))
    ]

    async def events():
        sent = 0
        try:
            while not limit or sent < limit:
                if missed:
                    n = missed.pop(0)
                else:
                    try:
                        n = await asyncio.wait_for(q.get(), timeout=15)
                    except TimeoutError:
                        yield ": still here\n\n"
                        continue
                if n["kind"] == "research":
                    yield _sse("evidence", compact_scan(n["payload"]["scan"]))
                    yield _sse("novelty", n["payload"]["novelty"])
                elif n["kind"] == "council":
                    yield _sse("council", council_brief(n["payload"]))
                sent += 1
        finally:
            board.unsubscribe(session_id, q)

    return StreamingResponse(events(), media_type="text/event-stream")


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
