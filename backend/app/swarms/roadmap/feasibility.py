"""Deterministic feasibility scoring (0–100) across four dimensions.

Concept completeness is the strongest signal (a half-described idea can't be
assessed well); market, technical and regulatory are heuristic priors adjusted by
domain cues. An LLM can refine these later; the shape stays the same.
"""

from __future__ import annotations

from app.swarms.roadmap.models import CONCEPT_ELEMENTS, Feasibility, StartupIdea

_WEIGHTS = {"completeness": 0.40, "market": 0.20, "technical": 0.20, "regulatory": 0.20}

# Domain cues → (technical difficulty penalty, regulatory penalty). Higher = harder.
_HARD_TECH = ("hardware", "deep tech", "biotech", "semiconductor", "robotics", "space")
_REGULATED = ("health", "fintech", "finance", "pharma", "drone", "defence", "food")


def score_feasibility(idea: StartupIdea) -> Feasibility:
    present = sum(1 for e in CONCEPT_ELEMENTS if getattr(idea, e))
    completeness = round(100 * present / len(CONCEPT_ELEMENTS))

    text = f"{idea.raw_text} {idea.domain or ''}".lower()
    technical = 60
    if any(k in text for k in _HARD_TECH):
        technical = 40  # harder to build, lower feasibility
    regulatory = 75
    if any(k in text for k in _REGULATED):
        regulatory = 50  # heavier compliance burden
    market = 65  # neutral prior without market data

    breakdown = {
        "completeness": completeness,
        "market": market,
        "technical": technical,
        "regulatory": regulatory,
    }
    score = round(sum(breakdown[k] * w for k, w in _WEIGHTS.items()))
    return Feasibility(score=score, breakdown=breakdown)
