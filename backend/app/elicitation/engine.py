"""The turn loop — the orchestrator that makes ideation a conversation.

This is the piece the old code could not have. `RoadmapSwarm.generate(text)`
was one input, one output; the clarifying questions it produced had nowhere to
send an answer. This module owns the state machine, so a question asked on
turn 3 can be answered on turn 4.

State machine (rnd-elicitation.md §5.2):

    NEW -> EXTRACTING -> ELICITING <-> AWAITING_ANSWER
                             |
                             v
                        CONFIRMING --reject--> ELICITING
                             | confirm
                             v
                        GENERATING -> COMPLETE | FAILED

Pure domain logic — no I/O, no ORM — so the whole loop is unit-testable
without a database.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal

from app.elicitation.answers import validate
from app.elicitation.extract import extract
from app.elicitation.selector import Q_MAX, is_objective_clear, next_question
from app.elicitation.session import (
    ElicitationSession,
    SessionState,
    Source,
)
from app.elicitation.slots import BY_KEY, EntryMode

ActionKind = Literal["ask", "confirm", "generate", "done"]


@dataclass(frozen=True)
class Action:
    """What the caller should do next. The API layer renders this."""

    kind: ActionKind
    slot: str | None = None
    question: str | None = None
    objective: str | None = None
    gaps: tuple[str, ...] = ()
    progress: float = 0.0
    turn: int = 0
    reason: str = ""


# Slots we will happily accept from a founder profile at high confidence, so
# the selector never asks for something the user already told us. Re-asking a
# founder for their district after they filled in a profile is the single most
# corrosive thing this feature could do.
PROFILE_SLOTS = ("district", "founder_years", "founder_skills", "owned_assets", "sector")

# Readable labels for enum values. Internal codes like "10L_50L" and
# "it_services" are storage identifiers, not something to show a founder — and
# this product's users may be reading in their second or third language.
HUMAN: dict[str, str] = {
    "under_2L": "under ₹2 lakh",
    "2L_10L": "₹2–10 lakh",
    "10L_50L": "₹10–50 lakh",
    "50L_2.5Cr": "₹50 lakh–2.5 crore",
    "above_2.5Cr": "over ₹2.5 crore",
    "self": "your own funds",
    "debt": "a loan",
    "equity": "investors",
    "grant": "a grant",
    "mixed": "a mix of sources",
    "software": "software",
    "physical": "a physical product",
    "service": "a service",
    "hybrid": "a mix of product and service",
    "it_services": "IT services",
    "agri": "agriculture",
    "poc": "proof of concept",
    "mvp": "MVP",
}

# The solution extractor strips the cue phrase ("I want to ..."), which takes
# the infinitive marker with it and leaves a bare verb. Restoring "to" is the
# difference between "Your plan is start a unit" and "Your plan is to start a
# unit".
_BARE_INFINITIVES = frozenset(
    {
        "start",
        "build",
        "make",
        "open",
        "set",
        "create",
        "launch",
        "run",
        "produce",
        "supply",
        "sell",
        "provide",
        "offer",
        "develop",
        "manufacture",
    }
)


def start(
    user_id: str,
    *,
    mode: EntryMode = EntryMode.IDEA,
    profile: dict[str, Any] | None = None,
) -> ElicitationSession:
    """Open a session, pre-filling anything the profile already knows."""
    s = ElicitationSession(user_id=user_id, mode=mode)
    for key in PROFILE_SLOTS:
        if profile and profile.get(key) not in (None, "", [], {}):
            s.put(key, profile[key], 0.95, Source.PROFILE)
    s.state = SessionState.ELICITING
    return s


def observe(session: ElicitationSession, text: str, *, answering: str | None = None) -> None:
    """Fold a user utterance into the slots.

    `answering` names the slot we asked about, so a direct reply is recorded
    as an ANSWER (which outranks any earlier extraction) even when the free-text
    extractor cannot parse it.
    """
    session.state = SessionState.EXTRACTING
    session.learned = []

    if answering and answering.startswith(DYN) and text.strip():
        for d in session.dynamic:  # free text: the founder's own answer, kept as said
            if d["key"] == answering:
                d["answer"] = text.strip()
    elif answering and answering in BY_KEY and text.strip():
        value = validate(answering, text)
        if value is not None:
            session.put(answering, value, 0.90, Source.ANSWER)
            session.reask = None
        else:
            # Not an answer to this question ("Chennai" for the stage). Never
            # store it there; let the extractor place it, and ask once more.
            misses = session.mismatches.get(answering, 0) + 1
            session.mismatches[answering] = misses
            session.reask = answering if misses < 2 else None
            if misses >= 2:
                session.skip(answering)

    for e in extract(text):
        # Never let an extraction overwrite the direct answer we just stored.
        if e.key == answering:
            continue
        was_filled = e.key in session.filled
        session.put(e.key, e.value, e.confidence, Source.EXTRACTED)
        if not was_filled and e.key in session.filled:
            session.learned.append(e.key)

    session.record(user_text=text, asked=answering)
    session.state = SessionState.ELICITING


def step(session: ElicitationSession) -> Action:
    """Decide the next move. Idempotent — safe to call repeatedly."""
    if session.state in (SessionState.COMPLETE, SessionState.FAILED):
        return Action(kind="done", progress=session.progress(), turn=session.turn_no)

    decision = is_objective_clear(session)

    # 1. A question the founder just answered with the wrong kind of reply is
    #    asked once more first, acknowledging what the reply did tell us.
    if (
        not decision.stop
        and (key := session.reask)
        and key not in session.filled
        and key not in session.skipped
    ):
        session.state = SessionState.AWAITING_ANSWER
        return Action(
            kind="ask",
            slot=key,
            question=f"{_acknowledge(session)} {BY_KEY[key].question}",
            progress=session.progress(),
            turn=session.turn_no,
            reason="reask: the reply did not answer the question",
        )

    # 2. Then a question the review panel raised: it marks where the evidence and
    #    the advisers disagree most. It still counts toward the Q_MAX ceiling.
    if (dyn := _pending_dynamic(session)) is not None and session.turn_no < Q_MAX:
        dyn["asked"] = True
        session.state = SessionState.AWAITING_ANSWER
        return Action(
            kind="ask",
            slot=dyn["key"],
            question=dyn["question"],
            progress=session.progress(),
            turn=session.turn_no,
            reason=f"dynamic: raised by {dyn['source']}",
        )

    # 3. Otherwise the most valuable unanswered slot.
    if not decision.stop:
        nq = next_question(session)
        if nq is not None:
            key, question = nq
            session.state = SessionState.AWAITING_ANSWER
            return Action(
                kind="ask",
                slot=key,
                question=question,
                progress=session.progress(),
                turn=session.turn_no,
                reason=decision.reason,
            )
        # Nothing left worth asking; fall through to confirmation.

    session.objective = restate(session)
    session.state = SessionState.CONFIRMING
    return Action(
        kind="confirm",
        objective=session.objective,
        gaps=decision.unfilled,
        progress=session.progress(),
        turn=session.turn_no,
        reason=decision.reason,
    )


def _acknowledge(session: ElicitationSession) -> str:
    """Name what the last reply did tell us, before asking again."""
    facts = [_word(session.slots[k].value) for k in session.learned if k in ("district", "sector")]
    facts += [k.replace("_", " ") for k in session.learned if k not in ("district", "sector")]
    if facts:
        return f"Got it, {', '.join(f for f in facts if f)}."
    return "Sorry, I didn't catch that."


def _word(v: Any) -> str:
    raw = getattr(v, "value", v) if v is not None else ""
    return HUMAN.get(str(raw), str(raw).replace("_", " ").title())


def confirm(session: ElicitationSession, accepted: bool) -> Action:
    """User accepts or rejects the restated objective."""
    if not accepted:
        session.state = SessionState.ELICITING
        return step(session)
    session.state = SessionState.GENERATING
    return Action(
        kind="generate",
        objective=session.objective,
        progress=session.progress(),
        turn=session.turn_no,
        reason="confirmed",
    )


DYN = "dyn:"
MAX_DYNAMIC = 3


def add_dynamic(session: ElicitationSession, question: str, source: str) -> str | None:
    """Queue a question specific to this idea; at most three per session, never twice."""
    q = question.strip()
    if not q or any(d["question"].lower() == q.lower() for d in session.dynamic):
        return None
    if len(session.dynamic) >= MAX_DYNAMIC:
        return None
    key = f"{DYN}{hashlib.sha1(q.lower().encode()).hexdigest()[:8]}"
    session.dynamic.append(
        {"key": key, "question": q, "source": source, "asked": False, "answer": None}
    )
    return key


def _pending_dynamic(session: ElicitationSession) -> dict | None:
    return next(
        (d for d in session.dynamic if not d["asked"] and d["key"] not in session.skipped), None
    )


def skip(session: ElicitationSession, key: str) -> Action:
    """User declines a question. Never ask it again — nagging loses people."""
    session.skip(key)
    session.state = SessionState.ELICITING
    return step(session)


def restate(session: ElicitationSession) -> str:
    """The objective, said back in plain language.

    This is the client's explicit requirement — restate what was understood and
    ask for confirmation, rather than silently proceeding on inference.
    """
    g = lambda k: session.slots[k].value if k in session.slots else None  # noqa: E731

    def word(v: Any) -> str:
        """Human label. Never show a user an internal enum code."""
        raw = getattr(v, "value", v) if v is not None else ""
        return HUMAN.get(str(raw), str(raw).replace("_", " "))

    problem, solution = g("problem"), g("solution")
    # The extractor can land the same span in both slots on a short utterance.
    # Saying it twice makes the restatement read like a machine.
    if solution and problem and str(solution).lower() in str(problem).lower():
        solution = None

    district = word(g("district"))
    problem_txt = str(problem or "")

    # Don't repeat a place the founder already named in their own words.
    say_district = bool(district) and district.lower() not in problem_txt.lower()

    sentences: list[str] = []

    # 1 — the problem, with the beneficiary placed BEFORE the colon so the
    # sentence does not trail a prepositional phrase off a complete clause.
    if problem:
        who = f" for {b}" if (b := g("beneficiary")) else ""
        sentences.append(f"You want to solve a problem{who}: {problem_txt.rstrip('.')}")

    # 2 — the plan. "Your plan is start a unit" is ungrammatical; a bare
    # infinitive needs "to", which the extractor strips along with the cue.
    if solution:
        plan = str(solution).strip()
        if plan.split(" ", 1)[0].lower() in _BARE_INFINITIVES:
            plan = f"to {plan}"
        desc = []
        if sec := g("sector"):
            desc.append(f"a {word(sec)} business")
        if pf := g("product_form"):
            desc.append(word(pf))
        tail = f" — {', '.join(desc)}" if desc else ""
        sentences.append(f"Your plan is {plan}{tail}")

    # 3 — where things stand.
    third = []
    if st := g("stage"):
        where = f" in {district}" if say_district else ""
        third.append(f"You are at the {word(st)} stage{where}")
    elif say_district:
        third.append(f"You would operate from {district}")
    if c := g("capital_band"):
        third.append(f"with about {word(c)} to invest")
    if r := g("funding_route"):
        third.append(f"funded by {word(r)}")
    if third:
        sentences.append(", ".join(third))

    body = ". ".join(s.strip() for s in sentences if s.strip()) or (
        "an idea we have not pinned down yet"
    )

    # Gaps are named, never hidden. A user who ran out of patience deserves to
    # know what we assumed rather than to discover it in a wrong roadmap.
    gaps = sorted(session.missing)
    if gaps:
        pretty = ", ".join(g.replace("_", " ") for g in gaps)
        body += (
            f". I still don't know your {pretty} — I'll use safe defaults and widen the estimates"
        )
    return body + "."


__all__ = [
    "Action",
    "Q_MAX",
    "add_dynamic",
    "confirm",
    "observe",
    "restate",
    "skip",
    "start",
    "step",
]
