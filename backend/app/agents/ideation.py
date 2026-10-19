"""The ideation agent: one conversation that knows what already exists.

Each founder turn (IDEATION-PIPELINE-DESIGN.md §1):

    1. the elicitation engine folds the words into facts, checks that a reply
       answers the question asked, and picks the one question worth asking next;
    2. the language model talks: it calls tools (prior-art scan, registry,
       schemes and incubators, roadmap) and phrases the reply around evidence
       and the engine's question;
    3. the reply streams out sentence by sentence, and every sentence the model
       wrote passes the fact check (grounding.py) before it is spoken.

`turn_stream` yields the events of §1.2 (ack, sentence, tool, evidence, done);
`turn` runs the same stream and returns the final `done` payload.

Which model talks is app/agents/providers.py: Claude when paid for, else the free
Gemini tier, else Ollama on this machine; each failure moves the turn to the next.
Ollama rewords the reply the code built instead of calling tools (too slow and
unreliable on a CPU). With no model at all the same turn runs offline: the scan
runs once the idea is clear, and a templated reply summarises it.
"""

from __future__ import annotations

import contextlib
import functools
import hashlib
import json
import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from app.agents import council, providers
from app.agents.council.seats import CRITERION_WORDS
from app.agents.grounding import NOVELTY_LINE, SentenceSplitter, facts_from, gate, problems
from app.agents.jobs import board
from app.agents.tools import TOOLS, compact_scan, council_brief, run_tool
from app.core.config import get_settings
from app.core.logging import get_logger
from app.elicitation import engine
from app.elicitation.answers import SKIP
from app.elicitation.entry import REGISTRATION
from app.elicitation.session import ElicitationSession, SessionState
from app.elicitation.slots import BY_KEY, EntryMode
from app.models.enums import EntryMode as Door
from app.models.enums import RegSubtype
from app.research import novelty
from app.voice.phrasebook import translation

log = get_logger("ideation_agent")

MAX_TOOL_ROUNDS = 4
# What counts as "the same idea": a change here is a new idea version.
CORE_SLOTS = ("problem", "solution", "product_form", "sector", "beneficiary")
# The founder asking for a judgement: worth convening the panel inside the turn.
OPINION = re.compile(
    r"\b(what do you think|your (honest )?(opinion|view|take)|is (this|it) (a )?good"
    r"|review (it|this|my idea)|check (it )?again|will (this|it) work)\b",
    re.I,
)

SYSTEM = """You are Vanigam's mentor for founders in Tamil Nadu: an experienced, warm
guide who has seen many startups. You talk with {name} about their idea — hardware,
software, a physical product or a service. You are heard, not read: this is a
spoken conversation.

How you sound:
- {language_rule}
- Like a mentor across the table: calm, encouraging, direct about risks. Use
  {name}'s name now and then, not every turn.
- Begin by reflecting what they said in a few words, then one point, then one
  question. Short sentences (under 20 words), one idea each, so they can be
  spoken with natural pauses. Never read out lists or symbols.
- Say numbers as digits; keep scheme names (PMEGP, TANSEED) and technical
  terms (EEG, MVP) as they are, inside any language.

How you work:
- Ground every claim about what exists in tool results. When the idea is clear
  enough to search, call scan_prior_art (pass technical search terms when the
  founder's words are everyday ones, and split the idea into its parts as
  elements). Name the closest papers, trials, projects, patents and local
  startups, and say plainly which sources were not searched and why.
- Never say an idea is new or unique. Say what was found in which sources, and
  what would make this founder's version different.
- Walk the founder through every field the idea touches (the scan's fields and
  discuss questions): technology, users, clinical or field validation,
  regulation, cost, who pays.
- After the scan, call check_novelty with the idea's parts. Share what it finds
  over the next turns, one point per turn: first the statement (what is rare),
  then one way to stand out at a time, always with the reason it gives.
- Use find_domains and support_for for Tamil Nadu schemes and incubators; never
  invent a scheme, amount or deadline.
- When the founder asks what you think, or before the roadmap, call ask_council
  and share its brief in your own words, with its one question.
- Use build_roadmap once they confirm; mention any gates it lists first.
- Only use numbers that appear in tool results or in what the founder said.
  Sentences with other numbers are removed before they are spoken.
- Record facts they state with note_fact.
- Ask at most one question per turn. The question to ask next is: {question}
  Ask it in your own words, unless the founder raised something more urgent.
- Speak simply; the founder may be listening rather than reading and English
  may be their second language. At most three short sentences before the
  question. No tables, no markdown.

Known so far: {known}
"""

# A founder away this long hears where the conversation stopped before anything
# else (task 1.1.4.3); a reload within it just shows the last question.
RESUME_GAP = timedelta(minutes=30)
OPENING_QUESTION = REGISTRATION[RegSubtype.UNREGISTERED].opening


class PendingAction(BaseModel):
    """What the founder is being asked right now (R176): one record for the
    resume preamble, the screen and later choice checks. `options` and
    `idea_version` let a choice among cards or levers (1.1.5, 1.2.4) be
    re-presented and checked against the idea it was offered for."""

    kind: Literal["ask", "confirm", "choose_card", "choose_lever"]
    slot: str | None = None
    question: str | None = None
    options: list[str] = Field(default_factory=list)
    idea_version: str | None = None


def _confirm_question(objective: str | None) -> str:
    return f"Here is what I understood. {objective} Is that right?"


@dataclass
class AgentSession:
    name: str
    elicitation: ElicitationSession
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    user_id: str = "anon"
    messages: list[dict] = field(default_factory=list)
    idea: str = ""
    scan: dict | None = None
    roadmap: dict | None = None
    novelty: dict | None = None
    council: dict | None = None  # the latest review-panel run
    # points already said: "evidence", "statement", "council:<at>", "lever:0", ...
    narrated: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)  # model tokens spent in this session
    language: str | None = None  # ta-IN | en-IN | hi-IN: the founder's last spoken language
    # the founder agreed that their programme may see this session in aggregates
    cohort_consent: bool = False
    pending_slot: str | None = None
    pending: dict | None = None  # a PendingAction: what the founder is being asked
    # The last turn sent with a client_turn_id: its ack, sentences and done payload,
    # saved in the same write as the turn, so a retry replays it instead of running
    # it again (R038).
    last_turn: dict | None = None
    private: bool = False  # search nothing outside Vanigam
    # the Start screen's two answers (app.models.enums values), sent at session
    # start; app/elicitation/entry.py says what they mean (task 1.1.6, R121)
    entry_mode: str | None = None
    reg_subtype: str | None = None
    version: int = 0  # bumped on every save; guards against lost updates
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def idea_version(self) -> str | None:
        slots = self.elicitation.slots
        core = {k: _plain(slots[k].value).strip().lower() for k in CORE_SLOTS if k in slots}
        if not core:
            return None
        return hashlib.sha1(json.dumps(core, sort_keys=True).encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "elicitation": self.elicitation.model_dump(mode="json"),
            "messages": self.messages,
            "idea": self.idea,
            "scan": self.scan,
            "roadmap": self.roadmap,
            "novelty": self.novelty,
            "council": self.council,
            "narrated": self.narrated,
            "usage": self.usage,
            "language": self.language,
            "cohort_consent": self.cohort_consent,
            "pending_slot": self.pending_slot,
            "pending": self.pending,
            "last_turn": self.last_turn,
            "private": self.private,
            "entry_mode": self.entry_mode,
            "reg_subtype": self.reg_subtype,
            "version": self.version,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> AgentSession:
        el = ElicitationSession.model_validate(d["elicitation"])
        for key, sv in el.slots.items():  # JSON stores enum values; restore the members
            enum = BY_KEY[key].enum if key in BY_KEY else None
            if enum is not None and isinstance(sv.value, str):
                with contextlib.suppress(ValueError):
                    sv.value = enum(sv.value)
        s = cls(
            name=d["name"],
            elicitation=el,
            id=d["id"],
            user_id=d.get("user_id", "anon"),
            messages=d.get("messages", []),
            idea=d.get("idea", ""),
            scan=d.get("scan"),
            roadmap=d.get("roadmap"),
            novelty=d.get("novelty"),
            council=d.get("council"),
            narrated=d.get("narrated", []),
            usage=d.get("usage", {}),
            language=d.get("language"),
            cohort_consent=d.get("cohort_consent", False),
            pending_slot=d.get("pending_slot"),
            last_turn=d.get("last_turn"),
            private=d.get("private", False),
            entry_mode=d.get("entry_mode"),
            reg_subtype=d.get("reg_subtype"),
            version=d.get("version", 0),
            updated_at=datetime.fromisoformat(d["updated_at"]),
        )
        # a document saved before `pending` existed: rebuild it from what it kept
        pending = d["pending"] if "pending" in d else _derive_pending(s)
        s.pending = PendingAction.model_validate(pending).model_dump() if pending else None
        return s


def _derive_pending(s: AgentSession) -> dict | None:
    el = s.elicitation
    if s.pending_slot:
        asked = next((t.question for t in reversed(el.turns) if t.question), None)
        question = asked or _question_for(s, s.pending_slot)
        return {"kind": "ask", "slot": s.pending_slot, "question": question}
    if el.state is SessionState.CONFIRMING:
        return {"kind": "confirm", "question": _confirm_question(el.objective)}
    if not el.turns:  # only the greeting so far
        return {"kind": "ask", "question": opening_question(s.reg_subtype)}
    return None


def _pending_for(s: AgentSession, action: engine.Action, question: str) -> dict | None:
    if action.kind not in ("ask", "confirm"):
        return None
    return PendingAction(
        kind=action.kind,
        slot=action.slot if action.kind == "ask" else None,
        question=question or None,
        idea_version=s.idea_version,
    ).model_dump()


def _plain(v: Any) -> str:
    return str(getattr(v, "value", v))


def opening_question(reg_subtype: str | None) -> str:
    """The first question: about the product for a registered founder, about the
    idea otherwise (task 1.1.6)."""
    return REGISTRATION[RegSubtype(reg_subtype)].opening if reg_subtype else OPENING_QUESTION


def new_session(
    name: str | None = None,
    profile: dict | None = None,
    user_id: str = "anon",
    private: bool = False,
    share_with_programme: bool = False,
    entry_mode: Door | None = None,
    reg_subtype: RegSubtype | None = None,
) -> tuple[AgentSession, str]:
    """A new conversation and its greeting.

    The registration subtype sets the opening and a stage floor (entry.py), so a
    registered founder is not asked what the Start screen already said. The
    entry mode is kept; the experience conversation it maps to
    (entry.CONVERSATION_MODE) starts with task 1.1.5.2, so until then every
    session runs the idea conversation."""
    who = (name or "").strip() or "there"
    reg = REGISTRATION[reg_subtype] if reg_subtype else None
    el = engine.start(
        user_id,
        mode=EntryMode.IDEA,
        profile=profile,
        stage_floor=reg.stage_floor if reg else None,
    )
    s = AgentSession(name=who, elicitation=el, user_id=user_id)
    s.private = private
    s.cohort_consent = share_with_programme
    s.entry_mode = entry_mode.value if entry_mode else None
    s.reg_subtype = reg_subtype.value if reg_subtype else None
    opening = opening_question(s.reg_subtype)
    s.pending = PendingAction(kind="ask", question=opening).model_dump()
    lead = f" {reg.lead}" if reg and reg.lead else ""
    shape = (
        " It can be a product, a machine, an app or a service."
        if opening == OPENING_QUESTION
        else ""
    )
    greeting = (
        f"Vanakkam {who}!{lead} {opening}{shape} I will look up what already exists for it,"
        " papers, patents, projects and products, and we will shape it together."
    )
    if private:
        greeting += " You chose private mode, so I will search only Vanigam's own data."
    # The Messages API starts with a user turn; the screen opening stands in for it.
    s.messages += [
        {"role": "user", "content": "(The founder opened the ideation screen.)"},
        {"role": "assistant", "content": greeting},
    ]
    return s, greeting


def snapshot(s: AgentSession, latest: dict | None = None) -> dict:
    """Where the conversation stands: enough for a screen to resume it.

    `latest` holds the board's latest finished results by kind (research,
    council): work that finished while the founder was away shows at once,
    before the next turn takes it in (R143). Reading never changes the session,
    so the resume preamble spends no question.
    """
    latest = latest or {}
    research = latest.get("research") if s.scan is None else None
    scan = s.scan or (research or {}).get("scan")
    nov = s.novelty or (research or {}).get("novelty")
    c = latest.get("council")
    fresh_council = bool(c) and (not s.council or s.council.get("at") != c.get("at"))
    panel = c if fresh_council else s.council
    fresh = [w for w, new in (("the search", research), ("the review panel", fresh_council)) if new]
    said = [
        {"role": m["role"], "text": m["content"]}
        for m in s.messages[1:]
        if isinstance(m.get("content"), str)
    ]
    question = next(
        (t.question for t in reversed(s.elicitation.turns) if t.question), None
    ) or next((m["text"] for m in reversed(said) if m["role"] == "assistant"), None)
    return {
        "session_id": s.id,
        "name": s.name,
        "private": s.private,
        "entry_mode": s.entry_mode,
        "reg_subtype": s.reg_subtype,
        "state": s.elicitation.state.value,
        "pending_slot": s.pending_slot,
        "pending": s.pending,
        "last_question": question,
        "resume": _resume_line(s, question, fresh),
        "transcript": said,
        "known": _known_dict(s),
        "evidence": compact_scan(scan) if scan else None,
        "roadmap": s.roadmap,
        "novelty": nov,
        "council": council_brief(panel) if panel else None,
        "idea_version": s.idea_version,
    }


def _resume_line(s: AgentSession, last_question: str | None, fresh: list[str]) -> str | None:
    """After a long gap: welcome back, what finished meanwhile, then the pending
    question again (task 1.1.4.3). It is the question already asked, so it spends
    nothing: the next reply answers it as before."""
    if datetime.now(UTC) - s.updated_at < RESUME_GAP:
        return None
    parts = ["Welcome back." if s.name == "there" else f"Welcome back, {s.name}."]
    if fresh:
        parts.append(f"While you were away, {' and '.join(fresh)} finished; it is shown below.")
    question = (s.pending or {}).get("question") or last_question
    if question:
        parts += ["Here is where we stopped.", question]
    return " ".join(parts)


def replay(s: AgentSession, client_turn_id: str | None) -> list[dict] | None:
    """The saved events of the last turn, when this is a retry of it (R038): the
    same ack, the same fact-checked sentences and the same done payload, with no
    model call and nothing applied twice. None when it is a new turn."""
    t = s.last_turn
    if not client_turn_id or not t or t.get("client_turn_id") != client_turn_id:
        return None
    return [
        _event("ack", t["ack"]),
        *(_event("sentence", x) for x in t["sentences"]),
        _event("done", {**t["done"], "replayed": True}),
    ]


def _known_dict(s: AgentSession) -> dict:
    # Only what the restatement keeps: a disputed or unknown value is not a fact.
    return {k: str(v) for k, v in s.elicitation.kept().items()}


def _known(s: AgentSession) -> str:
    rows = [f"{k}={v}" for k, v in sorted(_known_dict(s).items())]
    if s.reg_subtype:  # from the Start screen, not a slot (task 1.1.6)
        rows.append(f"registration={REGISTRATION[RegSubtype(s.reg_subtype)].said}")
    return ", ".join(rows) or "nothing yet"


def _action_dict(a: engine.Action) -> dict:
    return {
        "kind": a.kind,
        "slot": a.slot,
        "question": a.question,
        "objective": a.objective,
        "progress": round(a.progress, 2),
    }


def _idea_text(s: AgentSession) -> str:
    slots = s.elicitation.slots
    parts = [_plain(slots[k].value) for k in ("problem", "solution") if k in slots]
    return " ".join(parts) or s.idea


def _facts(s: AgentSession, question: str, *extra: object):
    """Everything this session can back, for the fact check."""
    tool_results = [
        b.get("content")
        for m in s.messages
        if m["role"] == "user" and isinstance(m["content"], list)
        for b in m["content"]
        if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
    founder_said = [
        m["content"] for m in s.messages if m["role"] == "user" and isinstance(m["content"], str)
    ]
    human = [engine.HUMAN.get(v, v) for v in _known_dict(s).values()]
    return facts_from(
        tool_results,
        founder_said,
        human,
        s.elicitation.objective or "",
        compact_scan(s.scan) if s.scan else "",
        s.roadmap or "",
        s.novelty or "",
        council_brief(s.council) if s.council else "",
        question,
        *extra,
    )


# ---- the model, streamed ----------------------------------------------------


LANGUAGE_NAMES = {"ta-IN": "Tamil", "en-IN": "English", "hi-IN": "Hindi"}


def _language_rule(s: AgentSession) -> str:
    """Reply in the founder's language, mixed the way they mix it."""
    name = LANGUAGE_NAMES.get(s.language or "", "")
    if not name or name == "English":
        return (
            "Reply in English, simply. If the founder writes or speaks in Tamil or Hindi,"
            " reply in that language instead."
        )
    return (
        f"The founder is speaking {name}. Reply in {name}, in its own script, the way"
        f" people in Tamil Nadu speak it: if they mix English words into {name}, mix the same"
        " English words back. Do not switch to English unless they do."
    )


def _add_usage(total: dict, use: dict | None) -> None:
    for k, v in (use or {}).items():
        if isinstance(v, int):
            total[k] = total.get(k, 0) + v


def _spent(s: AgentSession) -> int:
    u = s.usage
    return sum(
        u.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens")
    )


def _budget_left(s: AgentSession) -> bool:
    budget = get_settings().session_token_budget
    return not (budget and _spent(s) >= budget)


def _model_allowed(s: AgentSession) -> bool:
    """A model talks only when one is configured, its breaker closed, and budget left."""
    return _budget_left(s) and bool(providers.chain())


def _council_work(s: AgentSession):
    """The panel's work on a snapshot of the session (a job never touches it)."""
    idea, known, scan, nov = _idea_text(s), _known_dict(s), s.scan, s.novelty
    use_model = _budget_left(s) and providers.judge() is not None

    async def work() -> dict:
        return await council.convene(idea, known, scan=scan, novelty=nov, use_model=use_model)

    return work


def _research_work(s: AgentSession, args: dict | None = None):
    """The prior-art search and novelty check, on a snapshot. `args` are a model's
    own search terms (its scan_prior_art call); without them, the founder's words.
    The job has its own HTTP client: the turn's closes when the turn ends."""
    args = args or {}
    idea = args.get("idea") or _idea_text(s)
    elements, queries = args.get("elements"), args.get("queries")
    private, who = s.private, _slot_text(s, "beneficiary")

    async def work() -> dict:
        from app.research.scan import scan

        async with httpx.AsyncClient(timeout=60) as c:
            if elements or queries:
                found = await scan(
                    idea, elements=elements, queries=queries, client=c, private=private
                )
            else:
                found = await scan(idea, client=c, private=private)
            nov = await novelty.check(
                idea, elements=elements, scan=found, beneficiary=who, client=c, private=private
            )
        return {"scan": found, "novelty": nov}

    return work


async def _search(s: AgentSession, args: dict) -> dict | None:
    """A model's scan_prior_art call, on the job board: the result if it finishes
    within the turn's wait, else None (it enters a later turn)."""
    job = board.start(s.id, "research", _research_work(s, args), reuse_done=True)
    if not await board.wait(job, get_settings().research_wait_s):
        s.narrated.append("searching")
        return None
    return job.task.result()


def _apply_council(s: AgentSession, r: dict) -> None:
    s.council = r
    _add_usage(s.usage, r.get("usage"))
    if q := r["synthesis"].get("question"):
        engine.add_dynamic(s.elicitation, q, "review panel")


async def _convene(s: AgentSession, wait: float | None = None) -> dict | None:
    """Run the review panel and wait for it up to `wait` seconds (default: the
    founder asked, or the roadmap needs it). None if it is still deliberating:
    its view then enters a later turn."""
    wait = get_settings().opinion_wait_s if wait is None else wait
    job = board.running(s.id, "council") or board.start(s.id, "council", _council_work(s))
    if not await board.wait(job, wait):
        return None
    r = job.task.result()
    if not s.council or s.council.get("at") != r.get("at"):
        _apply_council(s, r)
    return s.council


async def _absorb(s: AgentSession, out: dict) -> list[dict]:
    """Take in background results that finished since the last turn (or within
    this turn's wait): research first, then the panel. Returns the events."""
    evs: list[dict] = []
    if s.scan is None and (r := await board.take(s.id, "research")):
        s.scan, s.novelty = r["scan"], r["novelty"]
        out["fresh"] = s.scan
        out["tools"] += ["scan_prior_art", "check_novelty"]
        out.setdefault("news", []).append(
            "The prior-art search you started has finished: "
            + json.dumps(compact_scan(s.scan), default=str)
            + " Novelty: "
            + json.dumps(s.novelty.get("statement"), default=str)
        )
        evs += [
            _event("tool", {"name": "scan_prior_art", "status": "done"}),
            _event("evidence", compact_scan(s.scan)),
            _event("tool", {"name": "check_novelty", "status": "done"}),
            _event("novelty", s.novelty),
        ]
        # the panel follows on its own; rule seats finish within the wait
        job = board.start(s.id, "council", _council_work(s))
        await board.wait(job, get_settings().council_wait_s)
    c = await board.take(s.id, "council")
    if c and s.scan is not None and (not s.council or s.council.get("at") != c.get("at")):
        _apply_council(s, c)
        out["tools"].append("ask_council")
        evs.append(_event("council", council_brief(s.council)))
        out.setdefault("news", []).append(
            "The review panel has finished: " + json.dumps(council_brief(s.council), default=str)
        )
    return evs


SEARCHING = "Let me look up what already exists for this; I will tell you what I find."
PANEL_BUSY = "The review panel is still looking at it; I will share its view next."


def _event(kind: str, data: Any) -> dict:
    return {"event": kind, "data": data}


class _Gate:
    """Every sentence a model wrote passes the fact check before it is spoken."""

    def __init__(self, out: dict, facts) -> None:
        self.out, self.facts, self.caveat_said = out, facts, False

    def __call__(self, sentence: str) -> dict | None:
        said = gate(sentence, self.facts)
        if said is None:
            self.out["dropped"].append(
                {"sentence": sentence, "why": problems(sentence, self.facts)}
            )
            log.info("grounding.dropped", sentence=sentence)
            return None
        if said == NOVELTY_LINE:
            if self.caveat_said:
                return None
            self.caveat_said = True
        self.out["spoken"].append(said)
        return _event("sentence", said)


async def _llm_stream(
    s: AgentSession,
    question: str,
    client: httpx.AsyncClient,
    out: dict,
    provider: providers.Provider,
) -> AsyncIterator[dict]:
    system = SYSTEM.format(
        name=s.name, question=question, known=_known(s), language_rule=_language_rule(s)
    )
    if out.get("news"):  # finished in the background since the last turn
        system += (
            "\nNew since your last reply (share the main point in a sentence or two;"
            " do not run these tools again):\n" + "\n".join(out["news"])
        )
    state: dict = {
        "private": s.private,
        "last_scan": s.scan,
        "council": s.council,
        "convene": lambda idea: _convene(s),  # None while it is still deliberating
        "search": lambda args: _search(s, args),  # None while it is still searching
    }
    had_council = s.council
    speak = _Gate(out, _facts(s, question))
    splitter = SentenceSplitter()

    for _ in range(MAX_TOOL_ROUNDS + 1):
        content, stop, extra = [], None, {}
        async for kind, payload in provider.stream(client, system, s.messages, TOOLS, out["usage"]):
            if kind == "text":
                for sentence in splitter.feed(payload):
                    if ev := speak(sentence):
                        yield ev
            else:
                content, stop, extra = payload
        s.messages.append({"role": "assistant", "content": content, **extra})
        calls = [b for b in content if b.get("type") == "tool_use"]
        if stop != "tool_use" or not calls:
            break
        for sentence in splitter.flush():  # "Let me look that up." before the tools run
            if ev := speak(sentence):
                yield ev
        results = []
        for c in calls:
            yield _event("tool", {"name": c["name"], "status": "started"})
            res = await run_tool(c["name"], c.get("input") or {}, s.elicitation, state)
            out["tools"].append(c["name"])
            yield _event("tool", {"name": c["name"], "status": "done"})
            results.append(
                {"type": "tool_result", "tool_use_id": c["id"], "content": json.dumps(res)}
            )
        s.messages.append({"role": "user", "content": results})
        if "scan" in state:
            s.scan = state.pop("scan")
            yield _event("evidence", compact_scan(s.scan))
        if "roadmap" in state:
            s.roadmap = state.pop("roadmap")
        if "novelty" in state:
            s.novelty = state.pop("novelty")
            yield _event("novelty", s.novelty)
        if s.council is not had_council:
            had_council = state["council"] = s.council
            yield _event("council", council_brief(s.council))
        speak.facts = _facts(s, question)  # new tool results can now be cited
    for sentence in splitter.flush():
        if ev := speak(sentence):
            yield ev
    if not out["spoken"] and question:  # every sentence failed the check
        out["spoken"].append(question)
        yield _event("sentence", question)


# ---- offline ----------------------------------------------------------------


def _slot_text(s: AgentSession, key: str) -> str | None:
    v = s.elicitation.slots.get(key)
    return _plain(v.value) if v else None


def _next_novelty_point(s: AgentSession) -> str | None:
    """One novelty point per turn: the statement first, then each way to stand out."""
    if not s.novelty:
        return None
    if "statement" not in s.narrated:
        s.narrated.append("statement")
        st = s.novelty["statement"]
        if st["type"] != "unclear":  # "I can't judge novelty yet" is not worth a turn
            return st["text"] + " That is only what I found in the sources I searched."
    if s.council and (key := f"council:{s.council['at']}") not in s.narrated:
        s.narrated.append(key)
        return " ".join(s.council["synthesis"]["voice_brief"])
    for i, lever in enumerate(s.novelty.get("levers", [])[:3]):
        if f"lever:{i}" not in s.narrated:
            s.narrated.append(f"lever:{i}")
            first = "One way to stand out" if i == 0 else "Another way to stand out"
            text = lever["text"].rstrip(".")
            return f"{first}: {text[:1].lower()}{text[1:]}, because {lever['because']}."
    return None


def _count(n: int, noun: str) -> str:
    """1 clinical trial, 23 clinical trials, 34,463 research papers."""
    return f"{n:,} {noun}" + ("" if n == 1 else "s")


def _fallback_reply(scan: dict | None, question: str | None, lead: str | None = None) -> str:
    """Plain-words summary of a fresh scan, used when no language model is configured."""
    parts: list[str] = []
    # Turn grammar: acknowledge, then one evidence point, then the question.
    if question and question.startswith(("Got it,", "Sorry,")) and ". " in question:
        ack, question = question.split(". ", 1)
        parts.append(ack + ".")
    if lead:
        parts.append(lead)
    c = compact_scan(scan) if scan else None
    if c:
        fields = [f["name"] for f in c["fields"][:4]]
        if fields:
            parts.append(f"Your idea touches {', '.join(fields)}.")
        if c["trials"]["total"]:
            t = c["trials"]["items"][0]
            parts.append(
                f"I found {_count(c['trials']['total'], 'clinical trial')}, for example"
                f" \"{t['title']}\"."
            )
        if c["projects"]["total"]:
            g = c["projects"]["items"][0]
            parts.append(
                f"I found {_count(c['projects']['total'], 'open-source project')}, such as"
                f" {g['name']}."
            )
        if c["papers"]["total"]:
            p = c["papers"]["most_relevant"][0]
            parts.append(
                f"About {_count(c['papers']['total'], 'research paper')}, the closest being"
                f" \"{p['title']}\" ({p['year']})."
            )
        if c["patents"]["total"]:
            line = f"{_count(c['patents']['total'], 'related patent')} came up"
            india = c["patents"].get("india")
            if india is not None:
                n = india["total"]
                line += (
                    ", none of them filed in India"
                    if not n
                    else (
                        f", {n:,} of them filed in India" if n > 1 else ", 1 of them filed in India"
                    )
                )
            parts.append(line + ".")
        if c["local"]["startups"]:
            names = ", ".join(x["name"] for x in c["local"]["startups"][:3])
            parts.append(f"In Tamil Nadu, {names} work in this space.")
        cov = c["coverage"]
        if any(x["status"] == "private" for x in cov):
            parts.append("You chose private mode, so I searched only Vanigam's own data.")
        else:
            missing = [  # not searched is never "nothing found"
                x["source"]
                for x in cov
                if x["status"] not in ("ok", "skipped") or x["note"].startswith("Not searched")
            ]
            if missing:
                parts.append(f"I could not search {', '.join(missing)} this time.")
        firsts = [d["questions"][0] for d in c["discuss"][:2]]
        if firsts:
            parts.append("Things to think through: " + " ".join(firsts))
    if question:
        parts.append(question)
    return " ".join(parts) or "Tell me a little more about the idea."


async def _offline_stream(
    s: AgentSession, action: engine.Action, question: str, client: httpx.AsyncClient, out: dict
) -> AsyncIterator[dict]:
    idea = _idea_text(s)
    lead = None
    if s.scan is None and len(idea) >= 20:
        job = board.start(s.id, "research", _research_work(s), reuse_done=True)
        if "searching" not in s.narrated:
            yield _event("tool", {"name": "scan_prior_art", "status": "started"})
            yield _event("tool", {"name": "check_novelty", "status": "started"})
        if await board.wait(job, get_settings().research_wait_s):
            for ev in await _absorb(s, out):
                yield ev
        elif "searching" not in s.narrated:  # still searching: say so once, ask on
            s.narrated.append("searching")
            lead = SEARCHING
    fresh = out.get("fresh")
    if out.get("wants_opinion") and fresh is None:
        before = s.council
        if await _convene(s) is None:  # asked for: worth a wait, but not forever
            lead = PANEL_BUSY
        else:
            out["tools"].append("ask_council")
            yield _event("council", council_brief(s.council))
            s.narrated.append(f"council:{s.council['at']}")
            if before and _same_view(before, s.council):
                lead = _unchanged_line(s.council)
            else:
                lead = " ".join(s.council["synthesis"]["voice_brief"])
    if action.kind == "generate":
        if s.roadmap is None:
            if s.council is None and await _convene(s) is not None:
                out["tools"].append("ask_council")
            state: dict = {"council": s.council}
            await run_tool("build_roadmap", {"idea": idea}, s.elicitation, state)
            s.roadmap = state["roadmap"]
            out["tools"].append("build_roadmap")
        question = _roadmap_line(s.roadmap)
    if lead is None and fresh is None and action.kind == "ask" and action.slot:
        lead = _next_novelty_point(s)
    reply = _fallback_reply(fresh, question, lead)  # templated from the session: no fact check
    s.messages.append({"role": "assistant", "content": reply})
    splitter = SentenceSplitter()
    for sentence in splitter.feed(reply) + splitter.flush():
        out["spoken"].append(sentence)
        yield _event("sentence", sentence)


REWORD = """You are Vanigam's mentor for founders in Tamil Nadu: an experienced, warm
guide, speaking with {name}.

- {language_rule}
- {script}
- You are given ONE sentence you are about to say. Say it again as one sentence:
  the same meaning, in calm, warm spoken words.
- Write every number in digits, exactly as given (3,467, not three thousand...).
- Keep every fact, name, title and number exactly as written. Add nothing: no
  praise, no opinion, no greeting, no extra question.
- If it is a question, keep it a question.
- Never add a translation, a transliteration or anything in brackets.
- Start with the substance: no lead-in such as "Let's revisit", "Well" or "So".
- Reply with that one sentence only.
"""

SCRIPTS = {"ta-IN": ("Tamil", "஀-௿"), "hi-IN": ("Hindi", "ऀ-ॿ")}
BRACKETS = re.compile(r"\s*[(\[][^)\]]*[)\]]")
# a bracket the sentence splitter cut in two: "… (Nallaa." and "kaavileen.) That's …"
OPEN_TAIL = re.compile(r"\s*[(\[][^)\]]*$")
CLOSE_HEAD = re.compile(r"^[^(\[]*[)\]]")
QUOTES = "\"'“”‘’"
# Large figures written out ("three thousand", "forty lakh"): the fact check reads
# digits, so a reworded sentence may not turn digits into these words.
NUMBER_WORDS = re.compile(
    r"\b(hundred|thousand|lakh|lakhs|crore|crores|million|billion)\b"
    r"|ஆயிரம்|லட்சம்|கோடி|हज़ार|हजार|लाख|करोड़",
    re.I,
)


@functools.cache
def _fixed_sentences() -> frozenset[str]:
    """Sentences that never change (the greeting, the questions, the templates that
    recur): in English they are said as written, without a call to the model."""
    from app.voice.phrasebook import wanted

    texts = {r["text"] for r in wanted() if r["language"] == "en-IN"}
    return frozenset(texts | {SEARCHING, PANEL_BUSY})


def _script_rule(s: AgentSession) -> str:
    if s.language in SCRIPTS:
        name = SCRIPTS[s.language][0]
        return f"Write in {name} script only; English words the founder used may stay as they are."
    return "Write in English."


def _plain_words(sentence: str, language: str | None) -> str:
    """What a small model adds that is not for speaking: the whole sentence in
    quotes; and in Tamil or Hindi, bracketed transliterations and translations,
    and sentences repeated in English. (English keeps its brackets: "(2020)".)"""
    sentence = sentence.strip()
    if len(sentence) > 2 and sentence[0] in QUOTES and sentence[-1] in QUOTES:
        sentence = sentence[1:-1].strip()
    if language not in SCRIPTS:
        return sentence
    sentence = CLOSE_HEAD.sub("", OPEN_TAIL.sub("", BRACKETS.sub("", sentence))).strip()
    return sentence if re.search(f"[{SCRIPTS[language][1]}]", sentence) else ""


async def _reword_stream(
    s: AgentSession,
    action: engine.Action,
    question: str,
    client: httpx.AsyncClient,
    out: dict,
    provider: providers.Provider,
) -> AsyncIterator[dict]:
    """The offline turn (scan, novelty, panel, roadmap: all code), each sentence of
    its reply reworded by the model, one at a time: a small model given one
    sentence cannot add lines or lose the question. A sentence it garbles, or that
    fails the fact check, is said as the code wrote it; so is the rest of the reply
    if the model stops answering."""
    async for ev in _offline_stream(s, action, question, client, out):
        if ev["event"] != "sentence":
            yield ev
    draft = s.messages.pop()["content"]
    built = out["spoken"][:]
    out["spoken"].clear()
    speak = _Gate(out, _facts(s, question, draft))
    system = REWORD.format(name=s.name, language_rule=_language_rule(s), script=_script_rule(s))
    reworded, working = 0, True
    english = s.language in (None, "en-IN")
    for line in built:
        said = None
        if english and line in _fixed_sentences():  # already in the mentor's words
            out["spoken"].append(line)
            yield _event("sentence", line)
            continue
        if not english and (written := translation(line, s.language or "")):
            out["spoken"].append(written)  # written once in Tamil or Hindi: no model needed
            yield _event("sentence", written)
            reworded += 1
            continue
        if working:
            try:
                said = await _reword_one(provider, client, system, line, out["usage"])
            except (httpx.HTTPError, RuntimeError, json.JSONDecodeError) as exc:
                provider.breaker.fail(type(exc).__name__)
                log.warning("model.reword_failed", provider=provider.name, error=type(exc).__name__)
                working = False
        said = _plain_words(said or "", s.language)
        if said and NUMBER_WORDS.search(said) and not NUMBER_WORDS.search(line):
            said = ""  # a figure in words would slip past the fact check: keep the digits
        if said and (ev := speak(said)):
            reworded += 1
            yield ev
        else:  # garbled, empty or not backed: the code's own sentence
            out["spoken"].append(line)
            yield _event("sentence", line)
    if working:
        provider.breaker.succeed()
    if reworded:
        out["model"], out["provider"] = "model", provider.name
    elif not working:
        out["model"] = "offline (model failed)"
    # else: every sentence was fixed, or none of the rewording passed: the code's reply
    s.messages.append({"role": "assistant", "content": " ".join(out["spoken"])})


async def _reword_one(
    provider: providers.Provider,
    client: httpx.AsyncClient,
    system: str,
    line: str,
    usage: dict,
) -> str:
    """The model's first sentence for this line; the stream is closed right after,
    so a model that runs on costs no more time."""
    splitter = SentenceSplitter()
    async for kind, payload in provider.stream(
        client, system, [{"role": "user", "content": line}], None, usage
    ):
        if kind == "text" and (done := splitter.feed(payload)):
            return done[0]
    rest = splitter.flush()
    return rest[0] if rest else ""


# ---- the turn -----------------------------------------------------------------


def _advance(s: AgentSession, text: str) -> engine.Action:
    """Fold the words into the elicitation engine; a reply to the restatement is
    read for corrections first, then for its yes or no (engine.reply)."""
    if s.elicitation.state is SessionState.CONFIRMING:
        return engine.reply(s.elicitation, text)
    if s.elicitation.state is SessionState.GENERATING:
        return engine.Action(kind="generate", objective=s.elicitation.objective, progress=1.0)
    if s.pending_slot and SKIP.match(text):
        s.elicitation.record(user_text=text, asked=s.pending_slot)
        return engine.skip(s.elicitation, s.pending_slot)
    if OPINION.search(text):  # a request for a view, not an answer: no miss counted
        engine.observe(s.elicitation, text)
        if s.pending_slot:  # keep the open question open, and ask it again after the view
            return engine.Action(
                kind="ask",
                slot=s.pending_slot,
                question=_question_for(s, s.pending_slot),
                progress=s.elicitation.progress(),
                turn=s.elicitation.turn_no,
                reason="repeat: the founder asked for a view instead of answering",
            )
        return engine.step(s.elicitation)
    engine.observe(s.elicitation, text, answering=s.pending_slot)
    return engine.step(s.elicitation)


def _question_for(s: AgentSession, slot: str) -> str:
    if slot.startswith(engine.DYN):
        return next((d["question"] for d in s.elicitation.dynamic if d["key"] == slot), "")
    return BY_KEY[slot].question if slot in BY_KEY else ""


def _same_view(a: dict, b: dict) -> bool:
    keys = ("band", "stances", "blockers")
    return all(a["vote"][k] == b["vote"][k] for k in keys) and (
        [v["text"] for v in a["vote"]["variants"]] == [v["text"] for v in b["vote"]["variants"]]
    )


def _unchanged_line(r: dict) -> str:
    """Said when the founder asks again and nothing new has changed the panel's view."""
    v = r["vote"]
    line = f"My view hasn't changed since we last looked: the picture is {v['band']}"
    if v["blockers"]:
        return line + ", and the biggest concern still stands."
    crit = v["criteria"]
    if crit:
        worst = min(crit, key=lambda c: crit[c]["score"])
        return line + f", and the weakest point is still {CRITERION_WORDS[worst]}."
    return line + "."


def _roadmap_line(r: dict) -> str:
    ms = r.get("milestones") or []
    first = ", then ".join(m["title"] for m in ms[:3])
    months = r.get("months_realistic")
    return (
        f"Your roadmap has {len(ms)} milestones over about {months} months. It starts with"
        f" {first}. Shall we go through the costs or the licences first?"
    )


async def turn_stream(
    s: AgentSession,
    text: str,
    *,
    client: httpx.AsyncClient | None = None,
    language: str | None = None,
    client_turn_id: str | None = None,
) -> AsyncIterator[dict]:
    """One founder turn as events: ack, sentence…, tool, evidence, done.

    `language` is the founder's language for this turn (from speech recognition or
    their choice); the reply comes back in it when a model is available.
    `client_turn_id` names the turn so a retry of it can be replayed (`replay`).
    """
    s.updated_at = datetime.now(UTC)
    if language in LANGUAGE_NAMES:
        s.language = language
    s.idea = s.idea or text
    action = _advance(s, text)
    s.pending_slot = action.slot if action.kind == "ask" else None
    if action.kind == "confirm":
        question = _confirm_question(action.objective)
    elif action.kind == "generate":
        question = "They confirmed: build the roadmap now and walk them through it."
    else:
        question = action.question or ""
    if action.kind == "ask" and s.elicitation.turns:
        s.elicitation.turns[-1].question = question  # so a resumed session can repeat it
    s.pending = _pending_for(s, action, question)
    ack = {
        "session_id": s.id,
        "action": _action_dict(action),
        # so the voice can start speaking the first sentence in the right language
        "reply_language": (s.language or "en-IN") if _model_allowed(s) else "en-IN",
    }
    yield _event("ack", ack)

    s.messages.append({"role": "user", "content": text})
    out: dict = {
        "fresh": None,
        "spoken": [],
        "dropped": [],
        "tools": [],
        "usage": {},
        "wants_opinion": bool(OPINION.search(text)),
        "model": "offline",
        "provider": None,
    }
    own = client is None
    client = client or httpx.AsyncClient(timeout=120)
    try:
        for ev in await _absorb(s, out):  # background work finished since the last turn
            yield ev
        failed = []
        for p in providers.chain() if _budget_left(s) else []:
            if not p.tools:  # rewords the code's reply; handles its own failure
                async for ev in _reword_stream(s, action, question, client, out, p):
                    yield ev
                break
            mark = len(s.messages)
            try:
                async for ev in _llm_stream(s, question, client, out, p):
                    yield ev
                p.breaker.succeed()
                out["model"], out["provider"] = "model", p.name
                break
            except (httpx.HTTPError, RuntimeError, json.JSONDecodeError) as exc:
                # This model failed: the breaker decides whether to skip it for a
                # while, and the turn moves to the next provider.
                p.breaker.fail(type(exc).__name__)
                log.warning("model.failed", provider=p.name, error=type(exc).__name__)
                del s.messages[mark:]  # drop the half-finished exchange
                failed.append(p.name)
                if out["spoken"]:  # already heard part of it: do not start over
                    out["model"] = "model (cut short)"
                    break
        else:
            out["model"] = "offline (model failed)" if failed else "offline"
            async for ev in _offline_stream(s, action, question, client, out):
                yield ev
    finally:
        if own:
            await client.aclose()
        _add_usage(s.usage, out["usage"])

    done = {
        "session_id": s.id,
        "reply": " ".join(out["spoken"]),
        "action": _action_dict(action),
        "tools_used": out["tools"],
        "dropped": len(out["dropped"]),
        "evidence": compact_scan(s.scan) if s.scan else None,
        "roadmap": s.roadmap,
        "novelty": s.novelty,
        "council": council_brief(s.council) if s.council else None,
        "model": out["model"],
        "provider": out["provider"],
        # the language the reply was written in: offline templates are English only
        "language": (s.language or "en-IN") if out["model"] == "model" else "en-IN",
        "usage": s.usage,
        "known": _known_dict(s),
        "idea_version": s.idea_version,
    }
    # saved with the turn (the caller saves on `done`); a turn without an id
    # forgets the last one, so an old id can never replay a stale reply
    s.last_turn = (
        {"client_turn_id": client_turn_id, "ack": ack, "sentences": out["spoken"][:], "done": done}
        if client_turn_id
        else None
    )
    yield _event("done", done)


async def turn(
    s: AgentSession,
    text: str,
    *,
    client: httpx.AsyncClient | None = None,
    language: str | None = None,
    client_turn_id: str | None = None,
) -> dict:
    """The same turn, collected: returns the `done` payload."""
    done: dict = {}
    async for ev in turn_stream(
        s, text, client=client, language=language, client_turn_id=client_turn_id
    ):
        if ev["event"] == "done":
            done = ev["data"]
    return done


__all__ = ["AgentSession", "new_session", "replay", "snapshot", "turn", "turn_stream"]
