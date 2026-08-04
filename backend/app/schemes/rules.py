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
    if op in (Op.IS_TRUE, Op.IS_FALSE):
        return bool(actual) is (op is Op.IS_TRUE)
    if actual is None:
        return False  # missing data can't satisfy a positive constraint
    try:
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
    except TypeError:
        return False
    return False


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


@dataclass
class EvalResult:
    ok: bool
    reasons: list[str]  # why it failed (empty when ok)


def evaluate(node: Rule | RuleGroup, profile: dict[str, Any]) -> EvalResult:
    if isinstance(node, Rule):
        ok = _apply(node.op, _get(profile, node.field), node.value)
        return EvalResult(ok, [] if ok else [node.describe()])

    child_results = [evaluate(c, profile) for c in node.rules]

    if node.combinator is Combinator.ALL:
        ok = all(r.ok for r in child_results)
        reasons = [rr for r in child_results for rr in r.reasons]
        return EvalResult(ok, [] if ok else reasons)

    if node.combinator is Combinator.ANY:
        ok = any(r.ok for r in child_results)
        reason = node.label or "none of the alternative criteria were met"
        return EvalResult(ok, [] if ok else [reason])

    # NONE / NOR — passes only if no child matched
    matched = any(r.ok for r in child_results)
    reason = node.label or "an exclusion criterion was matched"
    return EvalResult(not matched, [] if not matched else [reason])
