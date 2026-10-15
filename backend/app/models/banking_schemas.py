"""Pydantic schemas for the bank loan routing endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LoanNeedIn(BaseModel):
    amount_lakh: float = Field(gt=0, le=100_000)
    purpose: Literal["wc", "tl", "startup", "micro"]
    years_in_business: int = Field(default=0, ge=0, le=100)
    sector: str | None = None
    gst_registered: bool = False
    gst_months: int = Field(default=0, ge=0)
    women_owned: bool = False
    dpiit: bool = False
    can_offer_collateral: bool = False
    self_help_group: bool = False
    qualifies_for_subsidy: bool | None = None
    needs_within_week: bool = False


class AllocateIn(BaseModel):
    need: LoanNeedIn
    pin: str = Field(pattern=r"^[1-9]\d{5}$")
    radius_km: float = Field(default=10.0, gt=0, le=30)
    limit: int = Field(default=5, ge=1, le=20)


class SchemeOut(BaseModel):
    id: str
    bank: str | None
    name: str
    category: str
    min_lakh: float | None
    max_lakh: float | None
    collateral: str
    pricing: str
    for_whom: str
    digital: bool
    details: list[str]
    source_url: str
    confidence: str


class RejectedOut(BaseModel):
    scheme: SchemeOut
    reasons: list[str]


class StepOut(BaseModel):
    question: str
    answer: str


class RailOut(BaseModel):
    primary: str
    also: list[str]
    collateral_route: str
    guarantee_options: list[str]
    steps: list[StepOut]


class MatchOut(BaseModel):
    rail: RailOut
    loans: list[SchemeOut]
    guarantees: list[SchemeOut]
    rejected: list[RejectedOut]


class BranchOut(BaseModel):
    ifsc: str
    bank: str
    type: str
    branch: str
    address: str
    pin: str
    km: float  # straight line
    located_by: str
    travel_min: float  # by road from the pin's centre, free-flow
    road_km: float
    travel_basis: str  # "road_network" | "estimate"


class BranchesOut(BaseModel):
    pin: str
    located: bool
    radius_km: float
    count: int
    by_type: dict[str, int]
    branches: list[BranchOut]
    note: str


class OptionOut(BaseModel):
    scheme: SchemeOut
    branch: BranchOut | None
    channel: str
    score: int
    signals: dict[str, float]


class AllocateOut(BaseModel):
    rail: RailOut
    pin_located: bool
    options: list[OptionOut]
    guarantees: list[SchemeOut]
    signals_used: list[str]
    signals_missing: list[str]
    note: str
