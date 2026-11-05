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


# A cue preceded by one of these is the founder saying they are NOT there yet, so
# "no customers yet" and "we don't have a prototype" must not emit the value
# (arena flag F-A1-004). The trigger is looked for in the short run of characters
# just before the cue; Tamil negators (illai / illa / alla) are included.
_NEGATION = re.compile(
    r"(?<![" + _LETTER + r"])(?:no|not|n['’]?t|without|never|none|zero|"
    r"haven['’]?t|hasn['’]?t|hadn['’]?t|don['’]?t|doesn['’]?t|didn['’]?t|"
    r"isn['’]?t|aren['’]?t|wasn['’]?t|weren['’]?t|yet to|about to|hoping to|"
    r"planning to|illai|illa|alla)(?![" + _LETTER + r"])",
    re.IGNORECASE,
)
_NEG_WINDOW = 28  # characters before the cue to scan for a negation trigger


def negated(text: str, start: int) -> bool:
    """Is the cue at index ``start`` preceded by a negation trigger (same string)?"""
    return _NEGATION.search(text[max(0, start - _NEG_WINDOW) : start]) is not None


def unnegated_hit(text: str, cue: str) -> bool:
    """A boundary hit for ``cue`` that is *not* preceded by a negation trigger."""
    if not text or not cue.strip():
        return False
    m = _pattern(cue).search(text)
    return m is not None and not negated(text, m.start())


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
