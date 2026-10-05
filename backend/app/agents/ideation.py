"""The ideation agent: one conversation that knows what already exists.

Each founder turn:

    1. the elicitation engine folds the words into slots and picks the one
       question worth asking next (deterministic, never nags, Q_MAX ceiling);
    2. the language model talks — it calls tools (prior-art scan, registry,
       schemes and incubators, roadmap) and phrases the reply around evidence
       and the engine's question;
    3. the reply goes back with the evidence it used, so the screen (or the
       voice orb's caption) can show the papers, trials and projects it cites.

Without an API key the same turn runs offline: the scan runs once the idea is
clear, and a templated reply summarises it. The founder still gets evidence,
just in plainer words.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx

from app.agents.tools import TOOLS, compact_scan, run_tool
from app.core.config import get_settings
from app.elicitation import engine
from app.elicitation.session import ElicitationSession, SessionState

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MAX_TOOL_ROUNDS = 4
IDLE_EXPIRY = timedelta(hours=6)
YES = {"yes", "yeah", "yep", "correct", "right", "ok", "okay", "sure", "seri", "aamaa", "aama"}
NO = {"no", "nope", "wrong", "illai", "not"}
SKIP = re.compile(
    r"^\s*(skip|pass|next|not sure|no idea|don'?t know|i don'?t know|theriyala)\W*$", re.I
)

SYSTEM = """You are Vanigam's ideation guide for founders in Tamil Nadu. You talk with
{name} about their idea — hardware, software, a physical product or a service.

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
- Use find_domains and support_for for Tamil Nadu schemes and incubators; never
  invent a scheme, amount or deadline. Use build_roadmap once they confirm.
- Record facts they state with note_fact.
- Ask at most one question per turn. The question to ask next is: {question}
  Ask it in your own words, unless the founder raised something more urgent.
- Speak simply; the founder may be listening rather than reading and English
  may be their second language. Short paragraphs, no tables, no markdown.

Known so far: {known}
"""


@dataclass
class AgentSession:
    name: str
    elicitation: ElicitationSession
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    messages: list[dict] = field(default_factory=list)
    idea: str = ""
    scan: dict | None = None
    roadmap: dict | None = None
    pending_slot: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# In-memory for now; sessions move to the database with the elicitation endpoints.
_SESSIONS: dict[str, AgentSession] = {}


def get_session(session_id: str) -> AgentSession | None:
    s = _SESSIONS.get(session_id)
    if s and datetime.now(UTC) - s.updated_at > IDLE_EXPIRY:
        _SESSIONS.pop(session_id, None)
        return None
    return s


def start(name: str | None = None, profile: dict | None = None, user_id: str = "anon") -> dict:
    who = (name or "").strip() or "there"
    s = AgentSession(name=who, elicitation=engine.start(user_id, profile=profile))
    _SESSIONS[s.id] = s
    greeting = (
        f"Vanakkam {who}! Tell me about the idea you are working on, in your own words."
        " It can be a product, a machine, an app or a service. I will look up what already"
        " exists for it, papers, patents, projects and products, and we will shape it together."
    )
    # The Messages API starts with a user turn; the screen opening stands in for it.
    s.messages += [
        {"role": "user", "content": "(The founder opened the ideation screen.)"},
        {"role": "assistant", "content": greeting},
    ]
    return {"session_id": s.id, "reply": greeting, "action": {"kind": "ask", "slot": None}}


def _known(s: AgentSession) -> str:
    rows = [
        f"{k}={getattr(v.value, 'value', v.value)}" for k, v in sorted(s.elicitation.slots.items())
    ]
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
    parts = [str(slots[k].value) for k in ("problem", "solution") if k in slots]
    return " ".join(parts) or s.idea


async def _call_model(client: httpx.AsyncClient, system: str, messages: list[dict]) -> dict:
    st = get_settings()
    r = await client.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": st.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": st.llm_model_main,
            "max_tokens": 1024,
            "system": system,
            "tools": TOOLS,
            "messages": messages,
        },
    )
    r.raise_for_status()
    return r.json()


async def _llm_turn(s: AgentSession, question: str, client: httpx.AsyncClient) -> tuple[str, list]:
    system = SYSTEM.format(name=s.name, question=question, known=_known(s))
    state: dict = {}
    used: list[str] = []
    for _ in range(MAX_TOOL_ROUNDS + 1):
        resp = await _call_model(client, system, s.messages)
        content = resp.get("content", [])
        s.messages.append({"role": "assistant", "content": content})
        calls = [b for b in content if b.get("type") == "tool_use"]
        if resp.get("stop_reason") != "tool_use" or not calls:
            break
        results = []
        for c in calls:
            out = await run_tool(c["name"], c.get("input") or {}, s.elicitation, state)
            used.append(c["name"])
            results.append(
                {"type": "tool_result", "tool_use_id": c["id"], "content": json.dumps(out)}
            )
        s.messages.append({"role": "user", "content": results})
    s.scan = state.get("scan", s.scan)
    s.roadmap = state.get("roadmap", s.roadmap)
    text = "".join(b.get("text", "") for b in s.messages[-1]["content"] if isinstance(b, dict))
    return text.strip(), used


def _fallback_reply(scan: dict | None, question: str | None) -> str:
    """Plain-words summary of a fresh scan, used when no language model is configured."""
    parts: list[str] = []
    c = compact_scan(scan) if scan else None
    if c:
        fields = [f["name"] for f in c["fields"][:4]]
        if fields:
            parts.append(f"Your idea touches {', '.join(fields)}.")
        cov = {x["source"]: x for x in c["coverage"]}
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
        missing = [
            k for k, v in cov.items() if v["status"] not in ("ok", "skipped")
        ]  # not searched, so not "nothing"
        if missing:
            parts.append(f"I could not search {', '.join(missing)} this time.")
        firsts = [d["questions"][0] for d in c["discuss"][:2]]
        if firsts:
            parts.append("Things to think through: " + " ".join(firsts))
    if question:
        parts.append(question)
    return " ".join(parts) or "Tell me a little more about the idea."


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
    engine.observe(s.elicitation, text, answering=s.pending_slot)
    return engine.step(s.elicitation)


def _roadmap_line(r: dict) -> str:
    ms = r.get("milestones") or []
    first = ", then ".join(m["title"] for m in ms[:3])
    months = r.get("months_realistic")
    return (
        f"Your roadmap has {len(ms)} milestones over about {months} months. It starts with"
        f" {first}. Shall we go through the costs or the licences first?"
    )


async def turn(s: AgentSession, text: str, *, client: httpx.AsyncClient | None = None) -> dict:
    s.updated_at = datetime.now(UTC)
    s.idea = s.idea or text
    action = _advance(s, text)
    s.pending_slot = action.slot if action.kind == "ask" else None
    if action.kind == "confirm":
        question = f"Here is what I understood: {action.objective} Is that right?"
    elif action.kind == "generate":
        question = "They confirmed: build the roadmap now and walk them through it."
    else:
        question = action.question or ""

    s.messages.append({"role": "user", "content": text})
    own = client is None
    client = client or httpx.AsyncClient(timeout=120)
    used: list[str] = []
    try:
        if get_settings().anthropic_api_key:
            reply, used = await _llm_turn(s, question, client)
        else:
            idea = _idea_text(s)
            if s.scan is None and len(idea) >= 20:
                from app.research.scan import scan

                s.scan = await scan(idea, client=client)
                used.append("scan_prior_art")
            if action.kind == "generate":
                if s.roadmap is None:
                    state: dict = {}
                    await run_tool("build_roadmap", {"idea": idea}, s.elicitation, state)
                    s.roadmap = state["roadmap"]
                    used.append("build_roadmap")
                question = _roadmap_line(s.roadmap)
            fresh = s.scan if "scan_prior_art" in used else None  # summarise a scan once
            reply = _fallback_reply(fresh, question)
            s.messages.append({"role": "assistant", "content": reply})
    finally:
        if own:
            await client.aclose()

    return {
        "session_id": s.id,
        "reply": reply,
        "action": _action_dict(action),
        "tools_used": used,
        "evidence": compact_scan(s.scan) if s.scan else None,
        "roadmap": s.roadmap,
        "known": {k: getattr(v.value, "value", v.value) for k, v in s.elicitation.slots.items()},
    }


def _reset_sessions() -> None:  # tests
    _SESSIONS.clear()


__all__ = ["AgentSession", "get_session", "start", "turn"]
