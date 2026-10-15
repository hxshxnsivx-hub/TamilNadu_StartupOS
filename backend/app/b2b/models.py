"""B2B domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Tier(str, Enum):
    T1_MATERIALS = "raw_materials"
    T2_SERVICES = "services"
    T3_TECH = "tech_api"
    T4_CODEV = "co_development"


@dataclass
class SupplyProfile:
    id: str
    name: str
    category: str  # match key, e.g. "yarn" | "dye" | "pcb" | "packaging"
    tier: Tier
    spec: str  # free-text specification / offering
    unit_price: float  # ₹ per unit
    max_capacity: int  # units / month
    min_order: int  # minimum order quantity
    district: str
    state: str
    trust_score: int = 50  # 0–100
    payment_mode: str = "cash"  # cash | barter | either


@dataclass
class DemandRequest:
    category: str
    spec: str
    quantity: int  # units / month
    budget_per_unit: float  # ₹
    district: str
    state: str
    tier: Tier = Tier.T1_MATERIALS


@dataclass
class MatchBreakdown:
    spec_similarity: int
    price_fit: int
    capacity_fit: int
    geo_proximity: int


@dataclass
class Match:
    supply: SupplyProfile
    weight: int  # final 0–100 (after trust adjustment)
    base_weight: int  # before trust adjustment
    breakdown: MatchBreakdown = field(default=None)  # type: ignore[assignment]
