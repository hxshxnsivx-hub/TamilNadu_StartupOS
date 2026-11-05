"""Company stage and funding round, kept separate (arena flag F-A4-015).

``readiness`` scored stages ``idea..scaling``, ``investors`` mixed company stages
with funding rounds (``series_a``, ``growth``) in one list, and the elicitation
engine used ``idea..revenue``. A revenue-stage founder therefore matched nothing.
``Stage`` is the company's build stage; ``Round`` is the money round; the two are
mapped by ``ROUND_STAGES`` instead of being confused.
"""

from __future__ import annotations

import os
from enum import Enum

import structlog

log = structlog.get_logger(__name__)


class Stage(str, Enum):
    """Where the company actually is, in build order."""

    IDEA = "idea"
    POC = "poc"
    PROTOTYPE = "prototype"
    MVP = "mvp"
    REVENUE = "revenue"
    GROWTH = "growth"

    @property
    def rank(self) -> int:
        return _STAGE_ORDER.index(self)

    def __ge__(self, other: object) -> bool:  # readiness compares "at least mvp"
        if isinstance(other, Stage):
            return self.rank >= other.rank
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Stage):
            return self.rank > other.rank
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Stage):
            return self.rank <= other.rank
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Stage):
            return self.rank < other.rank
        return NotImplemented


_STAGE_ORDER = [Stage.IDEA, Stage.POC, Stage.PROTOTYPE, Stage.MVP, Stage.REVENUE, Stage.GROWTH]


class Round(str, Enum):
    """The funding round a founder is raising."""

    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    GROWTH = "growth"


# Every legacy spelling of a company stage seen in the repo, mapped onto a Stage.
LEGACY_STAGE: dict[str, Stage] = {
    "idea": Stage.IDEA,
    "ideation": Stage.IDEA,
    "concept": Stage.IDEA,
    "poc": Stage.POC,
    "proof_of_concept": Stage.POC,
    "validated": Stage.POC,
    "prototype": Stage.PROTOTYPE,
    "sample": Stage.PROTOTYPE,
    "mvp": Stage.MVP,
    "pilot": Stage.MVP,
    "beta": Stage.MVP,
    "revenue": Stage.REVENUE,
    "launched": Stage.REVENUE,  # readiness spelling
    "selling": Stage.REVENUE,
    "paying_customers": Stage.REVENUE,
    "growth": Stage.GROWTH,
    "scaling": Stage.GROWTH,  # readiness spelling
    "scale": Stage.GROWTH,  # investors spelling
    "expanding": Stage.GROWTH,
}

# Which company stages each funding round is typically raised at (investor matching).
ROUND_STAGES: dict[Round, frozenset[Stage]] = {
    Round.PRE_SEED: frozenset({Stage.IDEA, Stage.POC, Stage.PROTOTYPE}),
    Round.SEED: frozenset({Stage.PROTOTYPE, Stage.MVP}),
    Round.SERIES_A: frozenset({Stage.MVP, Stage.REVENUE}),
    Round.SERIES_B: frozenset({Stage.REVENUE, Stage.GROWTH}),
    Round.SERIES_C: frozenset({Stage.REVENUE, Stage.GROWTH}),
    Round.GROWTH: frozenset({Stage.REVENUE, Stage.GROWTH}),
}

_LEGACY_ROUND: dict[str, Round] = {
    "pre_seed": Round.PRE_SEED,
    "preseed": Round.PRE_SEED,
    "angel": Round.PRE_SEED,
    "seed": Round.SEED,
    "series_a": Round.SERIES_A,
    "series_b": Round.SERIES_B,
    "series_c": Round.SERIES_C,
    "growth": Round.GROWTH,
    "scale": Round.GROWTH,
}


def _strict() -> bool:
    # Raise under tests so a missing mapping fails CI; log-and-skip in production.
    return "PYTEST_CURRENT_TEST" in os.environ


def to_stage(value: object) -> Stage | None:
    """Normalise any legacy stage spelling to a :class:`Stage`."""
    if isinstance(value, Stage):
        return value
    if value is None:
        return None
    key = str(value).strip().lower()
    if key in LEGACY_STAGE:
        return LEGACY_STAGE[key]
    if _strict():
        raise ValueError(f"unknown stage {value!r}; add it to LEGACY_STAGE")
    log.warning("vocab.unknown_stage", value=str(value))
    return None


def to_round(value: object) -> Round | None:
    """Normalise any legacy round spelling to a :class:`Round`."""
    if isinstance(value, Round):
        return value
    if value is None:
        return None
    key = str(value).strip().lower()
    if key in _LEGACY_ROUND:
        return _LEGACY_ROUND[key]
    if _strict():
        raise ValueError(f"unknown round {value!r}; add it to _LEGACY_ROUND")
    log.warning("vocab.unknown_round", value=str(value))
    return None
