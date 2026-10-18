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

from app.core.stages import Stage
from app.elicitation.cues import compile_cues, matches
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
    Stage.IDEA: ("idea", "nothing built", "not started", "planning", "concept"),
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
    low = text.lower()
    for stage, patterns in _STAGE_PATTERNS.items():
        if matches(low, patterns):
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
