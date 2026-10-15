"""Pydantic schemas for the scheme eligibility endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EligibilityIn(BaseModel):
    founder: dict[str, Any] = Field(default_factory=dict)
    startup: dict[str, Any] | None = None


class SchemeOut(BaseModel):
    id: str
    name: str
    type: str
    agency: str
    level: str
    min_funding: int
    max_funding: int
    benefits: str
    source_url: str
    last_verified: str
    unmodelled_notes: list[str]


class IneligibleOut(BaseModel):
    scheme: SchemeOut
    reasons: list[str]


class EligibilityOut(BaseModel):
    total_checked: int
    eligible: list[SchemeOut]
    ineligible: list[IneligibleOut]


class RecommendIn(BaseModel):
    founder: dict[str, Any] = Field(default_factory=dict)
    startup: dict[str, Any] | None = None
    funding_need: int | None = None


class RankedSchemeOut(BaseModel):
    scheme: SchemeOut
    relevance: int
    likelihood: int
    why: list[str]


class RecommendOut(BaseModel):
    total_checked: int
    ranked_eligible: list[RankedSchemeOut]
    ineligible: list[IneligibleOut]
