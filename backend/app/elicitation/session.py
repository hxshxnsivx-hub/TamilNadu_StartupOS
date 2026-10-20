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

from pydantic import BaseModel, Field, model_validator

from app.elicitation.answers import coerce
from app.elicitation.slots import (
    ANY_OF,
    BY_KEY,
    DISPUTED,
    REQUIRED_BY_MODE,
    TAU_CONFIRM,
    Band,
    EntryMode,
    Finger,
    band,
    contract_fingers,
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
    # The experience conversation, after its restatement: the founder picks one
    # of the offered opportunities, or none (R066). A pick fills the idea slots.
    CHOOSING = "choosing"
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
    CHOSEN = "chosen"  # from an opportunity card the founder picked (task 1.1.5.5)


# Founder-given values (R025): an inference never replaces one, however
# confident it is. Rank before confidence, so no future cue constant can undo it.
# A card the founder picked is their choice, not our guess.
FOUNDER_GIVEN = frozenset({Source.PROFILE, Source.ANSWER, Source.CHOSEN})


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


class Outcome(str, Enum):
    """What `put` did with a value (R053), so a caller never reports a fact as
    recorded when it was not."""

    STORED = "stored"  # the slot now holds the value
    KEPT_EXISTING = "kept_existing"  # a founder-given, locked or surer value stands
    CONFLICT = "conflict"  # two inferences disagree; the founder will be asked
    REJECTED = "rejected"  # the value fits no slot (R007)


class PutResult(BaseModel):
    outcome: Outcome
    current: SlotValue | None = None  # the slot after the merge


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

    # Answer checking. A reply that does not fit the asked slot counts as a
    # miss: the question is asked once more (`reask`), then dropped for good.
    mismatches: dict[str, int] = Field(default_factory=dict)
    reask: str | None = None
    # Slots the extractor newly filled on the last turn, to acknowledge them.
    learned: list[str] = Field(default_factory=list)
    # Questions raised by the council or the scan for this idea specifically
    # (build spec 3.2): {key: "dyn:…", question, source, asked, answer}.
    dynamic: list[dict] = Field(default_factory=list)

    # Slots the founder corrected at confirmation (task 1.1.2): only another
    # correction changes them.
    locked: set[str] = Field(default_factory=set)
    # A value that disagreed with a founder-given or locked one and lost; kept,
    # not silently dropped, so a later check can ask about the disagreement.
    rivals: dict[str, SlotValue] = Field(default_factory=dict)
    # The question budget counts questions, not turns (R009): a re-ask, a reply
    # to the restatement or a request for a view used to spend it too, so with
    # nine required slots the ranking inputs were never asked.
    questions_asked: int = 0
    # The question waiting for a reply: asking it again before the founder
    # replies is the same question, not a new one.
    open_question: str | None = None
    # Questions given back: one per correction.
    refunds: int = 0
    # The founder said the restatement is wrong and was asked what to change,
    # so the next reply is a correction however it is phrased.
    awaiting_correction: bool = False

    objective: str | None = None  # the restatement shown at CONFIRMING
    roadmap_id: uuid.UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="before")
    @classmethod
    def _count_questions_in_old_documents(cls, data: Any) -> Any:
        """A document saved before the counter existed: count the turns that
        answered a question, so a resumed session does not get a fresh budget."""
        if isinstance(data, dict) and "questions_asked" not in data and data.get("turns"):
            asked = sum(
                1
                for t in data["turns"]
                if (t.get("asked") if isinstance(t, dict) else getattr(t, "asked", None))
            )
            data = {**data, "questions_asked": asked}
        return data

    # ---------------------------------------------------------------- views

    @property
    def filled(self) -> set[str]:
        """Slot keys whose value we keep: the known and confirm bands (R157).

        Below TAU_CONFIRM a value is not a fact and is asked; a confirm-band
        value is not asked but said back as an assumption.
        """
        return {k for k, v in self.slots.items() if v.confidence >= TAU_CONFIRM}

    def kept(self) -> dict[str, Any]:
        """The plain values of the filled slots: what the roadmap, the panel and
        the restatement all work from. A value below TAU_CONFIRM (unknown or
        disputed) is left out, so the planner falls back to the same default the
        restatement says it will assume."""
        return {
            k: getattr(v.value, "value", v.value) for k, v in self.slots.items() if k in self.filled
        }

    def band(self, key: str) -> Band:
        v = self.slots.get(key)
        return band(v.confidence) if v is not None else Band.UNKNOWN

    @property
    def uncovered(self) -> set[Finger]:
        """Contract fingers still open (R113). A finger whose every askable slot
        was skipped is let go: a skipped question is never nagged."""
        open_ = contract_fingers(self.mode) - self.fingers
        req = REQUIRED_BY_MODE[self.mode]
        out = set()
        for finger in open_:
            keys = ANY_OF.get(finger) or {k for k in req if BY_KEY[k].finger is finger}
            if keys - self.skipped:
                out.add(finger)
        return out

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

    def put(
        self,
        key: str,
        value: Any,
        confidence: float,
        source: Source,
        *,
        correction: bool = False,
    ) -> PutResult:
        """Merge a slot value and say what happened.

        The value is first coerced to the slot's type (R007); one that fits no
        slot is rejected and nothing changes. Then, rank before confidence
        (R025):

        * a locked slot changes only by another `correction`;
        * a founder-given value (profile or answer) is never replaced by an
          inference (extraction, document, model note), however confident;
        * a direct answer always wins over anything that is not one: the user
          correcting us must never lose to our own guess;
        * two inferences that disagree, both in the known band, are a conflict
          (R053, task 1.1.3.3): the surer one is kept at DISPUTED confidence,
          below the confirm band, so the founder is asked; the other is kept
          in `rivals`. Only the founder settles a dispute;
        * otherwise an inference replaces another only when it is surer, and
          a founder-given value replaces one when it is at least as sure. At
          equal confidence the first inference stands: a reply to another
          question must not rewrite an earlier one.

        A value that loses to a founder-given or locked one and disagrees with
        it is kept in `rivals`.
        """
        typed = coerce(key, value)
        if typed is None:
            return PutResult(outcome=Outcome.REJECTED, current=self.slots.get(key))
        new = SlotValue(
            key=key, value=typed, confidence=confidence, source=source, turn=self.turn_no
        )
        existing = self.slots.get(key)
        if existing is not None and not correction:
            founder = source in FOUNDER_GIVEN
            if key in self.locked or (existing.source in FOUNDER_GIVEN and not founder):
                if typed != existing.value:
                    self.rivals[key] = new
                return PutResult(outcome=Outcome.KEPT_EXISTING, current=existing)
            if not founder and existing.source not in FOUNDER_GIVEN:
                outcome = self._merge_inference(existing, new)
                if outcome is not None:
                    return PutResult(outcome=outcome, current=self.slots.get(key))
            elif not (source is Source.ANSWER and existing.source is not Source.ANSWER):
                if confidence < existing.confidence:
                    return PutResult(outcome=Outcome.KEPT_EXISTING, current=existing)
        self.slots[key] = new
        self.rivals.pop(key, None)
        if correction:
            self.locked.add(key)
            self.skipped.discard(key)
        self.touch()
        return PutResult(outcome=Outcome.STORED, current=new)

    def _merge_inference(self, existing: SlotValue, new: SlotValue) -> Outcome | None:
        """One inference meeting another. None means store the new one."""
        key = existing.key
        if key in self.rivals:  # disputed: only the founder settles it
            return Outcome.CONFLICT
        if new.value == existing.value:
            if new.confidence > existing.confidence:
                return None
            return Outcome.STORED  # the slot already holds it
        known = band(existing.confidence) is Band.KNOWN and band(new.confidence) is Band.KNOWN
        if known and BY_KEY[key].kind != "text":
            keep, rival = (
                (new, existing)
                if new.confidence > existing.confidence  # at a tie the first stands
                else (
                    existing,
                    new,
                )
            )
            self.slots[key] = keep.model_copy(update={"confidence": min(keep.confidence, DISPUTED)})
            self.rivals[key] = rival
            self.touch()
            return Outcome.CONFLICT
        if new.confidence > existing.confidence:
            return None
        return Outcome.KEPT_EXISTING

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
