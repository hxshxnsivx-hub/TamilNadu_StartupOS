"""Funding readiness scoring (Req 4.1 · design E6) — six dimensions, 0–100.

Each dimension is scored by an explicit rubric of inputs. Crucially, a missing
input is *unknown*, not a zero: it lowers the dimension's **coverage**, and a
dimension the founder has barely answered (coverage below 50%) is reported as
"not assessed" and left out of the overall score, which is the weighted mean
over the assessed dimensions only. So readiness never counts answers the founder
never gave (F-A4-016). For a fully answered profile the dimension points and the
overall are identical to the earlier scorer. Deterministic — no LLM.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.vocab import Stage, to_stage

WEIGHTS = {
    "team": 0.20,
    "product": 0.20,
    "traction": 0.25,
    "financial": 0.15,
    "pitch": 0.10,
    "legal": 0.10,
}

# Keyed by the canonical Stage, so every spelling ("revenue", "launched", "scaling")
# scores the same. A revenue-stage founder no longer falls through to 0 (F-A4-015).
_STAGE_SCORE = {
    Stage.IDEA: 10,
    Stage.POC: 20,
    Stage.PROTOTYPE: 25,
    Stage.MVP: 35,
    Stage.REVENUE: 45,
    Stage.GROWTH: 50,
}

COVERAGE_FLOOR = 0.5  # a dimension below this is "not assessed"
NOT_ENOUGH = "Not enough answers"

Kind = str  # "num" | "flag" | "stage"


@dataclass(frozen=True)
class Input:
    """One rubric input: where to read it, and the points it is worth."""

    key: str
    kind: Kind
    points: Callable[[Any], float]
    max_points: float  # the most this input can contribute, for ranking next_inputs


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _present(p: dict, inp: Input) -> bool:
    """Did the founder actually answer this input? Absent or null is unknown; a
    flag that is explicitly False is a real (known) answer and counts as covered."""
    if inp.key not in p or p[inp.key] is None:
        return False
    if inp.kind == "num":
        return _num(p[inp.key]) is not None
    if inp.kind == "stage":
        return to_stage(p[inp.key]) is not None
    return True  # flag: True or False both count


def _value_points(p: dict, inp: Input) -> float:
    if inp.kind == "num":
        return inp.points(_num(p[inp.key]) or 0.0)
    if inp.kind == "stage":
        return inp.points(to_stage(p[inp.key]))
    return inp.points(bool(p[inp.key]))


# Each dimension's inputs, reproducing the earlier scorer exactly for a fully
# answered profile. Per-dimension points still cap at 100 via _clamp.
RUBRIC: dict[str, list[Input]] = {
    "team": [
        Input("founder_experience_years", "num", lambda v: min(40, v * 8), 40),
        Input("team_size", "num", lambda v: min(25, v * 8), 25),
        Input("has_domain_expertise", "flag", lambda v: 20 if v else 0, 20),
        Input("advisors_count", "num", lambda v: min(15, v * 5), 15),
    ],
    "product": [
        Input("stage", "stage", lambda v: _STAGE_SCORE.get(v, 0), 50),
        Input("feature_completeness", "num", lambda v: v * 0.25, 25),
        Input("has_ip", "flag", lambda v: 25 if v else 0, 25),
    ],
    "traction": [
        Input("users", "num", lambda v: min(25, v / 40), 25),
        Input("monthly_revenue", "num", lambda v: min(25, v / 4000), 25),
        Input("retention_rate", "num", lambda v: v * 0.20, 20),
        Input("partnerships", "num", lambda v: min(15, v * 5), 15),
        Input("has_market_validation", "flag", lambda v: 15 if v else 0, 15),
    ],
    "financial": [
        Input("runway_months", "num", lambda v: min(30, v * 2.5), 30),
        Input("revenue_growth_pct", "num", lambda v: min(25, v), 25),
        Input("has_unit_economics", "flag", lambda v: 25 if v else 0, 25),
        Input("has_projections", "flag", lambda v: 20 if v else 0, 20),
    ],
    "pitch": [
        Input("has_pitch_deck", "flag", lambda v: 40 if v else 0, 40),
        Input("deck_completeness", "num", lambda v: v * 0.30, 30),
        Input("has_clear_problem", "flag", lambda v: 15 if v else 0, 15),
        Input("has_differentiation", "flag", lambda v: 15 if v else 0, 15),
    ],
    "legal": [
        Input("is_registered", "flag", lambda v: 30 if v else 0, 30),
        Input("dpiit_recognized", "flag", lambda v: 20 if v else 0, 20),
        Input("has_ip_filing", "flag", lambda v: 20 if v else 0, 20),
        Input("is_compliant", "flag", lambda v: 15 if v else 0, 15),
        Input("has_cap_table", "flag", lambda v: 15 if v else 0, 15),
    ],
}


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


def _band(score: int) -> str:
    if score <= 40:
        return "Not Ready"
    if score <= 60:
        return "Developing"
    if score <= 80:
        return "Ready"
    return "Highly Ready"


@dataclass
class ReadinessResult:
    dimensions: dict[str, int]
    overall: int
    band: str
    coverage: dict[str, float] = field(default_factory=dict)
    not_assessed: list[str] = field(default_factory=list)
    next_inputs: list[str] = field(default_factory=list)


def _dimension(p: dict, inputs: list[Input]) -> tuple[int, float, list[Input]]:
    """Return (score, coverage, missing inputs) for one dimension."""
    present = [inp for inp in inputs if _present(p, inp)]
    missing = [inp for inp in inputs if not _present(p, inp)]
    score = _clamp(sum(_value_points(p, inp) for inp in present))
    coverage = len(present) / len(inputs) if inputs else 0.0
    return score, coverage, missing


def score_readiness(profile: dict[str, Any]) -> ReadinessResult:
    dims: dict[str, int] = {}
    coverage: dict[str, float] = {}
    missing: dict[str, list[Input]] = {}
    for name, inputs in RUBRIC.items():
        dims[name], coverage[name], missing[name] = _dimension(profile, inputs)

    not_assessed = [d for d in RUBRIC if coverage[d] < COVERAGE_FLOOR]
    assessed = [d for d in RUBRIC if coverage[d] >= COVERAGE_FLOOR]

    if assessed:
        wsum = sum(WEIGHTS[d] for d in assessed)
        overall = _clamp(sum(dims[d] * WEIGHTS[d] for d in assessed) / wsum)
        band = _band(overall)
    else:
        overall, band = 0, NOT_ENOUGH

    # What to answer next: the missing inputs worth the most, weighted by their
    # dimension, so the founder is pointed at the answers that move the score.
    ranked = sorted(
        (inp for d in RUBRIC for inp in missing[d]),
        key=lambda inp: -next(
            WEIGHTS[d] * inp.max_points for d in RUBRIC if inp in missing[d]
        ),
    )
    next_inputs = [inp.key for inp in ranked[:5]]

    return ReadinessResult(
        dimensions=dims,
        overall=overall,
        band=band,
        coverage={d: round(c, 2) for d, c in coverage.items()},
        not_assessed=not_assessed,
        next_inputs=next_inputs,
    )
