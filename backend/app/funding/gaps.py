"""Gap analysis (Req 4.2) — turn weak dimensions into a ranked action plan.

Each action declares the rubric inputs it would set and, where relevant, a
precondition. Its impact is the **real** change those inputs make to the
dimension score — computed by re-scoring the founder's own facts with the change
applied, never a hardcoded number (F-A4-018). Actions already done make no
change and are dropped; an action whose input the founder has not answered is
offered but marked "if not done yet". Sorted by impact-to-effort.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core.vocab import Stage, to_stage
from app.funding.readiness import ReadinessResult, score_readiness

GAP_THRESHOLD = 60


def _stage(facts: dict) -> Stage | None:
    try:
        return to_stage(facts.get("stage"))
    except ValueError:
        return None


def _below(target: Stage) -> Callable[[dict], bool]:
    """Offer the action only when the founder's stage is unknown or below target,
    so an MVP-stage founder is never told to ship an MVP (F-A4-018)."""
    return lambda f: (st := _stage(f)) is None or st < target


@dataclass(frozen=True)
class Action:
    label: str
    sets: dict[str, Any]  # the rubric inputs this action would set
    effort_weeks: int
    precondition: Callable[[dict], bool] | None = None


# dimension → actions, each mapped to the rubric input(s) it moves.
_PLAYBOOK: dict[str, list[Action]] = {
    "team": [
        Action("Bring a co-founder or key hire onto the team", {"team_size": 3}, 6),
        Action("Recruit 2–3 domain advisors", {"advisors_count": 3}, 3),
        Action("Add recognised domain expertise", {"has_domain_expertise": True}, 5),
    ],
    "product": [
        Action("Ship an MVP with the core feature set",
               {"stage": "mvp", "feature_completeness": 80}, 6, _below(Stage.MVP)),
        Action("File a provisional patent / register IP", {"has_ip": True}, 4),
    ],  # fmt: skip
    "traction": [
        Action("Run a paid pilot and validate the market", {"has_market_validation": True}, 5),
        Action("Instrument and improve 30-day retention", {"retention_rate": 60}, 4),
        Action("Sign 2 partnership LOIs", {"partnerships": 2}, 3),
    ],
    "financial": [
        Action("Build a 12-month model with unit economics",
               {"has_unit_economics": True, "has_projections": True}, 3),
        Action("Extend runway to 12 months", {"runway_months": 12}, 4),
    ],  # fmt: skip
    "pitch": [
        Action("Build a complete 10-slide pitch deck",
               {"has_pitch_deck": True, "deck_completeness": 100}, 2),
        Action("Sharpen the problem statement", {"has_clear_problem": True}, 1),
        Action("Add a competitive-differentiation slide", {"has_differentiation": True}, 1),
    ],  # fmt: skip
    "legal": [
        Action("Register the entity (Pvt Ltd / LLP)", {"is_registered": True}, 4),
        Action("Apply for DPIIT recognition", {"dpiit_recognized": True}, 2),
        Action("Organise the cap table", {"has_cap_table": True}, 1),
    ],
}


@dataclass
class Recommendation:
    dimension: str
    action: str
    impact_points: int
    effort_weeks: int
    conditional: bool = False  # the founder has not said whether this is already done

    @property
    def impact_label(self) -> str:
        return "High" if self.impact_points >= 8 else "Medium" if self.impact_points >= 4 else "Low"

    @property
    def ratio(self) -> float:
        return self.impact_points / max(1, self.effort_weeks)


def analyze_gaps(facts: dict[str, Any], readiness: ReadinessResult) -> list[Recommendation]:
    recs: list[Recommendation] = []
    for dim, score in readiness.dimensions.items():
        if score >= GAP_THRESHOLD:
            continue
        for action in _PLAYBOOK.get(dim, []):
            if action.precondition and not action.precondition(facts):
                continue
            after = score_readiness({**facts, **action.sets}).dimensions[dim]
            impact = after - readiness.dimensions[dim]
            if impact <= 0:  # already done, or the rubric does not reward it
                continue
            conditional = any(k not in facts or facts[k] is None for k in action.sets)
            recs.append(Recommendation(dim, action.label, impact, action.effort_weeks, conditional))
    recs.sort(key=lambda r: r.ratio, reverse=True)
    return recs
