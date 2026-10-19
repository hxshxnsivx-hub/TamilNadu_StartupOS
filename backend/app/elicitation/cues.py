"""Whole-word keyword cues (task 1.1.8.2, arena R027).

The extractor used to test cues as bare substrings, so 'app' fired inside
Tiruchirappalli, 'crop' inside microprocessor and 'shop' inside workshop, and
the wrong sector was stored at 0.90, never to be asked. Cues are now compiled
to word-boundary patterns, the approach ecosystem/taxonomy.py already uses.

Cue syntax, kept to what the lists need:

  * ``"shop"``     the whole word and its plain forms: shops; a word of four or
                   more letters also takes -er/-ers/-ing (farmers, farming),
                   one ending in -e takes -r/-rs (wholesaler), one ending in -y
                   takes -ies (factories). Spaces match any run of whitespace.
  * ``"weav*"``    an explicit stem: any word starting with it (weaver, weaving).
  * a compiled ``re.Pattern`` is used as given, for the few cues that need
    context ('course' but not 'of course').

Deliberately no -ed: 'unit' would match 'united'.
"""

from __future__ import annotations

import re
from collections.abc import Iterable


def _pattern(cue: str) -> str:
    cue = cue.strip().lower()
    if cue.endswith("*"):
        return r"\b" + re.escape(cue[:-1]).replace(r"\ ", r"\s+") + r"\w*"
    *head, last = cue.split()
    if last.endswith("y") and len(last) > 3:
        tail = re.escape(last[:-1]) + r"(?:y|ies)"
    elif last.endswith("e"):
        tail = re.escape(last) + r"(?:s|r|rs)?"
    elif len(last) >= 4:
        tail = re.escape(last) + r"(?:s|es|er|ers|ing)?"
    else:
        tail = re.escape(last) + r"(?:s|es)?"
    words = [re.escape(w) for w in head] + [tail]
    return r"\b" + r"\s+".join(words) + r"\b"


def compile_cues(cues: Iterable[str | re.Pattern[str]]) -> tuple[re.Pattern[str], ...]:
    """Word-boundary patterns for `cues` (see the module docstring for the syntax)."""
    return tuple(c if isinstance(c, re.Pattern) else re.compile(_pattern(c)) for c in cues)


def matches(text: str, patterns: Iterable[re.Pattern[str]]) -> bool:
    """True when any pattern occurs in `text` (lower-case it first)."""
    return any(p.search(text) for p in patterns)


# Negation (R070): "no customers yet" is not revenue. A negator within a few
# words before a cue denies it, within the same clause; Tamil and Hindi put
# the negator right after the word ("customers illai"). Cues that carry their
# own negation ("not started", "nothing built") are unaffected: only the words
# BEFORE the match are read.
_NEGATOR = re.compile(
    r"\b(?:no|not|never|nothing|without|yet\s+to|havent|hasnt|hadnt|dont|didnt|doesnt"
    r"|isnt|arent|wasnt|wont|cant)\b|n't\b"
)
_AFTER_NEGATOR = re.compile(r"^\W*(?:\w+\W+)?(?:illai|illa|nahi|nahin)\b")
_CLAUSE_END = re.compile(r"[,.;:!?]|\bbut\b")


def negated(text: str, start: int, end: int, *, window: int = 3) -> bool:
    """Is the cue at text[start:end] denied? `window` words before it, in its clause."""
    clause = _CLAUSE_END.split(text[:start])[-1]
    before = " ".join(clause.split()[-window:]) if window else ""
    return bool(_NEGATOR.search(before) or _AFTER_NEGATOR.match(text[end:]))


def affirmed(text: str, patterns: Iterable[re.Pattern[str]], *, window: int = 3) -> bool:
    """True when some pattern occurs in `text` without being negated."""
    return any(
        not negated(text, m.start(), m.end(), window=window)
        for p in patterns
        for m in p.finditer(text)
    )
