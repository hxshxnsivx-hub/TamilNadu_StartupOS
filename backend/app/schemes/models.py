"""Scheme domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.schemes.rules import RuleGroup


class SchemeType(str, Enum):
    GRANT = "grant"
    LOAN = "loan"
    SUBSIDY = "subsidy"
    INCUBATION = "incubation"
    GUARANTEE = "guarantee"


@dataclass
class Scheme:
    id: str
    name: str
    type: SchemeType
    agency: str
    level: str  # "central" | "state" | "bank"
    min_funding: int  # ₹
    max_funding: int  # ₹
    sectors: list[str]  # sector-agnostic if empty
    eligibility: RuleGroup
    benefits: str
    source_url: str
    last_verified: str  # ISO date — shown in UI (freshness, design §B)
    unmodelled_notes: list[str] = field(default_factory=list)  # surfaced verbatim
    # Ranking metadata (Task 2.4)
    target_stages: list[str] = field(default_factory=list)  # stages the scheme suits
    preference_axes: list[str] = field(default_factory=list)  # women|sc_st|first_graduate|rural
