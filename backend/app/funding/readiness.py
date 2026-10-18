"""Funding readiness scoring (Req 4.1 · design E6) — six dimensions, 0–100.

Each dimension is scored by an explicit rubric over a founder-supplied profile
(missing inputs score low). The overall score is the weighted mean; bands mirror
the spec. Deterministic and fully testable — no LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.stages import Stage, parse_stage

WEIGHTS = {
    "team": 0.20,
    "product": 0.20,
    "traction": 0.25,
    "financial": 0.15,
    "pitch": 0.10,
    "legal": 0.10,
}

# Every Stage has a score (tests/unit/test_stages.py); a word that is not a stage scores 0.
STAGE_SCORE: dict[Stage, int] = {
    Stage.IDEA: 10,
    Stage.POC: 20,
    Stage.PROTOTYPE: 25,
    Stage.MVP: 35,
    Stage.REVENUE: 45,
    Stage.GROWTH: 50,
    Stage.SCALE: 50,
}


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


def _num(d: dict, k: str, default: float = 0.0) -> float:
    v = d.get(k, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _flag(d: dict, k: str) -> bool:
    return bool(d.get(k, False))


def _team(p: dict) -> int:
    return _clamp(
        min(40, _num(p, "founder_experience_years") * 8)
        + min(25, _num(p, "team_size") * 8)
        + (20 if _flag(p, "has_domain_expertise") else 0)
        + min(15, _num(p, "advisors_count") * 5)
    )


def _stage_score(p: dict) -> int:
    stage = parse_stage(p.get("stage"))
    return STAGE_SCORE[stage] if stage else 0


def _product(p: dict) -> int:
    return _clamp(
        _stage_score(p) + _num(p, "feature_completeness") * 0.25 + (25 if _flag(p, "has_ip") else 0)
    )


def _traction(p: dict) -> int:
    return _clamp(
        min(25, _num(p, "users") / 40)
        + min(25, _num(p, "monthly_revenue") / 4000)
        + _num(p, "retention_rate") * 0.20
        + min(15, _num(p, "partnerships") * 5)
        + (15 if _flag(p, "has_market_validation") else 0)
    )


def _financial(p: dict) -> int:
    return _clamp(
        min(30, _num(p, "runway_months") * 2.5)
        + min(25, _num(p, "revenue_growth_pct"))
        + (25 if _flag(p, "has_unit_economics") else 0)
        + (20 if _flag(p, "has_projections") else 0)
    )


def _pitch(p: dict) -> int:
    return _clamp(
        (40 if _flag(p, "has_pitch_deck") else 0)
        + _num(p, "deck_completeness") * 0.30
        + (15 if _flag(p, "has_clear_problem") else 0)
        + (15 if _flag(p, "has_differentiation") else 0)
    )


def _legal(p: dict) -> int:
    return _clamp(
        (30 if _flag(p, "is_registered") else 0)
        + (20 if _flag(p, "dpiit_recognized") else 0)
        + (20 if _flag(p, "has_ip_filing") else 0)
        + (15 if _flag(p, "is_compliant") else 0)
        + (15 if _flag(p, "has_cap_table") else 0)
    )


_SCORERS = {
    "team": _team,
    "product": _product,
    "traction": _traction,
    "financial": _financial,
    "pitch": _pitch,
    "legal": _legal,
}


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


def score_readiness(profile: dict[str, Any]) -> ReadinessResult:
    dims = {name: scorer(profile) for name, scorer in _SCORERS.items()}
    overall = _clamp(sum(dims[d] * w for d, w in WEIGHTS.items()))
    return ReadinessResult(dimensions=dims, overall=overall, band=_band(overall))
