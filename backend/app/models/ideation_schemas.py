"""Pydantic schemas for the ideation / orchestrator / completeness endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── orchestrator route ───────────────────────────────────────────────────────
class RouteIn(BaseModel):
    message: str = Field(min_length=1)


class RouteOut(BaseModel):
    intent: str
    swarm: str
    confidence: float
    action: str
    matched: list[str]


# ── ideation / roadmap ───────────────────────────────────────────────────────
class IdeaIn(BaseModel):
    text: str = Field(min_length=3, max_length=4000)
    language: str = "en"
    # Optional profile → milestones get annotated with eligible schemes.
    founder: dict[str, Any] | None = None
    startup: dict[str, Any] | None = None


class TimelineOut(BaseModel):
    optimistic: int
    realistic: int
    pessimistic: int


class SchemeTagOut(BaseModel):
    id: str
    name: str
    level: str
    type: str
    max_funding: int


class MilestoneOut(BaseModel):
    id: str
    phase: str
    title: str
    deliverables: list[str]
    timeline: TimelineOut
    depends_on: list[str]
    critical: bool
    schemes: list[SchemeTagOut] = []


class IdeaOut(BaseModel):
    problem: str | None
    solution: str | None
    target_market: str | None
    value_proposition: str | None
    differentiation: str | None
    domain: str | None
    missing_elements: list[str]


class RoadmapOut(BaseModel):
    idea: IdeaOut
    feasibility_score: int
    feasibility_breakdown: dict[str, int]
    milestones: list[MilestoneOut]
    critical_path: list[str]
    clarifications: list[str]


# ── completeness preview (stateless) ─────────────────────────────────────────
class CompletenessIn(BaseModel):
    founder: dict[str, Any] = Field(default_factory=dict)
    startup: dict[str, Any] | None = None
    has_verified_documents: bool = False


class CompletenessOut(BaseModel):
    score: int
    tier: str
    missing_fields: list[str]
    verified_fields: list[str]


# ── domain-aware plan: variants, costs, roadmap (app/planner) ────────────────
class PlanIn(BaseModel):
    text: str = Field(default="", max_length=4000)
    slots: dict[str, Any] = Field(default_factory=dict)  # elicitation slots: stage, district, ...
    domain: str | None = None  # a pack id; detected from text when omitted
    variants: list[str] | None = None
    format: Literal["loose_leaf", "tea_bags", "iced"] | None = None
    production_mode: Literal["co_packer", "own_unit"] | None = None
    channels: list[Literal["online", "retail", "horeca"]] | None = None
    monthly_packs: int | None = Field(default=None, ge=1, le=10_000_000)
    prices: dict[str, float] | None = None  # ingredient -> your quoted ₹ per kg
    costing: dict[str, Any] | None = None  # override pack cost assumptions
    confidence: float = Field(default=0.8, ge=0, le=1)


class PlanMilestoneOut(BaseModel):
    id: str
    phase: str
    title: str
    deliverables: list[str]
    months: dict[str, int]
    depends_on: list[str]
    critical: bool
    why: str
    because: list[str]
    risks: list[str] = []
    from_pack: str = Field(alias="from")

    model_config = {"populate_by_name": True}


class PlanRoadmapOut(BaseModel):
    milestones: list[PlanMilestoneOut]
    critical_path: list[str]
    months_realistic: int


class PlanOut(BaseModel):
    domain: dict[str, str] | None
    domain_card: dict[str, Any] | None = None
    domain_note: str | None
    risks_by_phase: dict[str, list[dict[str, Any]]] = {}
    variants: list[dict[str, Any]]
    unknown_variants: list[str]
    recipe_note: str
    shared_ingredients: list[dict[str, Any]]
    free_extensions: list[dict[str, Any]]
    sourcing: list[dict[str, str]]
    costs: dict[str, Any] | None
    regulatory: list[dict[str, str]]
    roadmap: PlanRoadmapOut
    next_questions: list[dict[str, Any]]


class DomainOut(BaseModel):
    id: str
    label: str
    about: str
    questions: list[dict[str, Any]]
    starting_variants: list[str]


class CategoryOut(BaseModel):
    id: str
    label: str
    kind: str
    neighbours: list[str]
    domains: int


class HybridOut(BaseModel):
    id: str
    title: str
    anchor: dict[str, str]
    partner: dict[str, str]
    partner_supplies: list[str]
    anchor_supplies: list[str]
    new_scheme_routes: list[dict[str, Any]]
    scheme_routes_total: int
    district_fit: dict[str, int]
    risk: dict[str, int]
    integration_risk: str
    score: int
