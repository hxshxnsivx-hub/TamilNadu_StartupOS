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
import re
from dataclasses import dataclass
from typing import Any, Literal

from app.core.stages import ORDER as STAGE_ORDER
from app.core.stages import Stage
from app.elicitation.answers import coerce, validate
from app.elicitation.confirmation import (
    after_cue,
    anchored,
    corrections,
    has_cue,
    named,
    named_values,
    polarity,
    strip_negated,
)
from app.elicitation.extract import extract
from app.elicitation.selector import (
    Q_MAX,
    is_objective_clear,
    next_question,
    question_budget,
)
from app.elicitation.session import (
    FOUNDER_GIVEN,
    ElicitationSession,
    SessionState,
    Source,
)
from app.elicitation.slots import (
    BY_KEY,
    REQUIRED_BY_MODE,
    SLOTS,
    TAU_FILL,
    Band,
    EntryMode,
    Finger,
)

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
# corrosive thing this feature could do. Because they are never asked again,
# each value passes the same slot rules as a spoken answer first (R019); one
# that fits no slot is left for the conversation to ask.
PROFILE_SLOTS = (
    "district",
    "founder_years",
    "founder_skills",
    "owned_assets",
    "sector",
    "stage",
)

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
    stage_floor: Stage | None = None,
) -> ElicitationSession:
    """Open a session, pre-filling anything the profile already knows.

    `stage_floor` is the lowest stage the founder's registration implies
    (entry.REGISTRATION, task 1.1.6). With no profile stage, or one below it
    (the two disagree), the floor is held in the confirm band: not asked, said
    back as an assumption at the restatement."""
    s = ElicitationSession(user_id=user_id, mode=mode)
    for key in PROFILE_SLOTS:
        value = _from_profile(key, (profile or {}).get(key))
        if key == "stage" and stage_floor is not None and _below(value, stage_floor):
            value = None
        if value is not None:
            s.put(key, value, 0.95, Source.PROFILE)
    if stage_floor is not None and "stage" not in s.slots:
        s.put("stage", stage_floor.value, ASSUMED_CONFIDENCE, Source.DEFAULT)
    s.state = SessionState.ELICITING
    return s


# Inside the confirm band (slots.TAU_CONFIRM to TAU_FILL): kept and said back as
# "I assumed", never asked.
ASSUMED_CONFIDENCE = 0.55


def _below(stage: str | None, floor: Stage) -> bool:
    return stage is None or STAGE_ORDER.index(Stage(stage)) < STAGE_ORDER.index(floor)


def _from_profile(key: str, raw: Any) -> Any | None:
    """The typed slot value for a profile field, or None when it fits no slot.
    The same gate as every other source (answers.coerce): the stage picks from
    the shared list (app/core/stages.py), the rest pass the slot's answer rules."""
    if isinstance(raw, int) and not isinstance(raw, bool) and BY_KEY[key].kind != "int":
        raw = str(raw)
    return coerce(key, raw)


# A correction said in passing, mid-conversation (R063): "sorry, actually I am
# in Salem, not Erode". A fact it states that differs from the one held is the
# founder's answer, not an inference that loses to the earlier answer.
_CORRECTION = re.compile(
    r"\b(?:actually|sorry|i mean|i meant|correction|instead|moved|shifted|relocated)\b"
    r"|\bnot\s+\w+(?:\s+\w+)?\s*,?\s*but\b",
    re.I,
)


def observe(session: ElicitationSession, text: str, *, answering: str | None = None) -> None:
    """Fold a user utterance into the slots.

    `answering` names the slot we asked about, so a direct reply is recorded
    as an ANSWER (which outranks any earlier extraction) even when the free-text
    extractor cannot parse it.

    A reply that answered a free-text question fills no other free-text slot:
    the founder's words about who it is for are not a new problem (the 1.1.2
    review). A reply with a correction word ("sorry, actually I am in Salem")
    states the founder's answer for each fact it changes (R063).
    """
    session.state = SessionState.EXTRACTING
    session.learned = []
    answered_text = False

    if answering and answering.startswith(DYN) and text.strip():
        for d in session.dynamic:  # free text: the founder's own answer, kept as said
            if d["key"] == answering:
                d["answer"] = text.strip()
    elif answering and answering in BY_KEY and text.strip():
        value = validate(answering, text)
        if value is not None:
            session.put(answering, value, 0.90, Source.ANSWER)
            session.reask = None
            answered_text = BY_KEY[answering].kind == "text"
        else:
            # Not an answer to this question ("Chennai" for the stage). Never
            # store it there; let the extractor place it, and ask once more.
            misses = session.mismatches.get(answering, 0) + 1
            session.mismatches[answering] = misses
            session.reask = answering if misses < 2 else None
            if misses >= 2:
                session.skip(answering)

    correcting = bool(_CORRECTION.search(text))
    for e in extract(strip_negated(text) if correcting else text):
        # Never let an extraction overwrite the direct answer we just stored.
        if e.key == answering or (answered_text and BY_KEY[e.key].kind == "text"):
            continue
        was_filled = e.key in session.filled
        held = session.slots.get(e.key)
        if (
            correcting
            and held is not None
            and e.confidence >= TAU_FILL
            and _plain_value(held.value) != _plain_value(e.value)
        ):
            session.put(e.key, e.value, 0.90, Source.ANSWER)
        else:
            session.put(e.key, e.value, e.confidence, Source.EXTRACTED)
        if not was_filled and e.key in session.filled:
            session.learned.append(e.key)

    session.record(user_text=text, asked=answering)
    session.open_question = None  # the founder replied
    session.state = SessionState.ELICITING


def _plain_value(v: Any) -> Any:
    return getattr(v, "value", v)


def _ask(
    session: ElicitationSession, key: str, question: str, reason: str, *, new: bool = True
) -> Action:
    """Ask `key`. A new question uses the budget (R009) unless it is the one
    already waiting for a reply; a re-ask never does."""
    if new and session.open_question != key:
        session.questions_asked += 1
    session.open_question = key
    session.state = SessionState.AWAITING_ANSWER
    return Action(
        kind="ask",
        slot=key,
        question=question,
        progress=session.progress(),
        turn=session.turn_no,
        reason=reason,
    )


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
        return _ask(
            session,
            key,
            f"{_acknowledge(session)} {BY_KEY[key].question}",
            "reask: the reply did not answer the question",
            new=False,
        )

    # 2. Then a question the review panel raised: it marks where the evidence and
    #    the advisers disagree most. It still counts toward the Q_MAX ceiling.
    if (dyn := _pending_dynamic(session)) is not None and session.questions_asked < question_budget(
        session
    ):
        dyn["asked"] = True
        return _ask(session, dyn["key"], dyn["question"], f"dynamic: raised by {dyn['source']}")

    # 3. Otherwise the most valuable unanswered slot.
    if not decision.stop:
        nq = next_question(session)
        if nq is not None:
            key, question = nq
            return _ask(session, key, question, decision.reason)
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
    # The stage itself ("prototype"), not the slot's name; a common noun, so lowercase.
    facts += [
        HUMAN.get(str(session.slots[k].value), str(session.slots[k].value))
        for k in session.learned
        if k == "stage"
    ]
    facts += [
        k.replace("_", " ") for k in session.learned if k not in ("district", "sector", "stage")
    ]
    if facts:
        return f"Got it, {', '.join(f for f in facts if f)}."
    return "Sorry, I didn't catch that."


def _word(v: Any) -> str:
    raw = getattr(v, "value", v) if v is not None else ""
    return HUMAN.get(str(raw), str(raw).replace("_", " ").title())


WHAT_TO_CHANGE = (
    "Which part should I change? Tell me the right fact, for example: the district is Salem."
)


def confirm(session: ElicitationSession, accepted: bool) -> Action:
    """User accepts or rejects the restated objective.

    A rejection that names no correction asks what to change and stays at
    confirmation, so the next reply is read as the correction (`reply`).
    Re-opening questioning used to land straight back on the same restatement.
    """
    if not accepted:
        session.state = SessionState.CONFIRMING
        session.awaiting_correction = True
        return Action(
            kind="ask",
            question=WHAT_TO_CHANGE,
            objective=session.objective,
            progress=session.progress(),
            turn=session.turn_no,
            reason="rejected: asking what to change",
        )
    session.state = SessionState.GENERATING
    return Action(
        kind="generate",
        objective=session.objective,
        progress=session.progress(),
        turn=session.turn_no,
        reason="confirmed",
    )


def reply(session: ElicitationSession, text: str) -> Action:
    """The founder's answer to the restatement (R005).

    Always read for facts first, with negated phrases removed ("Salem not
    Madurai" is Salem). A fact that differs from what was restated is a
    correction when the reply is anchored as one: a no, the slot named ("the
    district is Salem"), the fact standing alone right after a correction word
    ("yes, but it's Salem"), or a reply that is mostly the fact. A correction
    is stored as founder-given and locked, one question is given back, and the
    objective is restated. After "which part should I change?" the whole next
    reply counts as a correction. An unanchored fact is an aside ("yes, but my
    wife works in a school"), merged like any extraction, so it never replaces
    what the founder gave (R025): it is kept as a rival instead.

    Only a reply that changed nothing is a plain yes or no, and a yes with a
    correction word that changed nothing asks what to change.

    The reply itself is not a question, so it never uses the budget.
    """
    whole = anchored(text) or session.awaiting_correction
    session.awaiting_correction = False
    names = named(text) | after_cue(text)
    found = corrections(text) + named_values(text)
    session.open_question = None
    session.learned = []
    corrected, moved = [], False
    for e in found:
        value = getattr(e.value, "value", e.value)
        if e.key in session.slots and value == _current(session, e.key):
            continue
        if whole or e.key in names:
            session.put(e.key, e.value, 0.90, Source.ANSWER, correction=True)
            corrected.append(e.key)
        else:
            before = session.slots.get(e.key)
            session.put(e.key, e.value, e.confidence, Source.EXTRACTED)
            moved = moved or session.slots.get(e.key) is not before
    session.learned = corrected
    session.record(user_text=text, asked=None)
    if corrected:
        session.refunds += 1  # a correction gives back one question (task 1.1.2.3)
    if corrected or moved:
        session.state = SessionState.ELICITING
        return step(session)
    said = polarity(text)
    if said is True and not has_cue(text):
        return confirm(session, True)
    if said is not None:  # a no, or "yes, but ..." with nothing we could read
        return confirm(session, False)
    # Neither a yes, a no nor a fact: say the restatement again.
    session.state = SessionState.ELICITING
    return step(session)


def _current(session: ElicitationSession, key: str) -> Any:
    v = session.slots[key].value
    return getattr(v, "value", v)


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
    session.open_question = None
    session.state = SessionState.ELICITING
    return step(session)


# How each source is named when a fact is said back (task 1.1.2.1). Anything not
# founder-given was inferred: from free text, a document or a model's note.
LABELS: tuple[tuple[str, frozenset[Source]], ...] = (
    ("You told me", frozenset({Source.ANSWER})),
    ("From your profile", frozenset({Source.PROFILE})),
    ("I assumed", frozenset(Source) - FOUNDER_GIVEN),
)
ASSUMED_LABEL = LABELS[-1][0]


def _label(session: ElicitationSession, key: str) -> str:
    """A confirm-band value is said as an assumption whatever its source (R157):
    it was not asked, so the founder confirms it here."""
    if session.band(key) is not Band.KNOWN:
        return ASSUMED_LABEL
    source = session.slots[key].source
    return next(label for label, sources in LABELS if source in sources)


# The facts said back under those labels: every slot that is not free text and
# that the roadmap or the scheme match reads (R154), in slot-table order. The
# free-text slots (problem, solution, beneficiary) are said in their own
# sentences, in the founder's words.
RESTATED = tuple(
    s.key for s in SLOTS if s.kind != "text" and {"roadmap", "scheme"} & set(s.consumers)
)

# What a slot is called when it is named as a gap.
NAMES: dict[str, str] = {
    "product_form": "product type",
    "capital_band": "budget",
    "funding_route": "funding",
    "why_now": "reason for doing this now",
}
# The slot named as the gap when the WHY finger is still open (R113).
WHY_GAP = "why_now"

# What the plan uses when a required slot has no value (R051), so the founder
# hears the real default rather than "safe defaults". Each matches
# app/planner: stage falls to the first stage (roadmap.applicable), an empty
# district counts as Tamil Nadu (plan.build_plan), sector and product form
# come from the domain the idea's words match, and without a budget or route
# the risks keep the domain's own levels (risks.adjusted_levels).
ASSUMED: dict[str, str] = {
    "problem": "the idea as you described it",
    "solution": "the idea as you described it",
    "beneficiary": "the usual buyers for this kind of business",
    "sector": "the sector your idea's words point to",
    "product_form": "the product type your idea's words point to",
    "district": "a place in Tamil Nadu",
    "stage": "you are starting from the idea stage",
    "capital_band": "the usual budget for this kind of business",
    "funding_route": "no particular way of funding it",
    "why_now": "no particular reason it has to be now",
}

_REACH = {
    "local": "selling locally",
    "district": "selling across your district",
    "state": "selling across Tamil Nadu",
    "national": "selling across India",
    "export": "selling abroad",
}
_HORIZON = {
    "<6mo": "running within 6 months",
    "6-12mo": "running within a year",
    "1-2y": "running within 2 years",
    ">2y": "running in more than 2 years",
}

# The founder's own sentence, said back short (task 1.1.2.2): eval transcripts
# repeated the whole opening sentence as "the problem".
_INTENT = re.compile(
    r"^(?:i|we)\s+(?:want|plan|hope|would like|am planning|are planning|am going|are going)"
    r"\s+to\s+",
    re.I,
)
_PROBLEM_LEAD = re.compile(r"^(?:the\s+)?(?:problem|issue)\s+is\s+(?:that\s+)?", re.I)
_CLAUSE = frozenset(
    {"using", "because", "so", "which", "where", "while", "buying", "through", "since", "who"}
)
_TRAILING = frozenset(
    {"with", "for", "in", "and", "of", "to", "a", "an", "the", "from", "on", "at", "made", "by"}
)
_SHORT_WORDS = 12
_MIN_WORDS = 4  # a clause word this early is part of the subject, not a new clause


def _short(text: Any) -> tuple[str, bool]:
    """(the sentence said short, whether it was an intent: "I want to ...")."""
    t = str(text).strip().rstrip(".")
    intent = bool(_INTENT.match(t))
    t = _INTENT.sub("", t) if intent else _PROBLEM_LEAD.sub("", t)
    words: list[str] = []
    for w in t.split():
        if len(words) >= _MIN_WORDS and w.lower() in _CLAUSE:
            break
        words.append(w)
        if len(words) >= _SHORT_WORDS or (len(words) >= _MIN_WORDS and w[-1] in ",;:"):
            break
    while len(words) > 1 and words[-1].lower().strip(",;:") in _TRAILING:
        words.pop()
    return " ".join(words).rstrip(",;:"), intent


def _join(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"


def _plain(v: Any) -> str:
    """Human label. Never show a user an internal enum code."""
    raw = getattr(v, "value", v) if v is not None else ""
    return HUMAN.get(str(raw), str(raw).replace("_", " "))


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def _count(v: Any) -> int | None:
    try:
        return int(getattr(v, "value", v))
    except (TypeError, ValueError):
        return None  # a model can note "about five"; it is said as written


def _fact(key: str, v: Any) -> str:
    """One restated fact, as a phrase that reads after any label."""
    raw = str(getattr(v, "value", v))
    phrases = {
        "sector": lambda: f"{_article(_plain(v))} {_plain(v)} business",
        "product_form": lambda: _plain(v),
        "district": lambda: f"{_word(v)} district",
        "stage": lambda: f"the {_plain(v)} stage",
        "capital_band": lambda: f"about {_plain(v)} to invest",
        "funding_route": lambda: f"funded by {_plain(v)}",
        "geo_scope": lambda: _REACH.get(raw, f"{_article(_plain(v))} {_plain(v)} reach"),
        "time_horizon": lambda: _HORIZON.get(raw, f"running in {raw}"),
    }
    if key in phrases:
        return phrases[key]()
    n = _count(v)
    if key == "team_size":
        return "working alone" if n == 1 else f"a team of {raw if n is None else n}"
    if key == "founder_years":
        return "1 year in this line" if n == 1 else f"{raw if n is None else n} years in this line"
    listed = _join([str(x) for x in v]) if isinstance(v, list) and v else raw
    if key == "owned_assets":
        return f"you own {listed}"
    if key == "founder_skills":
        return f"skills in {listed}"
    return f"{key.replace('_', ' ')} {_plain(v)}"


def restate(session: ElicitationSession) -> str:
    """The objective, said back in plain language.

    This is the client's explicit requirement — restate what was understood and
    ask for confirmation, rather than silently proceeding on inference. Each
    fact says where it came from, and each gap says what will be assumed.
    """
    g = lambda k: session.slots[k].value if k in session.filled else None  # noqa: E731

    problem, solution = g("problem"), g("solution")
    # The extractor can land the same span in both slots on a short utterance.
    # Saying it twice makes the restatement read like a machine.
    if solution and problem and str(solution).lower() in str(problem).lower():
        solution = None

    sentences: list[str] = []
    said = ""  # the founder's words said back, so a place named in them is not repeated

    # 1 — the problem, short. An intent ("I want to start a unit") is said back
    # as one ("You want to start a unit"); a problem keeps its frame, with the
    # beneficiary BEFORE the colon so the sentence does not trail off a clause.
    b = g("beneficiary")
    if problem:
        short, intent = _short(problem)
        said += short
        if b and (short.lower() in str(b).lower() or str(b).lower() in short.lower()):
            b = None  # the problem already names who it is for: say it once
        if intent:
            sentences.append(f"You want to {short}" + (f", for {b}" if b else ""))
        else:
            who = f" for {b}" if b else ""
            sentences.append(f"You want to solve a problem{who}: {short}")
    elif b:
        sentences.append(f"It is for {b}")

    # 2 — the plan. "Your plan is start a unit" is ungrammatical; a bare
    # infinitive needs "to", which the extractor strips along with the cue.
    if solution:
        plan, _ = _short(solution)
        said += f" {plan}"
        if plan.split(" ", 1)[0].lower() in _BARE_INFINITIVES:
            plan = f"to {plan}"
        sentences.append(f"Your plan is {plan}")

    # 3 — the facts the plan runs on, grouped by where each came from.
    for label, _ in LABELS:
        facts = [
            _fact(key, g(key))
            for key in RESTATED
            if g(key) is not None and _label(session, key) == label
            # the founder already named the place in their own words
            and not (key == "district" and _word(g(key)).lower() in said.lower())
        ]
        if facts:
            sentences.append(f"{label}: {', '.join(facts)}")

    body = ". ".join(s.strip() for s in sentences if s.strip()) or (
        "an idea we have not pinned down yet"
    )

    # Gaps are named, never hidden, each with what will be assumed instead. A
    # user who ran out of patience deserves to know what we assumed rather
    # than to discover it in a wrong roadmap. Skipped and dropped questions
    # are named apart from the ones never asked (R051).
    unfilled = REQUIRED_BY_MODE[session.mode] - session.filled
    order = [s.key for s in SLOTS]
    skipped = sorted(unfilled & session.skipped, key=order.index)
    unknown = sorted(unfilled - session.skipped, key=order.index)
    if Finger.WHY in session.uncovered:
        unknown.append(WHY_GAP)
    if skipped:
        body += f". You skipped your {_gap_names(skipped)}; I will assume {_assumed(skipped)}"
    if unknown:
        body += (
            f". I still don't know your {_gap_names(unknown)}; I will assume"
            f" {_assumed(unknown)}, and widen the estimates"
        )
    return body + "."


def _gap_names(keys: list[str]) -> str:
    return _join([NAMES.get(k, k.replace("_", " ")) for k in keys])


def _assumed(keys: list[str]) -> str:
    return _join(list(dict.fromkeys(ASSUMED.get(k, "a typical value") for k in keys)))


__all__ = [
    "Action",
    "Q_MAX",
    "add_dynamic",
    "confirm",
    "observe",
    "reply",
    "restate",
    "skip",
    "start",
    "step",
]
