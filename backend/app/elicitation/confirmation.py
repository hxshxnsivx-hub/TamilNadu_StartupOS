"""Reading the founder's reply to the restatement (task 1.1.2, arena R005).

The reply used to be read as a bag of words: 'right' is a yes word and 'not'
a no word, and a yes word anywhere won, so "that's not right" confirmed the
restatement. A correction said with a yes ("yes, but it's Salem") was never
read at all, and one said with a no ran the ordinary extractor, which has no
negation: "Salem not Madurai" stored Madurai.

Now the reply is always read for facts, with negated phrases removed first,
and its yes or no only decides what happens when it changed nothing. A fact
replaces what the founder already gave only when the reply is anchored as a
correction (`anchored`, `named`): an aside in a long reply ("my wife works in
a school") is not a correction of the sector (R025).
"""

from __future__ import annotations

import re

from app.elicitation.answers import validate
from app.elicitation.extract import Extraction, extract

# The fill threshold (selector.TAU_FILL). A correction must be a fact, not the
# loose positional guess that reads any long reply as "the problem".
_MIN_CONFIDENCE = 0.60

YES = frozenset(
    {
        "yes",
        "yeah",
        "yep",
        "correct",
        "right",
        "ok",
        "okay",
        "sure",
        "fine",
        "exactly",
        "seri",
        "sari",
        "aamaa",
        "aama",
        "haan",
        "theek",
        "thik",
    }
)
NO = frozenset({"no", "nope", "wrong", "incorrect", "illai", "nahi", "nahin", "galat", "thappu"})

# Negate what follows them ("not Madurai", "isn't right").
_NEGATORS = frozenset(
    {"not", "no", "never", "isn't", "isnt", "aren't", "wasn't", "don't", "dont", "nope"}
)
# Tamil and Hindi put the negation after the word: "Madurai illai", "Madurai nahi".
_AFTER = frozenset({"illai", "nahi", "nahin"})
# A negated phrase ends here: "not Madurai but Salem", "not agriculture, it is electronics".
_BOUNDARY = frozenset(
    {"but", "it", "it's", "its", "i", "i'm", "we", "we're", "my", "our", "and", "rather"}
)
_MAX_NEGATED = 4  # words taken by one negator
# "No change", "no problem": a no word that agrees.
_AGREEING_NO = re.compile(r"\bno\s+(?:changes?|problem|issues?|corrections?)\b", re.I)
_PUNCT = ".,;:!?\"'"
# "Not really", "not quite": a negator with nothing after it but a softener is a no.
_SOFTENERS = frozenset({"really", "quite", "exactly", "so", "much", "fully", "entirely"})

# Words that mark a reply as correcting something, said with a yes or a no.
_CUES = frozenset(
    {"but", "except", "only", "actually", "instead", "change", "correction", "however"}
)
# A reply this short (yes and no words aside) is mostly the fact itself: "Salem".
_SHORT_REPLY = 5
# How each restated slot is named when the founder corrects it ("the district
# is Salem", "team is 3"). Naming a slot anchors a correction of it.
_SLOT_NAMES: dict[str, tuple[str, ...]] = {
    "sector": ("sector", "industry", "field"),
    "product_form": ("product type", "form"),
    "district": ("district", "place", "based", "located", "location"),
    "stage": ("stage",),
    "capital_band": ("budget", "capital", "invest", "investment"),
    "funding_route": ("funding", "funded", "fund"),
    "geo_scope": ("reach", "market"),
    "team_size": ("team", "people"),
    "founder_years": ("years", "experience"),
}
_NAME_PATTERNS = {
    key: re.compile(r"\b(?:" + "|".join(re.escape(n) for n in names) + r")\b", re.I)
    for key, names in _SLOT_NAMES.items()
}
# Slots the extractor cannot read in passing; a named correction is read with
# the slot's own answer rules (answers.validate) instead.
_READ_WHEN_NAMED = ("team_size", "founder_years", "geo_scope")
_CLAUSES = re.compile(r"[,.;!?]|\bbut\b|\band\b", re.I)

# The clause a correction word introduces, up to the next punctuation.
_AFTER_CUE = re.compile(r"\b(?:" + "|".join(sorted(_CUES)) + r")\b[\s,]*([^,.;!?]*)", re.I)
# What may stand before the fact in that clause: "it's Salem", "we are in Salem".
_CUE_LEAD = re.compile(
    r"^(?:(?:it'?s|it is|it should be|that is|that's|we are|we're|i am|i'm)\s+)?"
    r"(?:(?:in|from|based in|at)\s+)?(?:the|a|an)?\s*",
    re.I,
)
_CUE_FACT_WORDS = 3  # "it's Salem", "a textile business": the fact and little else
# Kept out of `_CUE_LEAD` deliberately: "I am a farmer's son" describes the
# founder, it does not correct the sector. Only "I am in/from ..." is a place.
_I_AM_DESCRIPTION = re.compile(r"^(?:i am|i'm)\s+(?!in\b|from\b|based\b|at\b)", re.I)

# Experience, for founder_years (see `_about_experience`).
_EXPERIENCE = re.compile(
    r"\bexperience\b|\bi(?:'ve|\s+have)?\s+(?:been\s+)?(?:worked|working|been)\b", re.I
)
_TIMELINE = re.compile(
    r"\b(?:in|within|after|by|next)\s+(?:\d+|a|an|one|two|three|four|five|few)\s+years?\b"
    r"|\b(?:launch\w*|running|thinking|plan\w*|start\w*|open\w*)\b",
    re.I,
)
_OTHER_PERSON = re.compile(
    r"\b(?:he|she|they|his|her|their)\b|\bmy\s+(?:brother|sister|father|mother|wife|husband"
    r"|son|daughter|friend|partner|uncle|aunt|cousin|family|dad|mom|amma|appa)\b",
    re.I,
)


def _core(token: str) -> str:
    return token.lower().strip(_PUNCT)


def polarity(text: str) -> bool | None:
    """True for a yes, False for a no, None when the reply says neither.

    A negator within two words before a yes word turns it into a no ("not
    right", "isn't quite correct").
    """
    tokens = [_core(t) for t in _AGREEING_NO.sub(" fine ", text).split()]
    negative = False
    positive = False
    for i, tok in enumerate(tokens):
        if tok in YES:
            if any(t in _NEGATORS for t in tokens[max(0, i - 2) : i]) or (
                i + 1 < len(tokens) and tokens[i + 1] in _AFTER
            ):
                negative = True
            else:
                positive = True
        elif tok in NO:
            negative = True
        elif tok in _NEGATORS and all(t in _SOFTENERS for t in tokens[i + 1 :]):
            negative = True  # "not really", or a bare "not" at the end
    if negative:
        return False
    return True if positive else None


def strip_negated(text: str) -> str:
    """The reply without what it denies: "Salem not Madurai" -> "Salem"."""
    tokens = text.split()
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        core = _core(tok)
        if core in _AFTER:
            if out:
                out.pop()
            i += 1
            continue
        if core in _NEGATORS:
            i += 1
            if tok[-1] in _PUNCT:  # "No, it is Salem": the no stands alone
                continue
            taken = 0
            while i < len(tokens) and taken < _MAX_NEGATED:
                if _core(tokens[i]) in _BOUNDARY:
                    break
                ends = tokens[i][-1] in ",.;:!?"
                i += 1
                taken += 1
                if ends:
                    break
            continue
        out.append(tok)
        i += 1
    return " ".join(out)


def corrections(text: str) -> list[Extraction]:
    """Facts the reply states, read without its negated phrases."""
    return [e for e in extract(strip_negated(text)) if e.confidence >= _MIN_CONFIDENCE]


def anchored(text: str) -> bool:
    """Does the reply as a whole read as a correction? A no or negation, or a
    reply that is mostly the fact. A correction word alone is not enough:
    "yes, but my wife works in a school" is an aside, not a sector correction;
    `after_cue` reads what such a word introduces."""
    tokens = [_core(t) for t in text.split()]
    if any(t in NO or t in _NEGATORS or t in _AFTER for t in tokens):
        return True
    return len([t for t in tokens if t and t not in YES]) <= _SHORT_REPLY


def has_cue(text: str) -> bool:
    """A correction word: "yes, but ..." is not a plain yes."""
    return any(_core(t) in _CUES for t in text.split())


def after_cue(text: str) -> set[str]:
    """Slots corrected by the clause right after a correction word, when that
    clause is just the fact: "yes, but it's Salem", "but we are in Salem".
    A clause about someone or something else ("but my wife works in a
    school", "but I am a farmer's son") corrects nothing."""
    keys: set[str] = set()
    for m in _AFTER_CUE.finditer(strip_negated(text)):
        clause = m.group(1).strip()
        if _I_AM_DESCRIPTION.match(clause):
            continue
        rest = _CUE_LEAD.sub("", clause)
        if rest and len(rest.split()) <= _CUE_FACT_WORDS:
            keys |= {e.key for e in extract(rest) if e.confidence >= _MIN_CONFIDENCE}
    return keys


def named(text: str) -> set[str]:
    """Restated slots the reply names ("the district is ...")."""
    low = strip_negated(text)
    return {key for key, pattern in _NAME_PATTERNS.items() if pattern.search(low)}


def _about_experience(clause: str) -> bool:
    """Years in a clause are the founder's own experience only when the clause
    says so ("experience", "I've worked ... 5 years"), and never when it is a
    timeline ("running in 2 years", "launch", "thinking about") or about
    someone else ("my brother has 10 years")."""
    if _TIMELINE.search(clause) or _OTHER_PERSON.search(clause):
        return False
    return bool(_EXPERIENCE.search(clause))


def named_values(text: str) -> list[Extraction]:
    """Values for slots the extractor cannot read, taken from the clause that
    names them: "yes but team is 3" -> team_size 3."""
    out = []
    clauses = _CLAUSES.split(strip_negated(text))
    for key in _READ_WHEN_NAMED:
        for clause in clauses:
            if not _NAME_PATTERNS[key].search(clause):
                continue
            if key == "founder_years" and not _about_experience(clause):
                continue
            value = validate(key, clause)
            if value is not None:
                out.append(Extraction(key, value, 0.90))
                break
    return out


__all__ = [
    "NO",
    "YES",
    "after_cue",
    "anchored",
    "corrections",
    "has_cue",
    "named",
    "named_values",
    "polarity",
    "strip_negated",
]
