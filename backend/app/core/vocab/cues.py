"""One word-boundary cue matcher, safe for Tamil and Devanagari (arena flag F-B4-003).

Cue matching was a plain substring test, so ``"app"`` matched inside
``"Tiruchirappalli"`` and ``"apparel"`` and tagged the idea as software. A plain
``\\b`` boundary also mishandles Indic text. ``boundary_hits`` matches a cue only
when it is delimited on both sides by a non-letter, where "letter" includes Latin,
Tamil (U+0B80–U+0BFF) and Devanagari (U+0900–U+097F), so a Latin cue never matches
inside a longer Latin word nor bleeds into surrounding Indic text.
"""

from __future__ import annotations

import re
from collections.abc import Hashable, Mapping, Sequence

# A "letter" for boundary purposes: ASCII word chars plus Tamil and Devanagari.
_LETTER = r"0-9A-Za-z_஀-௿ऀ-ॿ"
_NOT_LETTER = rf"[^{_LETTER}]"


# An English inflection may follow the cue and still count as the same word, so
# "patient" matches "patients" and "loan" matches "loaning" — but "app" still does
# not match "apparel" ("arel" is not an inflection) or "Tiruchirappalli" (no
# leading boundary).
_INFLECTION = r"(?:s|es|ing|ed)?"


def _pattern(cue: str) -> re.Pattern[str]:
    body = re.escape(cue.strip())
    return re.compile(rf"(?<![{_LETTER}]){body}{_INFLECTION}(?![{_LETTER}])", re.IGNORECASE)


def boundary_hits(text: str, cue: str) -> bool:
    """True if ``cue`` appears in ``text`` on word boundaries (Indic-safe)."""
    if not text or not cue.strip():
        return False
    return _pattern(cue) is not None and _pattern(cue).search(text) is not None


class Cues:
    """Compile a ``{value: (cue, ...)}`` table and return every value that hits.

    Unlike the old ``_first_cue`` (first match only), ``hits`` returns all matching
    values, so "a loan app for dairy farmers" can be both fintech and agritech.
    """

    def __init__(self, table: Mapping[Hashable, Sequence[str]]) -> None:
        self._compiled: list[tuple[Hashable, list[re.Pattern[str]]]] = [
            (value, [_pattern(c) for c in cues]) for value, cues in table.items()
        ]

    def hits(self, text: str) -> list[Hashable]:
        if not text:
            return []
        out: list[Hashable] = []
        for value, patterns in self._compiled:
            if any(p.search(text) for p in patterns):
                out.append(value)
        return out

    def first(self, text: str) -> Hashable | None:
        found = self.hits(text)
        return found[0] if found else None
