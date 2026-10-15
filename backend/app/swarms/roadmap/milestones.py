"""Milestone generation, topological ordering, and critical-path detection.

The dependency graph is a DAG. Ordering uses Kahn's algorithm; the critical path
is the longest path by realistic duration (DAG longest-path via DP over the
topological order). Both are deterministic and fully unit-tested.
"""

from __future__ import annotations

from app.swarms.roadmap.models import Milestone, Phase, StartupIdea, Timeline


def _t(o: int, r: int, p: int) -> Timeline:
    return Timeline(optimistic=o, realistic=r, pessimistic=p)


def generate_milestones(idea: StartupIdea) -> list[Milestone]:
    """A staged backbone across all six phases with realistic dependencies.

    Deterministic template (5–15 milestones per Req 1.3); an LLM can later enrich
    titles/deliverables per domain, but the phase structure and dependencies —
    what the critical path is computed from — stay stable.
    """
    dom = idea.domain or "your product"
    m = [
        Milestone(
            "m1",
            Phase.IDEATION,
            "Define problem & solution",
            ["Problem statement", "Solution concept"],
            _t(1, 1, 2),
        ),
        Milestone(
            "m2",
            Phase.VALIDATION,
            "Customer discovery",
            ["20 customer interviews", "Validated pain points"],
            _t(1, 2, 3),
            ["m1"],
        ),
        Milestone(
            "m3",
            Phase.VALIDATION,
            "Market & feasibility research",
            ["TAM/SAM/SOM", "Competitor map"],
            _t(1, 1, 2),
            ["m1"],
        ),
        Milestone(
            "m4",
            Phase.MVP,
            f"Build MVP for {dom}",
            ["Working MVP", "Test users"],
            _t(2, 4, 7),
            ["m2", "m3"],
        ),
        Milestone(
            "m5",
            Phase.MVP,
            "Register legal entity",
            ["Incorporation", "DPIIT recognition"],
            _t(1, 2, 3),
            ["m1"],
        ),
        Milestone(
            "m6",
            Phase.LAUNCH,
            "Pilot launch",
            ["Live pilot", "First feedback"],
            _t(1, 2, 4),
            ["m4", "m5"],
        ),
        Milestone(
            "m7",
            Phase.GROWTH,
            "Acquire first customers",
            ["10 paying customers", "Traction metrics"],
            _t(2, 3, 5),
            ["m6"],
        ),
        Milestone(
            "m8",
            Phase.GROWTH,
            "Raise seed funding",
            ["Pitch deck", "Investor conversations"],
            _t(2, 4, 8),
            ["m6"],
        ),
        Milestone(
            "m9",
            Phase.SCALE,
            "Scale operations",
            ["Hire team", "Expand market"],
            _t(3, 6, 12),
            ["m7", "m8"],
        ),
    ]
    return m


def topological_order(milestones: list[Milestone]) -> list[str]:
    """Kahn's algorithm. Raises ValueError on a cycle or dangling dependency."""
    ids = {m.id for m in milestones}
    for m in milestones:
        for d in m.depends_on:
            if d not in ids:
                raise ValueError(f"milestone {m.id} depends on unknown {d}")

    indeg = {m.id: len(m.depends_on) for m in milestones}
    children: dict[str, list[str]] = {m.id: [] for m in milestones}
    for m in milestones:
        for d in m.depends_on:
            children[d].append(m.id)

    queue = [mid for mid, deg in indeg.items() if deg == 0]
    order: list[str] = []
    while queue:
        queue.sort()  # deterministic tie-break
        nid = queue.pop(0)
        order.append(nid)
        for c in children[nid]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)

    if len(order) != len(milestones):
        raise ValueError("dependency cycle detected")
    return order


def critical_path(milestones: list[Milestone]) -> list[str]:
    """Longest path by realistic duration (DAG longest-path DP)."""
    by_id = {m.id: m for m in milestones}
    order = topological_order(milestones)
    dist: dict[str, int] = {}
    prev: dict[str, str | None] = {}

    for nid in order:
        m = by_id[nid]
        best_pred, best_cost = None, 0
        for d in m.depends_on:
            if dist[d] > best_cost:
                best_cost, best_pred = dist[d], d
        dist[nid] = best_cost + m.timeline.realistic
        prev[nid] = best_pred

    end = max(dist, key=lambda k: dist[k])
    path: list[str] = []
    node: str | None = end
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()
    return path
