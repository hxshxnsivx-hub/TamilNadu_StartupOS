"""A roadmap that responds to the founder (rnd-elicitation.md §7).

Three deterministic stages replace the old constant list of nine milestones:

1. Applicability — each template's rule tree is evaluated against the
   founder's facts with the scheme engine's evaluator; templates for work the
   founder has already done (by stage) are left out.
2. Selection — CP-SAT picks 5–15 milestones (Req 1.3 AC1) with dependency
   closure, every core milestone kept and every phase present, maximising
   relevance. If the solver fails, the applicable core milestones are used.
3. Duration — effort × domain × complexity × experience ÷ team capacity
   (sublinear in team size), floored at a calendar minimum, with an
   optimistic–pessimistic band that widens as confidence in the answers falls
   (Req 1.3 AC6–AC7).

Ordering and the critical path then run through the existing, tested
topological_order and critical_path in swarms/roadmap/milestones.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.planner.packs import Template
from app.schemes.rules import Combinator, Rule, RuleGroup, evaluate
from app.swarms.roadmap.milestones import critical_path, topological_order
from app.swarms.roadmap.models import Milestone, Phase, Timeline

STAGES = ["idea", "poc", "prototype", "mvp", "revenue", "growth", "scale"]
PHASES = [p.value for p in Phase]
MIN_MILESTONES, MAX_MILESTONES = 5, 15
K_DOMAIN = {"food": 1.10, "health": 1.25, "electronics": 1.20, "manufacturing": 1.15}


@dataclass
class Planned:
    milestone: Milestone
    template: Template
    because: list[str]


def _because(node: Rule | RuleGroup, facts: dict) -> list[str]:
    """The labels of the conditions that made a template apply."""
    if isinstance(node, Rule):
        return [node.describe()] if node.label and evaluate(node, facts).ok else []
    if not node.rules:
        return []
    if node.combinator is Combinator.ANY:
        return [lbl for c in node.rules if evaluate(c, facts).ok for lbl in _because(c, facts)][:2]
    return [lbl for c in node.rules for lbl in _because(c, facts)]


def applicable(templates: list[Template], facts: dict) -> list[Template]:
    stage = STAGES.index(facts["stage"]) if facts.get("stage") in STAGES else 0
    keep = []
    for t in templates:
        if t.done_from_stage and stage >= STAGES.index(t.done_from_stage):
            continue
        if evaluate(t.applies, facts).ok:
            keep.append(t)
    ids = {t.id for t in keep}
    for t in keep:  # a dependency that does not apply (or is done) is dropped, not forced
        t.depends_on = [d for d in t.depends_on if d in ids]
    return keep


def select(templates: list[Template]) -> list[Template]:
    try:
        from ortools.sat.python import cp_model
    except ImportError:  # pragma: no cover - ortools is a declared dependency
        return [t for t in templates if t.core]
    m = cp_model.CpModel()
    x = {t.id: m.NewBoolVar(t.id) for t in templates}
    for t in templates:
        for d in t.depends_on:
            m.AddImplication(x[t.id], x[d])
        if t.core:
            m.Add(x[t.id] == 1)
    lo = min(MIN_MILESTONES, len(templates))
    m.Add(sum(x.values()) >= lo)
    m.Add(sum(x.values()) <= MAX_MILESTONES)
    for ph in PHASES:
        in_phase = [x[t.id] for t in templates if t.phase == ph]
        if in_phase:
            m.Add(sum(in_phase) >= 1)
    m.Maximize(sum(t.relevance * x[t.id] for t in templates))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 2.0
    solver.parameters.num_search_workers = 1  # deterministic; see elicitation/selector.py
    status = solver.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return [t for t in templates if t.core]
    return [t for t in templates if solver.Value(x[t.id])]


def k_experience(years: float | None) -> float:
    if years is None:
        return 1.0
    if years < 2:
        return 1.15
    if years < 6:
        return 1.0
    if years < 11:
        return 0.88
    return 0.80


def capacity(team_size: int | None) -> float:
    """Sublinear: three people do not finish in a third of the time."""
    return float(max(1, team_size or 1)) ** 0.7


def months(t: Template, facts: dict, confidence: float) -> Timeline:
    if t.calendar:  # an office or a lab sets the pace, not the team
        weeks = t.effort_weeks
    else:
        k_dom = K_DOMAIN.get(facts.get("sector"), 1.0)
        k_cplx = 1.0 + (0.25 if facts.get("product_form") in ("physical", "hybrid") else 0.0)
        weeks = t.effort_weeks * k_dom * k_cplx * k_experience(facts.get("founder_years"))
        weeks /= capacity(facts.get("team_size"))
    realistic = max(t.min_months, math.ceil(weeks / 4.33))
    sigma = 0.20 + 0.60 * (1.0 - max(0.0, min(1.0, confidence)))
    return Timeline(
        optimistic=max(1, math.floor(realistic * (1 - sigma * 0.5))),
        realistic=realistic,
        pessimistic=max(realistic + 1, math.ceil(realistic * (1 + sigma))),
    )


def build(templates: list[Template], facts: dict, context: dict, confidence: float) -> dict:
    chosen = select(applicable(templates, facts))
    ids = {t.id for t in chosen}
    planned = []
    for t in chosen:
        planned.append(
            Planned(
                milestone=Milestone(
                    id=t.id,
                    phase=Phase(t.phase),
                    title=t.title.format(**context),
                    deliverables=[
                        text.format(**context)
                        for text, cond in t.deliverables
                        if cond is None or evaluate(cond, facts).ok
                    ],
                    timeline=months(t, facts, confidence),
                    depends_on=[d for d in t.depends_on if d in ids],
                ),
                template=t,
                because=_because(t.applies, facts)
                + [lbl for _, cond in t.deliverables if cond for lbl in _because(cond, facts)],
            )
        )
    milestones = [p.milestone for p in planned]
    order = topological_order(milestones)
    cp = critical_path(milestones)
    for m in milestones:
        m.critical = m.id in cp
    by_id = {p.milestone.id: p for p in planned}
    # Shown by phase, and in dependency order within a phase.
    rank = {mid: i for i, mid in enumerate(order)}
    order = sorted(
        order, key=lambda mid: (PHASES.index(by_id[mid].milestone.phase.value), rank[mid])
    )
    # Months to finish = the critical path's realistic length.
    total = sum(by_id[i].milestone.timeline.realistic for i in cp)
    return {"ordered": [by_id[i] for i in order], "critical_path": cp, "months_realistic": total}
