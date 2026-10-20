"""Question selection and the stopping rule (Req 1.2 AC4).

Which single question to ask next, given partial information, is the
intellectual core of the elicitation loop. Five things constrain the choice at
once: a burden budget that is tighter on the voice channel, an ask-once
contract against profile pre-fill, skip handling, a what-before-anything
order with required-before-enriching after it, and a ceiling on questions.

HOW IT CHOOSES (R119)
---------------------
Greedy by value over a filtered pool: first the finger gate (nothing but the
WHAT finger until the idea is known), then the required tier (required slots,
and the slots of a contract finger still open, before any enrichment). That is
the whole rule at default settings: the burden budget (3 per plan slot) cannot
bind at horizon 3, and over every subset of filled required slots the CP-SAT
plan's head equals greedy's, at about 700x the cost and two solves per turn.

The CP-SAT model is kept for the case it was built for, a burden budget that
binds (a tighter voice budget): `select_next` runs it only when the greedy
plan's burden exceeds the budget. Two findings from the R&D are encoded in it
and must not be "simplified":

1. `plan_size` is a VARIABLE, not a constant. Pinning it makes the model
   INFEASIBLE whenever the burden budget binds: a tight budget must be able
   to *shrink* the plan rather than fail.

2. `num_search_workers = 1`. It is ~30% faster at this model size, and
   google/or-tools#3842 reports 8 workers returning INFEASIBLE on a model that
   1 worker proves OPTIMAL. In a repo whose tests assert exact critical paths,
   that would surface as flaky tests that look like logic bugs.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.elicitation.session import ElicitationSession
from app.elicitation.slots import (
    ANCHOR,
    ANY_OF,
    ASKABLE_BY_MODE,
    BY_KEY,
    REQUIRED_BY_MODE,
    TAU_CONFIRM,
    TAU_FILL,
    Finger,
)

# ---------------------------------------------------------------- constants

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


def _decision_bits(slot) -> float:
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
    """Askable slots: in the unknown band (below TAU_CONFIRM) and not skipped.

    A confirm-band value is not asked but said back as an assumption (R157).
    Profile-sourced slots are excluded by the same rule: bootstrap seeds them
    at 0.95, so the selector never asks a founder for a district they already
    gave us. Re-asking is the single most corrosive thing this feature could
    do. A disputed slot sits below the band (R053), so it is asked. A mode
    that asks only some slots (slots.ASKABLE_BY_MODE) never offers the rest.
    """
    allowed = ASKABLE_BY_MODE.get(session.mode)
    out = []
    for s in BY_KEY.values():
        if s.key in session.skipped or (allowed is not None and s.key not in allowed):
            continue
        cur = session.slots.get(s.key)
        if cur is not None and cur.confidence >= TAU_CONFIRM:
            continue
        out.append(s.key)
    return out


def _idea_known(session: ElicitationSession) -> bool:
    """Is the what known? The mode's required free-text WHAT slots (problem,
    solution) when it has any, else any of its required WHAT slots."""
    what = [k for k in REQUIRED_BY_MODE[session.mode] if BY_KEY[k].finger is Finger.WHAT]
    idea = [k for k in what if BY_KEY[k].kind == "text"] or what
    return not idea or any(k in session.filled for k in idea)


def askable(session: ElicitationSession) -> list[str]:
    """Candidates behind the finger gate (task 1.1.3.1): until the idea is
    known only WHAT questions are asked, so capital is never asked before what
    it is for. A mode with its own anchor (slots.ANCHOR, R089) asks that first
    instead: the experience conversation starts from what the founder can do.
    When nothing gated is left to ask, the gate opens."""
    pool = candidates(session)
    anchor = ANCHOR.get(session.mode)
    if anchor is not None:
        if not anchor & session.filled:
            first = [k for k in pool if k in anchor]
            if first:
                return first
        return pool
    if not _idea_known(session):
        what = [k for k in pool if BY_KEY[k].finger is Finger.WHAT]
        if what:
            return what
    return pool


def needed(session: ElicitationSession) -> set[str]:
    """Slots that come before any enrichment: the missing required ones, and
    the slots of a contract finger still open (R113)."""
    keys = set(session.missing)
    for finger in session.uncovered:
        keys |= set(ANY_OF.get(finger, ()))
    return keys


def _tier(session: ElicitationSession, pool: list[str]) -> list[str]:
    """Required work comes before enrichment: no other slot is planned while a
    needed one is still askable."""
    first = needed(session)
    return [k for k in pool if k in first] or pool


# ---------------------------------------------------------------- selection


def _greedy(session: ElicitationSession, pool: list[str], horizon: int) -> Plan:
    ranked = sorted(_tier(session, pool), key=lambda k: -question_value(k, session))
    return Plan(head=ranked[0] if ranked else None, plan=tuple(ranked[:horizon]), status="GREEDY")


def _burden(keys) -> int:
    return sum(BURDEN_BY_KIND.get(BY_KEY[k].kind, 2) for k in keys)


def select_next(
    session: ElicitationSession,
    *,
    horizon: int = 3,
    burden_budget: int | None = None,
) -> Plan:
    """Choose the next question (and a short look-ahead plan): greedy, or the
    solver when a burden budget binds."""
    pool = askable(session)
    if not pool:
        return Plan(head=None, plan=(), status="EMPTY")
    if burden_budget is None:
        burden_budget = 3 * horizon
    plan = _greedy(session, pool, horizon)
    if _burden(plan.plan) <= burden_budget:
        return plan
    return _solve(session, pool, horizon=horizon, burden_budget=burden_budget)


def _solve(
    session: ElicitationSession, pool: list[str], *, horizon: int, burden_budget: int
) -> Plan:
    """The plan as a CP-SAT model: most value within the burden budget."""
    if not pool:
        return Plan(head=None, plan=(), status="EMPTY")
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

    # Required work comes before enrichment, as in `_tier`.
    tier = set(_tier(session, pool))
    for k in pool:
        if k not in tier:
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


def question_budget(session: ElicitationSession) -> int:
    """Questions allowed before the restatement: Q_MAX plus one given back per
    correction. Counted in questions, not turns (R009)."""
    return Q_MAX + session.refunds


def is_objective_clear(session: ElicitationSession) -> StopDecision:
    """Is the objective specified well enough to generate a roadmap?

    Three conjuncts, in evaluation order: required coverage, five-finger
    coverage (every finger with a required slot, and WHY by any of its slots),
    then diminishing returns.
    """
    unfilled = tuple(sorted(session.missing))
    uncovered = session.uncovered

    if unfilled or uncovered:
        if session.questions_asked >= question_budget(session):
            # Do NOT pretend this is clear. Proceed to confirmation with the
            # gaps named, and let the roadmap widen its pessimistic estimates.
            # Failing loudly-but-usefully beats silently guessing for a user
            # who is tired of questions.
            return StopDecision(True, "budget_exhausted", unfilled)
        if unfilled:
            return StopDecision(False, "required_unfilled", unfilled)
        if askable(session):
            return StopDecision(False, "finger_uncovered")

    # Enrichment only before the first restatement: a question given back for a
    # correction is for what the correction opened, not for new topics.
    if session.objective is not None:
        return StopDecision(True, "clear")
    plan = select_next(session)
    best = question_value(plan.head, session) if plan.head else 0
    if best >= TAU_GAIN and session.questions_asked < question_budget(session):
        return StopDecision(False, "enrichment_available")
    return StopDecision(True, "clear")


def next_question(session: ElicitationSession) -> tuple[str, str] | None:
    """(slot_key, question_text) for the next thing to ask, or None."""
    plan = select_next(session)
    if plan.head is None:
        return None
    slot = BY_KEY[plan.head]
    return plan.head, slot.question_for(session.mode)


__all__ = [
    "Plan",
    "StopDecision",
    "Q_MAX",
    "TAU_FILL",
    "TAU_GAIN",
    "askable",
    "candidates",
    "is_objective_clear",
    "needed",
    "next_question",
    "question_budget",
    "question_value",
    "select_next",
]
