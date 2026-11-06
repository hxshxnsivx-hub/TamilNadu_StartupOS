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
    conditional: bool = False


class ReadinessOut(BaseModel):
    overall: int
    band: str
    dimensions: dict[str, int]
    coverage: dict[str, float] = Field(default_factory=dict)
    not_assessed: list[str] = Field(default_factory=list)
    next_inputs: list[str] = Field(default_factory=list)
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
    track_record_score: int | None  # None: no source rates this investor
    thesis: str
    # most investors do not publish a ticket size; then min/max are 0 and this is False
    ticket_known: bool = True
    source_url: str | None = None


class EligibleInvestorOut(BaseModel):
    investor: InvestorOut
    fit: int
    why: list[str] = Field(default_factory=list)


class CheckWithInvestorOut(BaseModel):
    investor: InvestorOut
    unknowns: list[str]


class IneligibleInvestorOut(BaseModel):
    investor: InvestorOut
    reasons: list[str]


class InvestorMatchOut(BaseModel):
    total_checked: int
    eligible: list[EligibleInvestorOut]
    check_with: list[CheckWithInvestorOut] = Field(default_factory=list)
    ineligible: list[IneligibleInvestorOut]
    readiness_advice: str = ""


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
    value_by_stage: dict[str, int]


class PipelineColumnOut(BaseModel):
    stage: str
    count: int
    value: int
    entries: list[PipelineEntryModel]


class PipelineBoardOut(BaseModel):
    stages: list[str]
    columns: list[PipelineColumnOut]
    metrics: PipelineMetricsOut
