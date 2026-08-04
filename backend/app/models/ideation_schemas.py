"""Pydantic schemas for the ideation / orchestrator / completeness endpoints."""

from __future__ import annotations

from typing import Any

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
