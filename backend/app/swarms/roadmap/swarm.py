"""Roadmap Swarm supervisor — orchestrates extraction → feasibility → milestones."""

from __future__ import annotations

from app.swarms.roadmap.feasibility import score_feasibility
from app.swarms.roadmap.idea import extract_idea
from app.swarms.roadmap.milestones import critical_path, generate_milestones
from app.swarms.roadmap.models import Roadmap


class RoadmapSwarm:
    """Turns a founder's free-text idea into a structured, sequenced roadmap."""

    def generate(self, text: str) -> Roadmap:
        idea = extract_idea(text)
        feasibility = score_feasibility(idea)
        milestones = generate_milestones(idea)

        cp = critical_path(milestones)
        cp_set = set(cp)
        for m in milestones:
            m.critical = m.id in cp_set

        clarifications = [
            f"Tell me more about the {e.replace('_', ' ')}." for e in idea.missing_elements()
        ]
        return Roadmap(
            idea=idea,
            feasibility=feasibility,
            milestones=milestones,
            critical_path=cp,
            clarifications=clarifications,
        )
