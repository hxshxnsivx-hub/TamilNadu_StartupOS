"""One stage vocabulary for every module that reads a founder's stage (task 1.1.8.1).

Before this module the words drifted: the funding screen offered revenue and
growth, readiness scored 'launched' and 'scaling' instead (so a selling founder
scored zero), and the investor matcher knew neither, so it matched them to no
one. Each module now maps from `Stage`, and tests/unit/test_stages.py fails when
any module meets a stage it has no mapping for.

Two vocabularies, kept apart on purpose:

  * `Stage` is where the founder is: what exists today.
  * a *round* is what investors and incubators publish (TN Startup Map words:
    pre_seed, seed, early, growth...). Those names keep their published meaning;
    `ROUND_FOR_STAGE` says which round a founder at each stage raises, and
    `ROUND_FITS` which published rounds can fund it.
"""

from __future__ import annotations

from enum import Enum


class Stage(str, Enum):
    IDEA = "idea"
    POC = "poc"
    PROTOTYPE = "prototype"
    MVP = "mvp"
    REVENUE = "revenue"
    GROWTH = "growth"
    SCALE = "scale"


ORDER: tuple[Stage, ...] = tuple(Stage)

# Words other modules used before this vocabulary existed. Explicit, so no
# module invents its own synonym again.
ALIASES: dict[str, Stage] = {
    "launched": Stage.MVP,  # the elicitation cue reads "launched" as a first version
    "scaling": Stage.GROWTH,
}

# The round a founder at each stage raises. Matches the incubator labels
# (pre_seed = idea and prototype, seed = MVP, early = early revenue).
ROUND_FOR_STAGE: dict[Stage, str] = {
    Stage.IDEA: "idea",
    Stage.POC: "pre_seed",
    Stage.PROTOTYPE: "pre_seed",
    Stage.MVP: "seed",
    Stage.REVENUE: "pre_series_a",
    Stage.GROWTH: "series_a",
    Stage.SCALE: "growth",
}

# Published investor rounds that can fund a founder raising each round.
ROUND_FITS: dict[str, set[str]] = {
    "idea": {"pre_seed", "seed"},
    "pre_seed": {"pre_seed", "seed"},
    "seed": {"pre_seed", "seed", "early"},
    "pre_series_a": {"seed", "pre_series_a", "early"},
    "series_a": {"series_a", "early"},
    "growth": {"growth"},
}


def parse_stage(value: object) -> Stage | None:
    """The canonical stage for `value`, or None when it is not a stage."""
    if isinstance(value, Stage):
        return value
    if not isinstance(value, str):
        return None
    word = value.strip().lower()
    try:
        return Stage(word)
    except ValueError:
        return ALIASES.get(word)


def stages_funded_by(rounds: list[str]) -> list[str]:
    """Founder stages (in order) that investors publishing `rounds` can fund."""
    published = set(rounds)
    return [s.value for s in ORDER if ROUND_FITS[ROUND_FOR_STAGE[s]] & published]
