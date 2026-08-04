"""Milestone scheme annotation (Task 2.5) — schemes onto the roadmap.

Maps each roadmap phase to the scheme stages that apply there, then places each
eligible scheme once, on the earliest milestone it fits (ranked, capped). This is
the cross-pillar payoff: the roadmap tells a founder *when* to apply for *which*
money (SISFS at MVP, NEEDS at setup, TANSEED at prototype…).
"""

from __future__ import annotations

from app.schemes.models import Scheme
from app.schemes.swarm import SchemeSwarm
from app.swarms.roadmap.models import Roadmap

# roadmap phase → scheme target stages that belong at that phase
PHASE_STAGES: dict[str, set[str]] = {
    "Ideation": {"idea"},
    "Validation": {"idea", "poc", "prototype"},
    "MVP": {"mvp"},
    "Launch": {"mvp", "revenue"},
    "Growth": {"revenue", "growth"},
    "Scale": {"growth", "scale"},
}

_swarm = SchemeSwarm()


def annotate_roadmap(profile: dict, roadmap: Roadmap, cap: int = 4) -> dict[str, list[Scheme]]:
    """Return {milestone_id: [schemes]} — each eligible scheme placed once."""
    ranked = _swarm.recommend(profile).ranked_eligible  # already sorted by score
    placed: set[str] = set()
    out: dict[str, list[Scheme]] = {m.id: [] for m in roadmap.milestones}

    for m in roadmap.milestones:
        stages = PHASE_STAGES.get(m.phase.value, set())
        if not stages:
            continue
        for r in ranked:
            if r.scheme.id in placed:
                continue
            if set(r.scheme.target_stages) & stages:
                out[m.id].append(r.scheme)
                placed.add(r.scheme.id)
                if len(out[m.id]) >= cap:
                    break
    return out
