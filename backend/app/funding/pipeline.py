"""Funding pipeline management (Task 4.6) — stage machine, board, metrics.

An investor relationship moves through an ordered set of stages. This module is
the deterministic core: it validates transitions, groups entries into a Kanban
board, and derives pipeline metrics (stage conversion, time-in-stage, value by
stage) from each entry's own stage history. No DB and no LLM — persistence
lands with the storage layer; everything here is a pure function of its input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

# Ordered open stages, then the two terminal outcomes.
OPEN_STAGES: list[str] = [
    "initial_contact",
    "pitch_scheduled",
    "pitch_delivered",
    "due_diligence",
    "term_sheet",
    "negotiation",
]
WON, LOST = "closed_won", "closed_lost"
STAGES: list[str] = [*OPEN_STAGES, WON, LOST]
TERMINAL: set[str] = {WON, LOST}

_ORDER = {s: i for i, s in enumerate(OPEN_STAGES)}

# A deal may be won only once it has real commitment behind it.
_WIN_FROM = {"term_sheet", "negotiation"}


@dataclass
class PipelineEntry:
    investor_id: str
    investor_name: str
    stage: str
    amount: int = 0
    history: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PipelineEntry:
        stage = str(d.get("stage", "initial_contact"))
        if stage not in STAGES:
            raise ValueError(f"Unknown stage '{stage}'")
        hist = [
            {"stage": str(h.get("stage", "")), "at": str(h.get("at", ""))}
            for h in d.get("history", [])
            if str(h.get("stage", "")) in STAGES
        ]
        return cls(
            investor_id=str(d.get("investor_id", "")),
            investor_name=str(d.get("investor_name", "")),
            stage=stage,
            amount=int(d.get("amount", 0) or 0),
            history=hist,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "investor_id": self.investor_id,
            "investor_name": self.investor_name,
            "stage": self.stage,
            "amount": self.amount,
            "history": self.history,
        }


def can_advance(frm: str, to: str) -> tuple[bool, str]:
    """Validate a stage transition, returning (ok, reason-when-not)."""
    if frm not in STAGES:
        return False, f"Unknown stage '{frm}'"
    if to not in STAGES:
        return False, f"Unknown stage '{to}'"
    if frm in TERMINAL:
        return False, f"'{frm}' is final — the relationship is already concluded"
    if to == frm:
        return False, "Already at this stage"
    if to == LOST:
        return True, ""
    if to == WON:
        if frm in _WIN_FROM:
            return True, ""
        return False, "A deal can only be won from term sheet or negotiation"
    # Forward movement through the open stages, one step at a time.
    if _ORDER[to] < _ORDER[frm]:
        return False, "Pipeline stages move forward only"
    if _ORDER[to] != _ORDER[frm] + 1:
        return False, f"Cannot skip stages — next is '{OPEN_STAGES[_ORDER[frm] + 1]}'"
    return True, ""


def advance(entry: PipelineEntry, to_stage: str, at: str | None = None) -> PipelineEntry:
    """Move an entry to `to_stage`, appending to its history. Raises on invalid moves."""
    ok, reason = can_advance(entry.stage, to_stage)
    if not ok:
        raise ValueError(reason)
    stamp = at or date.today().isoformat()
    history = [*entry.history]
    if not history:
        history.append({"stage": entry.stage, "at": stamp})
    history.append({"stage": to_stage, "at": stamp})
    return PipelineEntry(
        investor_id=entry.investor_id,
        investor_name=entry.investor_name,
        stage=to_stage,
        amount=entry.amount,
        history=history,
    )


def _reached(entry: PipelineEntry) -> set[str]:
    """Stages this relationship has ever occupied (inferred when history is absent).

    A terminal entry with no trail is not assumed to have passed through every
    stage — that counted lost deals as having reached negotiation and inflated
    conversion at each stage (F-A4-020). A lost deal is credited only with the
    first contact; a won deal with the open stages up to the term sheet it must
    have been won from (negotiation is not implied)."""
    if entry.history:
        return {h["stage"] for h in entry.history} | {entry.stage}
    if entry.stage == LOST:
        return {OPEN_STAGES[0], LOST}
    if entry.stage == WON:
        return set(OPEN_STAGES[: _ORDER["term_sheet"] + 1]) | {WON}
    return {s for s in OPEN_STAGES if _ORDER[s] <= _ORDER[entry.stage]}


def _to_date(s: str) -> date | None:
    """Parse a 'YYYY-MM-DD' date or a full ISO datetime ('...T..:..Z' or with an
    offset, as the frontend stamps with Date.toISOString). 'Z' is normalised so
    it parses on Python 3.10 as well as 3.11 (F-A4-020)."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    iso = s[:-1] + "+00:00" if s.endswith("Z") else s
    try:
        return datetime.fromisoformat(iso).date()
    except ValueError:
        pass
    try:  # last resort: a leading YYYY-MM-DD
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _days(a: str, b: str) -> int | None:
    da, db = _to_date(a), _to_date(b)
    return (db - da).days if da is not None and db is not None else None


@dataclass
class PipelineMetrics:
    total: int
    by_stage: dict[str, int]
    open_count: int
    won: int
    lost: int
    win_rate: int
    stage_conversion: dict[str, int]
    avg_days_in_stage: dict[str, float]
    pipeline_value: int
    value_by_stage: dict[str, int]


def pipeline_metrics(entries: list[PipelineEntry]) -> PipelineMetrics:
    total = len(entries)
    by_stage = {s: 0 for s in STAGES}
    for e in entries:
        by_stage[e.stage] += 1

    won, lost = by_stage[WON], by_stage[LOST]
    concluded = won + lost
    win_rate = round(won / concluded * 100) if concluded else 0

    conversion = {
        s: (round(sum(1 for e in entries if s in _reached(e)) / total * 100) if total else 0)
        for s in STAGES
    }

    durations: dict[str, list[int]] = {s: [] for s in STAGES}
    for e in entries:
        for cur, nxt in zip(e.history, e.history[1:], strict=False):
            d = _days(cur["at"], nxt["at"])
            if d is not None and d >= 0:
                durations[cur["stage"]].append(d)
    avg_days = {s: (round(sum(v) / len(v), 1) if v else 0.0) for s, v in durations.items()}

    open_entries = [e for e in entries if e.stage not in TERMINAL]
    value = sum(e.amount for e in open_entries)
    # Open pipeline value split by the stage it actually sits in — an honest,
    # uncited breakdown instead of a made-up per-stage probability (F-A4-020).
    value_by_stage = {s: sum(e.amount for e in open_entries if e.stage == s) for s in OPEN_STAGES}

    return PipelineMetrics(
        total=total,
        by_stage=by_stage,
        open_count=len(open_entries),
        won=won,
        lost=lost,
        win_rate=win_rate,
        stage_conversion=conversion,
        avg_days_in_stage=avg_days,
        pipeline_value=value,
        value_by_stage=value_by_stage,
    )


def kanban(entries: list[PipelineEntry]) -> list[dict[str, Any]]:
    """Group entries into ordered board columns, one per stage."""
    return [
        {
            "stage": s,
            "count": sum(1 for e in entries if e.stage == s),
            "value": sum(e.amount for e in entries if e.stage == s),
            "entries": [e.to_dict() for e in entries if e.stage == s],
        }
        for s in STAGES
    ]


def next_stages(stage: str) -> list[str]:
    """The stages an entry may legally move to from here (for UI affordances)."""
    return [s for s in STAGES if can_advance(stage, s)[0]]
