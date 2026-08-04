"""Scheme ranking — relevance + approval-likelihood (Task 2.4 · design E6, P-24).

Runs only on the *eligible* set (soundness is already guaranteed). Relevance
answers "which should I do first" from stage/funding fit; likelihood answers
"where is my approval chance highest" from how well the founder matches a scheme's
preference axes (women / SC-ST / first-graduate / rural). Deterministic, no LLM;
positive plain-language reasons explain the ranking.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemes.models import Scheme

_AXIS_LABEL = {
    "women": "favours women-led ventures",
    "sc_st": "favours SC/ST founders",
    "first_graduate": "favours first-generation entrepreneurs",
    "rural": "favours rural entrepreneurs",
}


def _founder_axes(profile: dict) -> set[str]:
    f = profile.get("founder") or {}
    axes: set[str] = set()
    if f.get("gender") == "female":
        axes.add("women")
    if f.get("caste_category") in ("sc", "st"):
        axes.add("sc_st")
    if f.get("first_graduate"):
        axes.add("first_graduate")
    if f.get("rural"):
        axes.add("rural")
    return axes


@dataclass
class RankedScheme:
    scheme: Scheme
    relevance: int  # 0–100
    likelihood: int  # 0–100
    score: float  # composite sort key
    why: list[str] = field(default_factory=list)


def _stage_fit(scheme: Scheme, profile: dict) -> int:
    stage = (profile.get("startup") or {}).get("stage")
    if not scheme.target_stages or stage is None:
        return 60
    return 100 if stage in scheme.target_stages else 40


def _funding_fit(scheme: Scheme, funding_need: int | None) -> int:
    if funding_need is None:
        return 60
    if scheme.min_funding <= funding_need <= scheme.max_funding:
        return 100
    # scaled by how far outside the band the need falls
    nearest = scheme.min_funding if funding_need < scheme.min_funding else scheme.max_funding
    if nearest == 0:
        return 50
    diff = abs(funding_need - nearest) / max(nearest, 1)
    return max(20, round(100 - min(diff, 1.0) * 80))


def _likelihood(scheme: Scheme, founder_axes: set[str]) -> tuple[int, list[str]]:
    if not scheme.preference_axes:
        return 60, []  # open to all — neutral
    matched = [a for a in scheme.preference_axes if a in founder_axes]
    score = min(100, 50 + 15 * len(matched))
    reasons = [_AXIS_LABEL[a] for a in matched]
    return score, reasons


def rank_schemes(
    profile: dict, schemes: list[Scheme], funding_need: int | None = None
) -> list[RankedScheme]:
    founder_axes = _founder_axes(profile)
    stage = (profile.get("startup") or {}).get("stage")
    ranked: list[RankedScheme] = []

    for s in schemes:
        stage_fit = _stage_fit(s, profile)
        funding_fit = _funding_fit(s, funding_need)
        relevance = round(0.6 * stage_fit + 0.4 * funding_fit)
        likelihood, axis_reasons = _likelihood(s, founder_axes)

        why: list[str] = list(axis_reasons)
        if stage and stage in s.target_stages:
            why.append(f"matches your {stage} stage")
        if s.type.value == "grant":
            why.append("non-dilutive grant")
        if funding_need is not None and s.min_funding <= funding_need <= s.max_funding:
            why.append("fits your funding need")

        composite = 0.5 * likelihood + 0.5 * relevance
        ranked.append(RankedScheme(s, relevance, likelihood, composite, why))

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked
