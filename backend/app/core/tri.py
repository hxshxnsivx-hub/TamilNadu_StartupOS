"""Kleene three-valued logic (arena theme T04).

Eligibility rules were two-valued: a missing founder fact evaluated to False, so
an early founder was told "not eligible" with reasons they had never failed, and
an ``is_false`` check even *passed* on absent data. Kleene logic adds a third
value, UNKNOWN, with the property that a result is only TRUE when it is provably
true and only FALSE when it is provably false; anything resting on a missing fact
is UNKNOWN and routed to "we need to know" rather than a false refusal.

    AND  → FALSE if any FALSE, else UNKNOWN if any UNKNOWN, else TRUE
    OR   → TRUE  if any TRUE,  else UNKNOWN if any UNKNOWN, else FALSE
    NOT  → swaps TRUE/FALSE, leaves UNKNOWN unchanged

This is the one evaluator every eligibility path shares (Schemes, recommend,
annotate, /talk); T29 and T24 reuse it too.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum


class Tri(Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


def of(value: bool) -> Tri:
    return Tri.TRUE if value else Tri.FALSE


def not_(a: Tri) -> Tri:
    if a is Tri.TRUE:
        return Tri.FALSE
    if a is Tri.FALSE:
        return Tri.TRUE
    return Tri.UNKNOWN


def and_(values: Iterable[Tri]) -> Tri:
    result = Tri.TRUE
    for v in values:
        if v is Tri.FALSE:
            return Tri.FALSE
        if v is Tri.UNKNOWN:
            result = Tri.UNKNOWN
    return result


def or_(values: Iterable[Tri]) -> Tri:
    result = Tri.FALSE
    for v in values:
        if v is Tri.TRUE:
            return Tri.TRUE
        if v is Tri.UNKNOWN:
            result = Tri.UNKNOWN
    return result


@dataclass
class Verdict:
    """A three-valued evaluation result: the value, the specific violations that
    make it FALSE, and the field paths left UNKNOWN (what we would need to know)."""

    value: Tri
    reasons: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True only when provably eligible (TRUE); UNKNOWN and FALSE are not ok."""
        return self.value is Tri.TRUE
