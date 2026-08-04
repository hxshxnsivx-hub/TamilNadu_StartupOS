"""Profile completeness scoring (Req 1.1.4 · design.md CompletenessScorer).

Deterministic, cumulative tiers — no LLM. A tier is only reached when every
lower tier is satisfied, so score ∈ {0, 40, 60, 80, 100}:

    40  → basic demographics complete
    60  → + education complete
    80  → + startup details complete
    100 → + at least one verified document
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

BASIC_FIELDS: tuple[str, ...] = (
    "name",
    "email",
    "phone",
    "date_of_birth",
    "gender",
    "state",
    "district",
    "city",
)
EDUCATION_FIELDS: tuple[str, ...] = (
    "highest_qualification",
    "institution",
    "graduation_year",
)
STARTUP_FIELDS: tuple[str, ...] = ("startup_name", "entity_type", "domain", "stage")


@dataclass
class CompletenessInput:
    founder: dict[str, Any]
    startup: dict[str, Any] | None = None
    has_verified_documents: bool = False


@dataclass
class CompletenessResult:
    score: int
    tier: str
    missing_fields: list[str] = field(default_factory=list)
    verified_fields: list[str] = field(default_factory=list)


_TIER_LABEL = {
    0: "incomplete",
    40: "basic",
    60: "standard",
    80: "verified",
    100: "investment_ready",
}


def _present(data: dict[str, Any] | None, fields: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """Split *fields* into (present, missing) by truthy presence in *data*."""
    data = data or {}
    present = [f for f in fields if data.get(f) not in (None, "", [])]
    missing = [f for f in fields if f not in present]
    return present, missing


def score_completeness(inp: CompletenessInput) -> CompletenessResult:
    basic_present, basic_missing = _present(inp.founder, BASIC_FIELDS)
    edu_present, edu_missing = _present(inp.founder, EDUCATION_FIELDS)
    startup_present, startup_missing = _present(inp.startup, STARTUP_FIELDS)

    verified: list[str] = list(basic_present)
    score = 0
    missing: list[str] = []

    basic_ok = not basic_missing
    edu_ok = basic_ok and not edu_missing
    startup_ok = edu_ok and not startup_missing
    docs_ok = startup_ok and inp.has_verified_documents

    if basic_ok:
        score = 40
        verified += edu_present
    if edu_ok:
        score = 60
        verified += startup_present
    if startup_ok:
        score = 80
    if docs_ok:
        score = 100
        verified.append("verified_documents")

    # Report only the fields blocking the *next* tier — actionable guidance.
    if not basic_ok:
        missing = [f"founder.{f}" for f in basic_missing]
    elif not edu_ok:
        missing = [f"founder.{f}" for f in edu_missing]
    elif not startup_ok:
        missing = [f"startup.{f}" for f in startup_missing]
    elif not docs_ok:
        missing = ["documents.verified"]

    return CompletenessResult(
        score=score,
        tier=_TIER_LABEL[score],
        missing_fields=missing,
        verified_fields=verified,
    )
