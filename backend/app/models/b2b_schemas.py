"""Pydantic schemas for the B2B matching endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MatchIn(BaseModel):
    category: str = Field(min_length=1)
    spec: str = ""
    quantity: int = Field(gt=0)
    budget_per_unit: float = Field(gt=0)
    district: str = ""
    state: str = ""
    tier: str = "raw_materials"


class SupplyOut(BaseModel):
    id: str
    name: str
    category: str
    unit_price: float
    max_capacity: int
    min_order: int
    district: str
    state: str
    trust_score: int
    payment_mode: str


class BreakdownOut(BaseModel):
    spec_similarity: int
    price_fit: int
    capacity_fit: int
    geo_proximity: int


class MatchItemOut(BaseModel):
    supply: SupplyOut
    weight: int
    base_weight: int
    breakdown: BreakdownOut


class MatchOut(BaseModel):
    category: str
    count: int
    matches: list[MatchItemOut]


class DecomposeIn(BaseModel):
    product: str = Field(min_length=2, max_length=500)
    monthly_units: int = Field(default=1000, gt=0)
    district: str = ""
    state: str = "Tamil Nadu"


class BOMLineOut(BaseModel):
    category: str
    spec: str
    qty_per_unit: float
    unit: str


class SupplyMapLineOut(BaseModel):
    line: BOMLineOut
    gap: bool
    matches: list[MatchItemOut]


class DecomposeOut(BaseModel):
    product: str
    monthly_units: int
    bom: list[BOMLineOut]
    supply_map: list[SupplyMapLineOut]
    gaps: int
