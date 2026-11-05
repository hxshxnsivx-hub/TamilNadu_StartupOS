"""Canonical vocabulary for stage, funding round and sector (arena theme T01).

Before this package, stage/sector/round words were re-spelled as string literals in
each module (elicitation, planner, readiness, investors, scan, council, b2b), each
with its own substring cues. Values from one vocabulary silently failed to match
another (a revenue founder scored 0 against investors; "app" inside "Tiruchirappalli"
was read as software). This package owns the meaning once:

* ``Stage`` / ``Round`` — the company stage and the funding round, kept separate,
  with ``LEGACY_STAGE`` and ``ROUND_STAGES`` mapping the old spellings.
* ``Sector`` — the 20 ecosystem ids used as the join key, with ``CATEGORY_OF`` for
  display, ``SPOKEN_CHOICES`` for the 12 founder-facing options and
  ``ELICITATION_TO_SECTOR`` mapping the old 12-value enum onto the 20.
* ``Cues`` — one word-boundary cue matcher that is safe for Tamil and Devanagari
  text (plain ``\\b`` splits Tamil words and misfired).

Converters (``to_stage``, ``to_sector``, ``to_round``) raise ``ValueError`` on an
unknown value under tests and return ``None`` with a log event in production, so a
gap in a mapping table is caught in CI, never silently mislabelled for a founder.
"""

from app.core.vocab.cues import Cues, boundary_hits, negated, unnegated_hit
from app.core.vocab.sector import (
    CATEGORY_OF,
    ELICITATION_TO_SECTOR,
    SPOKEN_CHOICES,
    Sector,
    to_sector,
)
from app.core.vocab.stage import (
    LEGACY_STAGE,
    ROUND_STAGES,
    Round,
    Stage,
    to_round,
    to_stage,
)

__all__ = [
    "Stage",
    "Round",
    "LEGACY_STAGE",
    "ROUND_STAGES",
    "to_stage",
    "to_round",
    "Sector",
    "CATEGORY_OF",
    "SPOKEN_CHOICES",
    "ELICITATION_TO_SECTOR",
    "to_sector",
    "Cues",
    "boundary_hits",
    "negated",
    "unnegated_hit",
]
