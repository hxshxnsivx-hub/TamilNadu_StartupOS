"""Pydantic schemas for the funding readiness endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReadinessIn(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)


class RecommendationOut(BaseModel):
    dimension: str
    action: str
    impact: str
    impact_points: int
    effort_weeks: int


class ReadinessOut(BaseModel):
    overall: int
    band: str
    dimensions: dict[str, int]
    gaps: list[RecommendationOut]


class InvestorMatchIn(BaseModel):
    startup: dict[str, Any] = Field(default_factory=dict)
    funding_need: int = Field(gt=0)
    readiness_overall: int = Field(ge=0, le=100)


class InvestorOut(BaseModel):
    id: str
    name: str
    type: str
    min_ticket: int
    max_ticket: int
    track_record_score: int
    thesis: str


class EligibleInvestorOut(BaseModel):
    investor: InvestorOut
    fit: int


class IneligibleInvestorOut(BaseModel):
    investor: InvestorOut
    reasons: list[str]


class InvestorMatchOut(BaseModel):
    total_checked: int
    eligible: list[EligibleInvestorOut]
    ineligible: list[IneligibleInvestorOut]


class PipelineHistoryItem(BaseModel):
    stage: str
    at: str


class PipelineEntryModel(BaseModel):
    investor_id: str
    investor_name: str = ""
    stage: str = "initial_contact"
    amount: int = 0
    history: list[PipelineHistoryItem] = Field(default_factory=list)


class PipelineAdvanceIn(BaseModel):
    entry: PipelineEntryModel
    to_stage: str
    at: str | None = None


class PipelineAdvanceOut(BaseModel):
    entry: PipelineEntryModel
    next_stages: list[str]


class PipelineBoardIn(BaseModel):
    entries: list[PipelineEntryModel] = Field(default_factory=list)


class PipelineMetricsOut(BaseModel):
    total: int
    by_stage: dict[str, int]
    open_count: int
    won: int
    lost: int
    win_rate: int
    stage_conversion: dict[str, int]
    avg_days_in_stage: dict[str, float]
    pipeline_value: int
    weighted_value: int


class PipelineColumnOut(BaseModel):
    stage: str
    count: int
    value: int
    entries: list[PipelineEntryModel]


class PipelineBoardOut(BaseModel):
    stages: list[str]
    columns: list[PipelineColumnOut]
    metrics: PipelineMetricsOut
