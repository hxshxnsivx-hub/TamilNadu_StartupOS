"""Scheme Swarm supervisor — eligibility → ranking → explanation (Task 2.4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemes.engine import IneligibleScheme, NeedsInfoScheme, check_eligibility
from app.schemes.ranking import RankedScheme, rank_schemes


@dataclass
class Recommendation:
    ranked_eligible: list[RankedScheme]
    ineligible: list[IneligibleScheme]
    total_checked: int
    needs_info: list[NeedsInfoScheme] = field(default_factory=list)


class SchemeSwarm:
    """Retrieve → check eligibility (rules) → rank eligible → explain.

    Only *proven-eligible* schemes are ranked; schemes resting on missing facts
    are carried through as needs_info and listed after, never ranked or refused.
    """

    def recommend(self, profile: dict, funding_need: int | None = None) -> Recommendation:
        result = check_eligibility(profile)
        ranked = rank_schemes(profile, result.eligible, funding_need)
        return Recommendation(
            ranked_eligible=ranked,
            ineligible=result.ineligible,
            total_checked=result.total_checked,
            needs_info=result.needs_info,
        )
