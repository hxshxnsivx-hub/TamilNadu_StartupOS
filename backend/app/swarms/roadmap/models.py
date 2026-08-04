"""Domain models for the Roadmap Swarm."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Phase(str, Enum):
    IDEATION = "Ideation"
    VALIDATION = "Validation"
    MVP = "MVP"
    LAUNCH = "Launch"
    GROWTH = "Growth"
    SCALE = "Scale"


CONCEPT_ELEMENTS = ("problem", "solution", "target_market", "value_proposition", "differentiation")


@dataclass
class StartupIdea:
    raw_text: str
    problem: str | None = None
    solution: str | None = None
    target_market: str | None = None
    value_proposition: str | None = None
    differentiation: str | None = None
    domain: str | None = None

    def missing_elements(self) -> list[str]:
        return [e for e in CONCEPT_ELEMENTS if not getattr(self, e)]


@dataclass
class Timeline:
    optimistic: int
    realistic: int
    pessimistic: int


@dataclass
class Milestone:
    id: str
    phase: Phase
    title: str
    deliverables: list[str]
    timeline: Timeline
    depends_on: list[str] = field(default_factory=list)
    critical: bool = False


@dataclass
class Feasibility:
    score: int
    breakdown: dict[str, int]


@dataclass
class Roadmap:
    idea: StartupIdea
    feasibility: Feasibility
    milestones: list[Milestone]
    critical_path: list[str]
    clarifications: list[str]
