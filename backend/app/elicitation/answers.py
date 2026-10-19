"""Does a reply actually answer the question that was asked?

A direct answer outranks every guess (session.put), which is exactly why a
wrong-type answer is dangerous: "Chennai" given to "where are you today?" was
stored as the stage, at answer confidence, and nothing could correct it.

`validate(slot, text)` returns the typed value when the reply fits the slot,
or None when it does not. The engine then lets the extractor place the reply
where it does fit and asks the question once more.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from app.core.stages import Stage, parse_stage
from app.elicitation.cues import affirmed, compile_cues
from app.elicitation.extract import extract
from app.elicitation.places import find_district
from app.elicitation.slots import BY_KEY

# Stage words as a founder answers the stage question directly. Broader than
# the extractor's cues, which must catch stage in passing and so need phrases.
# Whole words (app/elicitation/cues.py): "ideally" is not "idea".
_STAGE_WORDS: dict[Stage, tuple[str, ...]] = {
    Stage.REVENUE: ("selling", "sales", "revenue", "customers", "orders", "earning"),
    Stage.GROWTH: ("growing", "scaling", "expanding"),
    Stage.MVP: ("mvp", "pilot", "beta", "first version", "launched"),
    Stage.PROTOTYPE: ("prototyp*", "sample", "working model", "demo"),
    Stage.POC: ("proof of concept", "poc", "tested", "validated"),
    Stage.IDEA: (
        "idea",
        "nothing built",
        "not started",
        "haven't started",
        "yet to start",
        "planning",
        "concept",
    ),
}
_STAGE_PATTERNS = {stage: compile_cues(words) for stage, words in _STAGE_WORDS.items()}

_NUMBER_WORDS = {
    w: i
    for i, w in enumerate(
        (
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
            "seventeen", "eighteen", "nineteen", "twenty",
        )  # fmt: skip
    )
}

SKIP = re.compile(
    r"^\s*(skip|pass|next|not sure|no idea|don'?t know|i don'?t know|theriyala)\W*$", re.I
)


def _stage(text: str) -> str | None:
    """The first stage whose word the reply says without denying it (R070).

    A denied stage word ("no customers yet", "we haven't launched") says where
    the founder is not, not where they are. With nothing else said, the reply
    does not answer the question and is asked once more rather than guessed:
    a guess here would be stored as the founder's own answer.
    """
    low = text.lower()
    for stage, patterns in _STAGE_PATTERNS.items():
        if affirmed(low, patterns):
            return stage.value
    return None


def _int(text: str, bounds: tuple[int, int] | None) -> int | None:
    low = text.lower()
    nums = [int(t) for t in re.findall(r"\d+", low)]
    nums += [_NUMBER_WORDS[w] for w in re.findall(r"[a-z]+", low) if w in _NUMBER_WORDS]
    if not nums:
        return None
    lo, hi = bounds or (0, 10**6)
    return nums[0] if lo <= nums[0] <= hi else None


def _enum(key: str, text: str, enum: type[Enum]) -> Enum | None:
    low = text.strip().lower()
    for member in enum:
        if member.value.lower() == low or re.search(rf"\b{re.escape(member.value.lower())}\b", low):
            return member
    # The extractor knows the everyday words ("5 lakh", "bank loan", "garments").
    for e in extract(text):
        if e.key == key:
            return e.value
    return None


def validate(key: str, text: str) -> Any | None:
    """The typed value if `text` answers slot `key`, else None."""
    slot = BY_KEY.get(key)
    raw = text.strip()
    if slot is None or not raw or SKIP.match(raw):
        return None
    if key == "district":
        return find_district(raw)
    if key == "stage":
        return _stage(raw)
    if slot.enum is not None:
        return _enum(key, raw, slot.enum)
    if slot.kind == "int":
        return _int(raw, slot.bounds)
    if slot.kind == "multi":
        parts = [p.strip() for p in re.split(r",|\band\b|/", raw) if p.strip()]
        return parts or None
    # Free-text slots: a bare place name or a bare number is not a description.
    if find_district(raw) and len(raw.split()) <= 2:
        return None
    if re.fullmatch(r"[\d\s.,₹]+", raw) or len(raw) < 3:
        return None
    return raw


def coerce(key: str, value: Any) -> Any | None:
    """The slot's typed value for `value` from any source, or None (R007).

    Every value passes here before it is stored (session.put): the extractor's
    and the profile's, a spoken answer and a model's note. A model could store
    "about five" as the team size, which then broke the roadmap's number
    comparisons, or "healthtech" as a sector no downstream rule knows. Typed
    values pass as they are; text is read with the slot's own answer rules.
    The stage takes only the shared vocabulary (app/core/stages.py), never a
    loose phrase.
    """
    slot = BY_KEY.get(key)
    if slot is None or value is None or isinstance(value, bool):
        return None
    if key == "stage":
        stage = parse_stage(value)
        return stage.value if stage else None
    if slot.enum is not None:
        if isinstance(value, slot.enum):
            return value
        return validate(key, value) if isinstance(value, str) else None
    if slot.kind == "int":
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if isinstance(value, int):
            lo, hi = slot.bounds or (0, 10**6)
            return value if lo <= value <= hi else None
        return _int(value, slot.bounds) if isinstance(value, str) else None
    if slot.kind == "multi" and isinstance(value, (list, tuple)):
        if not all(isinstance(x, str) for x in value):
            return None
        return [x.strip() for x in value if x.strip()] or None
    return validate(key, value) if isinstance(value, str) else None
