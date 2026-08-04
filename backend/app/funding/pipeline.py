"""Funding pipeline management (Task 4.6) — stage machine, board, metrics.

An investor relationship moves through an ordered set of stages. This module is
the deterministic core: it validates transitions, groups entries into a Kanban
board, and derives pipeline metrics (stage conversion, time-in-stage, weighted
value) from each entry's own stage history. No DB and no LLM — persistence
lands with the storage layer; everything here is a pure function of its input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
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

# Probability a relationship at this stage eventually closes — used to weight
# pipeline value so an early conversation isn't counted like a signed term sheet.
STAGE_PROBABILITY: dict[str, float] = {
    "initial_contact": 0.05,
    "pitch_scheduled": 0.10,
    "pitch_delivered": 0.20,
    "due_diligence": 0.40,
    "term_sheet": 0.65,
    "negotiation": 0.80,
    WON: 1.0,
    LOST: 0.0,
}

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
    """Stages this relationship has ever occupied (inferred when history is absent)."""
    if entry.history:
        return {h["stage"] for h in entry.history} | {entry.stage}
    if entry.stage in TERMINAL:
        return set(OPEN_STAGES) | {entry.stage}
    return {s for s in OPEN_STAGES if _ORDER[s] <= _ORDER[entry.stage]}


def _days(a: str, b: str) -> int | None:
    try:
        return (date.fromisoformat(b) - date.fromisoformat(a)).days
    except ValueError:
        return None


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
    weighted_value: int


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
    weighted = round(sum(e.amount * STAGE_PROBABILITY[e.stage] for e in open_entries))

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
        weighted_value=weighted,
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
