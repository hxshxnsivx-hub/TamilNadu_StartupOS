"""Question selection and the stopping rule (Req 1.2 AC4).

Which single question to ask next, given partial information, is the
intellectual core of the elicitation loop. It is posed as a constrained
optimisation over a question *plan* and re-solved every turn, with a greedy
maximum-value fallback if the solver is unavailable.

Why not just sort by value? Because five things constrain the choice at once —
a burden budget that is tighter on the voice channel, an ask-once contract
against profile pre-fill, skip handling, required-before-enriching ordering,
and a ceiling on total questions. A sort key cannot express a budget.

The solver strictly generalises greedy: at plan horizon 1 with slack, both
return the same head question.

TWO FINDINGS FROM THE R&D THAT ARE ENCODED HERE AND MUST NOT BE "SIMPLIFIED":

1. `plan_size` is a VARIABLE, not a constant. Pinning it makes the model
   INFEASIBLE whenever the burden budget binds — a tight budget must be able
   to *shrink* the plan rather than fail.

2. `num_search_workers = 1`. It is ~30% faster at this model size, and
   google/or-tools#3842 reports 8 workers returning INFEASIBLE on a model that
   1 worker proves OPTIMAL. In a repo whose tests assert exact critical paths,
   that would surface as flaky tests that look like logic bugs.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.elicitation.session import ElicitationSession
from app.elicitation.slots import BY_KEY, REQUIRED_BY_MODE, Finger, Slot

# ---------------------------------------------------------------- constants

TAU_FILL = 0.60  # confidence at or above which a slot counts as known
TAU_GAIN = 900  # scaled x1000: below this, another question is not worth it
Q_MAX = 7  # ceiling on questions asked. A product decision — see §4.2
# of rnd-elicitation.md; marked UNVERIFIED and due A/B calibration.

SCALE = 1000

# Value-function weights. [UNVERIFIED] — plausible and internally consistent,
# but not calibrated against user data. Tuning these is a product exercise.
W_REQUIRED = 1.00
W_CLASSES = 0.35
W_CONSUMERS = 0.30
W_BURDEN = 0.25

# Asking costs more on voice than on a keyboard, so the budget is tighter.
BURDEN_BY_KIND = {"text": 3, "multi": 3, "enum": 1, "int": 1}


@dataclass(frozen=True)
class StopDecision:
    stop: bool
    reason: str
    unfilled: tuple[str, ...] = ()


@dataclass(frozen=True)
class Plan:
    head: str | None  # the ONE slot to ask about now
    plan: tuple[str, ...]  # the look-ahead, for UI progress hints
    status: str


# ---------------------------------------------------------------- value


def _decision_bits(slot: Slot) -> float:
    """Value of resolving this slot, in decision-equivalent classes.

    NOT log2(len(domain)). See slots.py — scoring over raw domain size makes
    `district` (38 values) outrank `problem`, and the conversation opens by
    asking someone their district instead of what they want to build.
    """
    n = max(1, slot.decision_classes)
    return n.bit_length() - 1 + (0.5 if n & (n - 1) else 0.0)


def question_value(key: str, session: ElicitationSession) -> int:
    """Scaled integer value of asking about `key` now. Higher is better."""
    slot = BY_KEY.get(key)
    if slot is None:
        return 0
    required = key in REQUIRED_BY_MODE[session.mode]
    v = (
        W_REQUIRED * (1.0 if required else 0.0)
        + W_CLASSES * _decision_bits(slot)
        + W_CONSUMERS * len(slot.consumers)
        - W_BURDEN * BURDEN_BY_KIND.get(slot.kind, 2)
    )
    # A slot already half-known is worth less to ask about than a blank one.
    existing = session.slots.get(key)
    if existing is not None:
        v *= max(0.0, 1.0 - existing.confidence)
    return int(round(v * SCALE))


def candidates(session: ElicitationSession) -> list[str]:
    """Askable slots: not confidently known, not skipped, not sensitive.

    Profile-sourced slots are excluded by the confidence filter — bootstrap
    seeds them at 0.95, so the selector never asks a founder for a district
    they already gave us. Re-asking is the single most corrosive thing this
    feature could do.
    """
    out = []
    for s in BY_KEY.values():
        if s.key in session.skipped:
            continue
        cur = session.slots.get(s.key)
        if cur is not None and cur.confidence >= TAU_FILL:
            continue
        out.append(s.key)
    return out


# ---------------------------------------------------------------- selection


def _greedy(session: ElicitationSession, pool: list[str], horizon: int) -> Plan:
    ranked = sorted(pool, key=lambda k: -question_value(k, session))
    return Plan(head=ranked[0] if ranked else None, plan=tuple(ranked[:horizon]), status="GREEDY")


def select_next(
    session: ElicitationSession,
    *,
    horizon: int = 3,
    burden_budget: int | None = None,
) -> Plan:
    """Choose the next question (and a short look-ahead plan)."""
    pool = candidates(session)
    if not pool:
        return Plan(head=None, plan=(), status="EMPTY")

    if burden_budget is None:
        burden_budget = 3 * horizon

    try:
        from ortools.sat.python import cp_model
    except ImportError:  # solver absent — degrade, never fail
        return _greedy(session, pool, horizon)

    model = cp_model.CpModel()
    x = {k: model.NewBoolVar(f"ask_{k}") for k in pool}

    # Plan size is a VARIABLE. Pinning it to `horizon` makes the model
    # INFEASIBLE the moment the burden budget binds; as a variable, a tight
    # budget shrinks the plan instead of failing.
    size = model.NewIntVar(1, min(horizon, len(pool)), "plan_size")
    model.Add(sum(x.values()) == size)

    model.Add(sum(BURDEN_BY_KIND.get(BY_KEY[k].kind, 2) * x[k] for k in pool) <= burden_budget)

    # Required work comes before enrichment: no ENRICHING slot may be selected
    # while any REQUIRED one is still available to ask.
    req_pool = [k for k in pool if k in REQUIRED_BY_MODE[session.mode]]
    enr_pool = [k for k in pool if k not in REQUIRED_BY_MODE[session.mode]]
    if req_pool:
        for k in enr_pool:
            model.Add(x[k] == 0)

    model.Maximize(sum(question_value(k, session) * x[k] for k in pool))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1  # see module docstring
    solver.parameters.max_time_in_seconds = 1.0
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return _greedy(session, pool, horizon)

    chosen = [k for k in pool if solver.Value(x[k])]
    chosen.sort(key=lambda k: -question_value(k, session))
    return Plan(
        head=chosen[0] if chosen else None,
        plan=tuple(chosen),
        status=solver.StatusName(status),
    )


# ---------------------------------------------------------------- stopping


def is_objective_clear(session: ElicitationSession) -> StopDecision:
    """Is the objective specified well enough to generate a roadmap?

    Three conjuncts, in evaluation order: required coverage, five-finger
    coverage, then diminishing returns.
    """
    unfilled = tuple(sorted(session.missing))
    fingers_ok = session.fingers >= _fingers_with_required(session)

    if unfilled or not fingers_ok:
        if session.turn_no >= Q_MAX:
            # Do NOT pretend this is clear. Proceed to confirmation with the
            # gaps named, and let the roadmap widen its pessimistic estimates.
            # Failing loudly-but-usefully beats silently guessing for a user
            # who is tired of questions.
            return StopDecision(True, "budget_exhausted", unfilled)
        return StopDecision(False, "required_unfilled", unfilled)

    plan = select_next(session)
    best = question_value(plan.head, session) if plan.head else 0
    if best >= TAU_GAIN and session.turn_no < Q_MAX:
        return StopDecision(False, "enrichment_available")
    return StopDecision(True, "clear")


def _fingers_with_required(session: ElicitationSession) -> set[Finger]:
    """Fingers that have at least one REQUIRED slot in the active mode.

    Checked explicitly rather than assumed from required-coverage: it is the
    client's stated contract, and it stays correct if someone later adds a
    REQUIRED slot to a finger that currently has none.
    """
    req = REQUIRED_BY_MODE[session.mode]
    return {BY_KEY[k].finger for k in req}


def next_question(session: ElicitationSession) -> tuple[str, str] | None:
    """(slot_key, question_text) for the next thing to ask, or None."""
    plan = select_next(session)
    if plan.head is None:
        return None
    slot = BY_KEY[plan.head]
    return plan.head, slot.question


__all__ = [
    "Plan",
    "StopDecision",
    "Q_MAX",
    "TAU_FILL",
    "TAU_GAIN",
    "candidates",
    "is_objective_clear",
    "next_question",
    "question_value",
    "select_next",
]
