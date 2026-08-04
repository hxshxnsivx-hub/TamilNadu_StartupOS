"""Gap analysis (Req 4.2) — turn weak dimensions into a ranked action plan.

Dimensions scoring below the threshold become gap areas; each yields concrete
recommendations with an impact estimate (points) and effort (weeks), sorted by
impact-to-effort so the highest-leverage action is first.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.funding.readiness import ReadinessResult

GAP_THRESHOLD = 60

# dimension → [(action, impact_points, effort_weeks)]
_PLAYBOOK: dict[str, list[tuple[str, int, int]]] = {
    "team": [
        ("Add a co-founder with complementary skills", 8, 6),
        ("Recruit 2–3 domain advisors", 5, 3),
        ("Hire for the key missing role", 6, 5),
    ],
    "product": [
        ("Ship an MVP with the core feature set", 9, 6),
        ("File a provisional patent / register IP", 6, 4),
        ("Document the technical architecture", 4, 2),
    ],
    "traction": [
        ("Run a paid pilot with 3–5 customers", 9, 5),
        ("Instrument and improve 30-day retention", 6, 4),
        ("Sign 2 partnership LOIs", 5, 3),
    ],
    "financial": [
        ("Build a 12-month financial model with unit economics", 7, 3),
        ("Extend runway via cost optimisation", 6, 4),
        ("Establish clear pricing and margins", 5, 3),
    ],
    "pitch": [
        ("Build a complete 10-slide pitch deck", 6, 2),
        ("Sharpen the problem–solution narrative", 4, 1),
        ("Add competitive-differentiation slide", 3, 1),
    ],
    "legal": [
        ("Register the entity (Pvt Ltd / LLP)", 8, 4),
        ("Apply for DPIIT recognition", 5, 2),
        ("Organise the cap table", 4, 1),
    ],
}


@dataclass
class Recommendation:
    dimension: str
    action: str
    impact_points: int
    effort_weeks: int

    @property
    def impact_label(self) -> str:
        return "High" if self.impact_points >= 8 else "Medium" if self.impact_points >= 4 else "Low"

    @property
    def ratio(self) -> float:
        return self.impact_points / max(1, self.effort_weeks)


def analyze_gaps(readiness: ReadinessResult) -> list[Recommendation]:
    recs: list[Recommendation] = []
    for dim, score in readiness.dimensions.items():
        if score < GAP_THRESHOLD:
            for action, impact, effort in _PLAYBOOK.get(dim, []):
                recs.append(Recommendation(dim, action, impact, effort))
    recs.sort(key=lambda r: r.ratio, reverse=True)
    return recs
