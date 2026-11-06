"""Deterministic rule-tree evaluation (design E2 · the rules layer).

Scheme eligibility is a pure function of a fully-known profile — there is nothing
to *search*, so no solver is used here (the CP-SAT boundary is reserved for the
genuinely combinatorial matching problems). Every failed rule yields a
human-readable reason, which is how "a reason for every no" is delivered for free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.tri import Tri, Verdict, and_, not_, of, or_


class Op(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


class Combinator(str, Enum):
    ALL = "all"  # AND
    ANY = "any"  # OR
    NONE = "none"  # NOR


def _get(profile: dict[str, Any], dotted: str) -> Any:
    node: Any = profile
    for part in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _apply(op: Op, actual: Any, value: Any) -> bool:
    """Two-valued op on a *known* (non-None) actual; may raise TypeError, which
    the three-valued leaf turns into UNKNOWN."""
    if op is Op.IS_TRUE:
        return bool(actual)
    if op is Op.IS_FALSE:
        return not bool(actual)
    if op is Op.EQ:
        return actual == value
    if op is Op.NE:
        return actual != value
    if op is Op.GT:
        return actual > value
    if op is Op.GTE:
        return actual >= value
    if op is Op.LT:
        return actual < value
    if op is Op.LTE:
        return actual <= value
    if op is Op.IN:
        return actual in value
    if op is Op.NOT_IN:
        return actual not in value
    if op is Op.BETWEEN:
        return value[0] <= actual <= value[1]
    return False


def _apply_tri(op: Op, actual: Any, value: Any) -> Tri:
    """Missing data (None) and uncomparable types are UNKNOWN, not False — so a
    positive rule never fails on absent data and ``is_false`` no longer passes
    on a field the founder has not given (F-A4-001, F-B4-008)."""
    if actual is None:
        return Tri.UNKNOWN
    try:
        return of(_apply(op, actual, value))
    except TypeError:
        return Tri.UNKNOWN


@dataclass
class Rule:
    field: str
    op: Op
    value: Any = None
    label: str | None = None  # human-readable requirement, shown on failure

    def describe(self) -> str:
        if self.label:
            return self.label
        return f"{self.field} {self.op.value} {self.value}"


@dataclass
class RuleGroup:
    combinator: Combinator
    rules: list[Rule | RuleGroup] = field(default_factory=list)
    label: str | None = None


def evaluate(node: Rule | RuleGroup, profile: dict[str, Any]) -> Verdict:
    """Evaluate a rule tree to a three-valued :class:`Verdict`.

    A verdict is TRUE only when every leaf is provably true; FALSE when a leaf is
    provably violated (carrying its reason); UNKNOWN when the outcome rests on a
    missing fact (carrying the field paths we would need).
    """
    if isinstance(node, Rule):
        val = _apply_tri(node.op, _get(profile, node.field), node.value)
        if val is Tri.FALSE:
            return Verdict(val, reasons=[node.describe()])
        if val is Tri.UNKNOWN:
            return Verdict(val, missing=[node.field])
        return Verdict(Tri.TRUE)

    children = [evaluate(c, profile) for c in node.rules]
    values = [c.value for c in children]

    if node.combinator is Combinator.ALL:
        val = and_(values)
    elif node.combinator is Combinator.ANY:
        val = or_(values)
    else:  # NONE / NOR
        val = not_(or_(values))

    if val is Tri.TRUE:
        return Verdict(Tri.TRUE)

    missing = [m for c in children for m in c.missing]
    if val is Tri.UNKNOWN:
        return Verdict(Tri.UNKNOWN, missing=missing)

    # val is FALSE — give the specific violation(s)
    if node.combinator is Combinator.ALL:
        reasons = [r for c in children for r in c.reasons]
    elif node.combinator is Combinator.ANY:
        reasons = [node.label or "none of the alternative criteria were met"]
    else:
        reasons = [node.label or "an exclusion criterion was matched"]
    return Verdict(Tri.FALSE, reasons=reasons)
