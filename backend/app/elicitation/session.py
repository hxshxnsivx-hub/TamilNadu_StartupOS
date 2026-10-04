"""The elicitation session — the aggregate that makes ideation multi-turn.

This is the piece whose absence was the root defect. `RoadmapSwarm.generate`
took a string and returned a roadmap; `routers/ideation.py` constructed a
`ConversationState` inside the request handler and threw it away on return. So
the swarm could *generate* clarifying questions but had nowhere to put an
answer. Architecturally it could not have a second turn, which is why no amount
of prompt work could have made it feel dynamic.

Everything here is pure domain state — no ORM, no I/O — so the turn loop is
unit-testable without a database. Persistence is a separate concern (`store`).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.elicitation.slots import (
    BY_KEY,
    REQUIRED_BY_MODE,
    EntryMode,
    Finger,
    fingers_covered,
    missing_required,
)

# Idle expiry. Long, because a founder gathering documents may legitimately
# disappear for weeks; a session that dies over a weekend is a session nobody
# finishes.
IDLE_EXPIRY = timedelta(days=30)


class SessionState(str, Enum):
    NEW = "new"
    EXTRACTING = "extracting"
    ELICITING = "eliciting"
    AWAITING_ANSWER = "awaiting_answer"
    CONFIRMING = "confirming"
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"
    EXPIRED = "expired"


class Source(str, Enum):
    """Where a slot value came from. Drives merge precedence and confidence."""

    PROFILE = "profile"  # pre-filled from the founders table — never re-asked
    ANSWER = "answer"  # the user answered the question directly
    EXTRACTED = "extracted"  # inferred from free text
    DOCUMENT = "document"  # parsed from an upload
    DEFAULT = "default"


class SlotValue(BaseModel):
    """One filled slot, with provenance.

    Confidence matters: an extracted value at 0.4 should still be confirmed,
    while a profile value at 0.95 must never be asked about again.
    """

    key: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source: Source
    turn: int = 0


class Turn(BaseModel):
    n: int
    asked: str | None = None  # slot key we asked about
    question: str | None = None
    user_text: str | None = None
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ElicitationSession(BaseModel):
    """The conversation. One per founder per idea attempt."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: str
    mode: EntryMode = EntryMode.IDEA
    state: SessionState = SessionState.NEW

    slots: dict[str, SlotValue] = Field(default_factory=dict)
    turns: list[Turn] = Field(default_factory=list)

    # Slots the user declined to answer. Excluded from candidate selection so
    # we never nag — a skipped question that keeps coming back is the fastest
    # way to make someone abandon the flow.
    skipped: set[str] = Field(default_factory=set)

    objective: str | None = None  # the restatement shown at CONFIRMING
    roadmap_id: uuid.UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # ---------------------------------------------------------------- views

    @property
    def filled(self) -> set[str]:
        """Slot keys whose value we actually trust.

        The 0.5 floor is deliberate: a low-confidence extraction is a *hint*,
        not a fact, and treating it as filled is how the system ends up
        confidently wrong about someone's business.
        """
        return {k for k, v in self.slots.items() if v.confidence >= 0.5}

    @property
    def missing(self) -> set[str]:
        return missing_required(self.filled, self.mode) - self.skipped

    @property
    def fingers(self) -> set[Finger]:
        return fingers_covered(self.filled, self.mode)

    @property
    def required_count(self) -> int:
        return len(REQUIRED_BY_MODE[self.mode])

    @property
    def turn_no(self) -> int:
        return len(self.turns)

    @property
    def expired(self) -> bool:
        return datetime.now(UTC) - self.updated_at > IDLE_EXPIRY

    def progress(self) -> float:
        req = REQUIRED_BY_MODE[self.mode]
        if not req:
            return 1.0
        return len(self.filled & set(req)) / len(req)

    # ---------------------------------------------------------------- writes

    def put(self, key: str, value: Any, confidence: float, source: Source) -> None:
        """Merge a slot value.

        Precedence rule: a new value only wins if it is at least as confident
        as what is already there, EXCEPT that a direct user answer always wins
        over an extraction. The user correcting us must never lose to our own
        guess.
        """
        if key not in BY_KEY:
            return
        existing = self.slots.get(key)
        if existing is not None:
            user_correcting = source is Source.ANSWER and existing.source is not Source.ANSWER
            if not user_correcting and confidence < existing.confidence:
                return
        self.slots[key] = SlotValue(
            key=key, value=value, confidence=confidence, source=source, turn=self.turn_no
        )
        self.touch()

    def skip(self, key: str) -> None:
        self.skipped.add(key)
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    def record(self, **kw: Any) -> Turn:
        t = Turn(n=self.turn_no + 1, **kw)
        self.turns.append(t)
        self.touch()
        return t
