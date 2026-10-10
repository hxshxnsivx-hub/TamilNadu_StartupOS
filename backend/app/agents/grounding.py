"""Fact check before speech: a sentence the session cannot back is not said.

The model's reply is checked one sentence at a time, as it streams, before it
reaches the voice. A sentence is dropped when it contains:

    - a number (with or without ₹, %, lakh, crore) that appears nowhere in the
      session: tool results, known facts, the objective, the roadmap;
    - a government scheme the session never looked up;
    - a trial or project identifier that no tool returned.

Novelty claims ("unique", "first of its kind") are replaced by the standard
caveat. Pure functions, no model call: cheap enough for the voice path.
Only model-written text is checked; templated text is built from the session
by code and is grounded by construction.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

NOVELTY_LINE = (
    "I didn't find it in the sources I searched, which isn't proof it's new;"
    " a patent attorney's search is still needed before filing."
)
BANNED = re.compile(
    r"\b(unique|novel|first[- ]of[- ]its[- ]kind|never been done|no one (?:has|else)"
    r"|nobody (?:has|else)|world'?s first|completely new|groundbreaking)\b"
    # Tamil: unique, first time, never before, new invention
    r"|தனித்துவ|முதன்முறையாக|இதுவரை யாரும்|புதிய கண்டுபிடிப்பு"
    # Hindi: unique, first time, never before, nobody has
    r"|अनोखा|अनोखी|अद्वितीय|पहली बार|पहले कभी नहीं|किसी ने नहीं",
    re.I,
)
# A figure as said in a reply: 1,200 · 4.5 · 12% · ₹5 · 2022
NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{2,3})+|\d+(?:\.\d+)?)(?![\w])")
UNIT_AFTER = re.compile(r"^\s*(%|percent|lakh|lakhs|crore|crores|l\b|cr\b)", re.I)
NCT = re.compile(r"\bNCT\d{8}\b")
REPO = re.compile(r"\b[\w.-]+/[\w.-]+\b")
SENTENCE_END = re.compile(
    r"(?<!\bDr)(?<!\bRs)(?<!\bMr)(?<!\bMs)(?<!\bvs)[.!?\u0964\u0965](?=\s|$)"
)  # . ! ? and the Hindi danda (। ॥)
# Bare small counts ("two steps", "3 questions") carry little risk and are
# everywhere in natural speech; a figure with a unit or a year never passes free.
FREE_MAX = 12


@lru_cache
def scheme_names() -> tuple[dict[str, str], dict[str, str]]:
    """(lower-cased full names → id, acronyms in capitals → id).

    Acronyms match only in capitals: NEEDS is a scheme, "needs" is a verb.
    """
    from app.planner.registry import _catalogue

    names: dict[str, str] = {}
    acros: dict[str, str] = {}
    for sid, s in _catalogue().items():
        full = re.sub(r"\s*\([^)]*\)", "", s["name"]).strip()
        if len(full.split()) >= 2:
            names[full.lower()] = sid
        else:  # a one-word name is an acronym: TANSEED, NEEDS
            acros[full.upper()] = sid
        for acro in re.findall(r"\(([A-Za-z-]{2,})\)", s["name"]):
            acros[acro.upper()] = sid
        if "_" in sid:
            names[sid.replace("_", " ")] = sid
        else:
            acros[sid.upper()] = sid
    return names, acros


def mentioned_schemes(text: str) -> set[str]:
    names, acros = scheme_names()
    low = text.lower()
    found = {sid for name, sid in names.items() if re.search(rf"\b{re.escape(name)}\b", low)}
    found |= {sid for acro, sid in acros.items() if re.search(rf"\b{re.escape(acro)}\b", text)}
    return found


def _norm(num: str) -> str:
    n = num.replace(",", "")
    return n[:-2] if n.endswith(".0") else n


@dataclass
class Facts:
    """Everything the session can back: built once per change of state."""

    numbers: set[str] = field(default_factory=set)
    schemes: set[str] = field(default_factory=set)
    ids: set[str] = field(default_factory=set)
    text: str = ""


def facts_from(*blobs: object) -> Facts:
    text = " ".join(b if isinstance(b, str) else json.dumps(b, default=str) for b in blobs)
    low = text.lower()
    return Facts(
        numbers={_norm(m) for m in NUM.findall(text)},
        schemes=mentioned_schemes(text) | _scheme_ids_in(low),
        ids=set(NCT.findall(text)) | {r.lower() for r in REPO.findall(text)},
        text=low,
    )


def _scheme_ids_in(low: str) -> set[str]:
    """Scheme ids as tools return them (lower case, in data)."""
    from app.planner.registry import _catalogue

    return {sid for sid in _catalogue() if re.search(rf"\b{re.escape(sid)}\b", low)}


def problems(sentence: str, facts: Facts) -> list[str]:
    """Why this sentence cannot be said; empty when it is backed."""
    out = []
    for m in NUM.finditer(sentence):
        n = _norm(m.group(1))
        has_unit = bool(UNIT_AFTER.match(sentence[m.end() :])) or sentence[
            max(0, m.start() - 1) : m.start()
        ] in ("₹", "$")
        is_year = len(n) == 4 and n[:2] in ("19", "20")
        small = n.isdigit() and int(n) <= FREE_MAX and not has_unit
        if not small and n not in facts.numbers and not (is_year and n in facts.text):
            out.append(f"number {m.group(0)}")
    for sid in sorted(mentioned_schemes(sentence) - facts.schemes):
        out.append(f"scheme {sid}")
    for nct in NCT.findall(sentence):
        if nct not in facts.ids:
            out.append(f"trial {nct}")
    return out


def gate(sentence: str, facts: Facts) -> str | None:
    """The sentence to speak, the caveat in its place, or None to drop it."""
    if problems(sentence, facts):
        return None
    if BANNED.search(sentence):
        return NOVELTY_LINE
    return sentence


class SentenceSplitter:
    """Feed streamed text; get back whole sentences as soon as they end."""

    def __init__(self) -> None:
        self.buf = ""

    def feed(self, chunk: str) -> list[str]:
        self.buf += chunk
        out = []
        while (m := SENTENCE_END.search(self.buf)) is not None:
            out.append(self.buf[: m.end()].strip())
            self.buf = self.buf[m.end() :]
        return [s for s in out if s]

    def flush(self) -> list[str]:
        rest, self.buf = self.buf.strip(), ""
        return [rest] if rest else []


def check_reply(text: str, facts: Facts) -> tuple[list[str], list[dict]]:
    """Split a whole reply and gate each sentence: (kept, dropped with reasons)."""
    sp = SentenceSplitter()
    kept, dropped, caveat_said = [], [], False
    for s in sp.feed(text) + sp.flush():
        why = problems(s, facts)
        if why:
            dropped.append({"sentence": s, "why": why})
            continue
        if BANNED.search(s):
            if not caveat_said:
                kept.append(NOVELTY_LINE)
                caveat_said = True
            continue
        kept.append(s)
    return kept, dropped
