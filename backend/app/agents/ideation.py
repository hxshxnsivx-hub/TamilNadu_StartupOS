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

Without an API key the same turn runs offline: the scan runs once the idea is
clear, and a templated reply summarises it.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.agents import council
from app.agents.council.seats import CRITERION_WORDS
from app.agents.grounding import NOVELTY_LINE, SentenceSplitter, facts_from, gate, problems
from app.agents.tools import TOOLS, compact_scan, council_brief, run_tool
from app.core.config import get_settings
from app.core.logging import get_logger
from app.elicitation import engine
from app.elicitation.answers import SKIP
from app.elicitation.session import ElicitationSession, SessionState
from app.elicitation.slots import BY_KEY
from app.research import novelty
from app.services.breaker import model_breaker

log = get_logger("ideation_agent")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MAX_TOOL_ROUNDS = 4
YES = {"yes", "yeah", "yep", "correct", "right", "ok", "okay", "sure", "seri", "aamaa", "aama"}
NO = {"no", "nope", "wrong", "illai", "not"}
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
    pending_slot: str | None = None
    private: bool = False  # search nothing outside Vanigam
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
            "pending_slot": self.pending_slot,
            "private": self.private,
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
        return cls(
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
            pending_slot=d.get("pending_slot"),
            private=d.get("private", False),
            version=d.get("version", 0),
            updated_at=datetime.fromisoformat(d["updated_at"]),
        )


def _plain(v: Any) -> str:
    return str(getattr(v, "value", v))


def new_session(
    name: str | None = None,
    profile: dict | None = None,
    user_id: str = "anon",
    private: bool = False,
) -> tuple[AgentSession, str]:
    who = (name or "").strip() or "there"
    s = AgentSession(name=who, elicitation=engine.start(user_id, profile=profile), user_id=user_id)
    s.private = private
    greeting = (
        f"Vanakkam {who}! Tell me about the idea you are working on, in your own words."
        " It can be a product, a machine, an app or a service. I will look up what already"
        " exists for it, papers, patents, projects and products, and we will shape it together."
    )
    if private:
        greeting += " You chose private mode, so I will search only Vanigam's own data."
    # The Messages API starts with a user turn; the screen opening stands in for it.
    s.messages += [
        {"role": "user", "content": "(The founder opened the ideation screen.)"},
        {"role": "assistant", "content": greeting},
    ]
    return s, greeting


def snapshot(s: AgentSession) -> dict:
    """Where the conversation stands: enough for a screen to resume it."""
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
        "state": s.elicitation.state.value,
        "pending_slot": s.pending_slot,
        "last_question": question,
        "transcript": said,
        "known": _known_dict(s),
        "evidence": compact_scan(s.scan) if s.scan else None,
        "roadmap": s.roadmap,
        "novelty": s.novelty,
        "council": council_brief(s.council) if s.council else None,
        "idea_version": s.idea_version,
    }


def _known_dict(s: AgentSession) -> dict:
    return {k: _plain(v.value) for k, v in s.elicitation.slots.items()}


def _known(s: AgentSession) -> str:
    rows = [f"{k}={v}" for k, v in sorted(_known_dict(s).items())]
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


def _facts(s: AgentSession, question: str):
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
    )


# ---- the model, streamed ----------------------------------------------------


async def _model_events(
    client: httpx.AsyncClient, system: str, messages: list[dict], usage: dict | None = None
) -> AsyncIterator[tuple[str, Any]]:
    """("text", chunk) while streaming, then ("message", (content, stop_reason))."""
    st = get_settings()
    body = {
        "model": st.llm_model_main,
        "max_tokens": 1024,
        "system": system,
        "tools": TOOLS,
        "messages": messages,
        "stream": True,
    }
    headers = {
        "x-api-key": st.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    blocks: dict[int, dict] = {}
    partial_json: dict[int, str] = {}
    stop = None
    async with client.stream("POST", ANTHROPIC_URL, headers=headers, json=body) as r:
        if r.status_code != 200:
            await r.aread()
            r.raise_for_status()
        async for line in r.aiter_lines():
            if not line.startswith("data:"):
                continue
            ev = json.loads(line[5:].strip())
            kind = ev.get("type")
            if usage is not None:
                _add_usage(usage, (ev.get("message") or {}).get("usage") or ev.get("usage"))
            if kind == "content_block_start":
                blocks[ev["index"]] = dict(ev["content_block"])
            elif kind == "content_block_delta":
                i, d = ev["index"], ev["delta"]
                if d.get("type") == "text_delta":
                    blocks[i]["text"] = blocks[i].get("text", "") + d["text"]
                    yield "text", d["text"]
                elif d.get("type") == "input_json_delta":
                    partial_json[i] = partial_json.get(i, "") + d.get("partial_json", "")
            elif kind == "message_delta":
                stop = ev.get("delta", {}).get("stop_reason", stop)
            elif kind == "error":
                raise RuntimeError(ev.get("error", {}).get("message", "model stream error"))
    for i, raw in partial_json.items():
        blocks[i]["input"] = json.loads(raw) if raw.strip() else {}
    content = [blocks[i] for i in sorted(blocks)]
    yield "message", (content, stop)


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


def _model_allowed(s: AgentSession) -> bool:
    """The model is used only with a key, a closed breaker, and budget left."""
    budget = get_settings().session_token_budget
    over = bool(budget) and _spent(s) >= budget
    return bool(get_settings().anthropic_api_key) and model_breaker.allow() and not over


async def _convene(s: AgentSession) -> dict:
    """Run the review panel for the current idea, and queue its question."""
    r = await council.convene(
        _idea_text(s),
        _known_dict(s),
        scan=s.scan,
        novelty=s.novelty,
        use_model=_model_allowed(s),
    )
    s.council = r
    _add_usage(s.usage, r.get("usage"))
    if q := r["synthesis"].get("question"):
        engine.add_dynamic(s.elicitation, q, "review panel")
    return r


def _event(kind: str, data: Any) -> dict:
    return {"event": kind, "data": data}


async def _llm_stream(
    s: AgentSession, question: str, client: httpx.AsyncClient, out: dict
) -> AsyncIterator[dict]:
    system = SYSTEM.format(
        name=s.name, question=question, known=_known(s), language_rule=_language_rule(s)
    )
    state: dict = {
        "private": s.private,
        "last_scan": s.scan,
        "council": s.council,
        "convene": lambda idea: _convene(s),
    }
    had_council = s.council
    facts = _facts(s, question)
    splitter = SentenceSplitter()
    caveat_said = False

    def speak(sentence: str) -> dict | None:
        nonlocal caveat_said
        said = gate(sentence, facts)
        if said is None:
            out["dropped"].append({"sentence": sentence, "why": problems(sentence, facts)})
            log.info("grounding.dropped", sentence=sentence)
            return None
        if said == NOVELTY_LINE:
            if caveat_said:
                return None
            caveat_said = True
        out["spoken"].append(said)
        return _event("sentence", said)

    for _ in range(MAX_TOOL_ROUNDS + 1):
        content, stop = [], None
        async for kind, payload in _model_events(client, system, s.messages, out["usage"]):
            if kind == "text":
                for sentence in splitter.feed(payload):
                    if ev := speak(sentence):
                        yield ev
            else:
                content, stop = payload
        s.messages.append({"role": "assistant", "content": content})
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
        facts = _facts(s, question)  # new tool results can now be cited
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
        caveat = (
            " That is only what I found in the sources I searched."
            if st["type"] != ("unclear")
            else ""
        )
        return st["text"] + caveat
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
                f"I found {c['trials']['total']} clinical trials, for example \"{t['title']}\"."
            )
        if c["projects"]["total"]:
            g = c["projects"]["items"][0]
            parts.append(
                f"There are {c['projects']['total']} open-source projects, such as {g['name']}."
            )
        if c["papers"]["total"]:
            p = c["papers"]["most_relevant"][0]
            parts.append(
                f"About {c['papers']['total']} research papers, the closest being"
                f" \"{p['title']}\" ({p['year']})."
            )
        if c["patents"]["total"]:
            parts.append(f"{c['patents']['total']} related patents came up.")
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
    fresh = None
    if s.scan is None and len(idea) >= 20:
        from app.research.scan import scan

        yield _event("tool", {"name": "scan_prior_art", "status": "started"})
        s.scan = fresh = await scan(idea, client=client, private=s.private)
        out["tools"].append("scan_prior_art")
        yield _event("tool", {"name": "scan_prior_art", "status": "done"})
        yield _event("evidence", compact_scan(s.scan))
        yield _event("tool", {"name": "check_novelty", "status": "started"})
        s.novelty = await novelty.check(
            idea,
            scan=s.scan,
            beneficiary=_slot_text(s, "beneficiary"),
            client=client,
            private=s.private,
        )
        out["tools"].append("check_novelty")
        yield _event("tool", {"name": "check_novelty", "status": "done"})
        yield _event("novelty", s.novelty)
        await _convene(s)
        out["tools"].append("ask_council")
        yield _event("council", council_brief(s.council))
    lead = None
    if out.get("wants_opinion") and fresh is None:
        before = s.council
        await _convene(s)  # asked for: worth the wait
        out["tools"].append("ask_council")
        yield _event("council", council_brief(s.council))
        s.narrated.append(f"council:{s.council['at']}")
        if before and _same_view(before, s.council):
            lead = _unchanged_line(s.council)
        else:
            lead = " ".join(s.council["synthesis"]["voice_brief"])
    if action.kind == "generate":
        if s.roadmap is None:
            if s.council is None:
                await _convene(s)
                out["tools"].append("ask_council")
            state: dict = {"council": s.council}
            await run_tool("build_roadmap", {"idea": idea}, s.elicitation, state)
            s.roadmap = state["roadmap"]
            out["tools"].append("build_roadmap")
        question = _roadmap_line(s.roadmap)
    if lead is None and fresh is None and action.kind == "ask":
        lead = _next_novelty_point(s)
    reply = _fallback_reply(fresh, question, lead)  # templated from the session: no fact check
    s.messages.append({"role": "assistant", "content": reply})
    splitter = SentenceSplitter()
    for sentence in splitter.feed(reply) + splitter.flush():
        out["spoken"].append(sentence)
        yield _event("sentence", sentence)


# ---- the turn -----------------------------------------------------------------


def _advance(s: AgentSession, text: str) -> engine.Action:
    """Fold the words into the elicitation engine; a yes/no answers a restatement."""
    if s.elicitation.state is SessionState.CONFIRMING:
        words = set(re.findall(r"[a-z]+", text.lower()))
        if words & NO and not words & YES:
            engine.observe(s.elicitation, text)
            return engine.confirm(s.elicitation, False)
        if words & YES:
            return engine.confirm(s.elicitation, True)
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
) -> AsyncIterator[dict]:
    """One founder turn as events: ack, sentence…, tool, evidence, done.

    `language` is the founder's language for this turn (from speech recognition or
    their choice); the reply comes back in it when a model is available.
    """
    s.updated_at = datetime.now(UTC)
    if language in LANGUAGE_NAMES:
        s.language = language
    s.idea = s.idea or text
    action = _advance(s, text)
    s.pending_slot = action.slot if action.kind == "ask" else None
    if action.kind == "confirm":
        question = f"Here is what I understood: {action.objective} Is that right?"
    elif action.kind == "generate":
        question = "They confirmed: build the roadmap now and walk them through it."
    else:
        question = action.question or ""
    if action.kind == "ask" and s.elicitation.turns:
        s.elicitation.turns[-1].question = question  # so a resumed session can repeat it
    yield _event(
        "ack",
        {
            "session_id": s.id,
            "action": _action_dict(action),
            # so the voice can start speaking the first sentence in the right language
            "reply_language": (s.language or "en-IN") if _model_allowed(s) else "en-IN",
        },
    )

    s.messages.append({"role": "user", "content": text})
    out: dict = {
        "spoken": [],
        "dropped": [],
        "tools": [],
        "usage": {},
        "wants_opinion": bool(OPINION.search(text)),
        "model": "offline",
    }
    own = client is None
    client = client or httpx.AsyncClient(timeout=120)
    try:
        if _model_allowed(s):
            mark = len(s.messages)
            try:
                async for ev in _llm_stream(s, question, client, out):
                    yield ev
                model_breaker.succeed()
                out["model"] = "model"
            except (httpx.HTTPError, RuntimeError, json.JSONDecodeError) as exc:
                # The model failed: finish this turn offline, and let the breaker
                # decide whether to skip the model for a while.
                model_breaker.fail(type(exc).__name__)
                log.warning("model.failed_turn_offline", error=type(exc).__name__)
                del s.messages[mark:]  # drop the half-finished exchange
                out["model"] = "offline (model failed)"
                if not out["spoken"]:
                    async for ev in _offline_stream(s, action, question, client, out):
                        yield ev
        else:
            async for ev in _offline_stream(s, action, question, client, out):
                yield ev
    finally:
        if own:
            await client.aclose()
        _add_usage(s.usage, out["usage"])

    yield _event(
        "done",
        {
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
            # the language the reply was written in: offline templates are English only
            "language": (s.language or "en-IN") if out["model"] == "model" else "en-IN",
            "usage": s.usage,
            "known": _known_dict(s),
            "idea_version": s.idea_version,
        },
    )


async def turn(
    s: AgentSession,
    text: str,
    *,
    client: httpx.AsyncClient | None = None,
    language: str | None = None,
) -> dict:
    """The same turn, collected: returns the `done` payload."""
    done: dict = {}
    async for ev in turn_stream(s, text, client=client, language=language):
        if ev["event"] == "done":
            done = ev["data"]
    return done


__all__ = ["AgentSession", "new_session", "snapshot", "turn", "turn_stream"]
