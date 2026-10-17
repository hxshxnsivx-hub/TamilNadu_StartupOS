"""The conversation state machine (design.md "Central Orchestrator", Req 5.1).

One founder turn walks these nodes:

    greeting ──────────────────────────────────────────────┐
    intent_recognition ─┬─ profile_collection   (profile)  │
       (conditional     ├─ idea_discussion      (roadmap)  ├─► reply
        edges on the    ├─ scheme_discovery     (scheme)   │
        classified      ├─ b2b_matching         (b2b)      │
        intent)         ├─ funding_assessment   (funding)  │
                        └─ clarification        (unclear)  │
    any task node that raises ─► error_handling ───────────┘

Deterministic and offline: the keyword classifier decides the edge, and each task
node is a handler (app/orchestrator/handlers.py) that calls the swarm code. A plain
machine rather than LangGraph, because the state is saved in the session document
between turns (decision 0003) and each turn runs exactly one task node.

The context stack lets a founder pause a task: a turn that switches swarm pushes
the current task; when the detour finishes in one turn (a scheme check, a
completeness score) the paused task is popped and its open question asked again.
"Go back" pops it by hand. Mid-task, a turn only switches when it is a clear
request (a question, an ask, or two topic keywords): an answer to the task's own
question ("a grant", "investors") stays with the task (``_switches``).
"""

from __future__ import annotations

import copy
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.orchestrator.intent import AUTO_ROUTE, Classification, classify_keywords
from app.orchestrator.state import ConversationState

log = get_logger("orchestrator")

# Conditional edges: the swarm the classifier names → the node that serves it.
SWARM_NODE: dict[str, str] = {
    "profile": "profile_collection",
    "roadmap": "idea_discussion",
    "scheme": "scheme_discovery",
    "b2b": "b2b_matching",
    "funding": "funding_assessment",
}
# How a paused task is named when the founder comes back to it.
SWARM_LABEL: dict[str, str] = {
    "profile": "your profile",
    "roadmap": "your idea",
    "scheme": "schemes",
    "b2b": "suppliers",
    "funding": "funding",
}

_GREETING = re.compile(
    r"^\s*(hi|hello|hey|vanakkam|namaste|namaskaram|good (morning|afternoon|evening))[\s!.,]*$",
    re.I,
)
_RESUME = re.compile(r"\b(go back|back to|resume|where we were)\b", re.I)
# A request rather than an answer: a clause that opens with a question or an ask.
_ASKING = re.compile(
    r"(^|[,.;:!]\s*|\b(wait|actually|also|now|ok|okay|and|but|so|then)\s+)"
    r"(which|what|what's|how|where|who|when|why|is there|are there|am i|can i|could i|"
    r"do i|should i|will i|show me|find me|tell me|give me|help me|let's talk about)\b",
    re.I,
)

GREETING = (
    "Vanakkam! I can help you shape a startup idea into a roadmap, find government schemes"
    " you qualify for, check how complete your profile is, list the materials your product"
    " needs, or see how ready you are to raise funding. What would you like to start with?"
)
CLARIFY = (
    "I did not quite follow. Would you like to work on your idea or its roadmap, find"
    " schemes you qualify for, update your profile, find suppliers, or talk about funding?"
)
ERROR = "Sorry, something went wrong on my side while working on that. Please try again."


@dataclass
class TurnContext:
    """What a task node receives: the state, the saved session, the turn and its intent."""

    state: ConversationState
    session: Any  # the AgentSession the conversation is saved in (None in some tests)
    text: str
    classification: Classification
    language: str | None = None


@dataclass
class HandlerResult:
    reply: str
    done: bool  # the task finished this turn, so a paused task may resume
    data: dict = field(default_factory=dict)


Handler = Callable[[TurnContext], Awaitable[HandlerResult]]


@dataclass
class TurnResult:
    reply: str
    node: str  # the node that answered
    action: str  # greet | route | continue | clarify | resume | error
    intent: str | None = None
    swarm: str | None = None
    confidence: float = 0.0
    matched: tuple[str, ...] = ()
    resumed: dict | None = None  # the paused task this turn returned to
    paused: list[str] = field(default_factory=list)  # swarms still waiting, oldest first
    data: dict = field(default_factory=dict)


class ConversationGraph:
    TASK_NODES = tuple(SWARM_NODE.values())

    def __init__(
        self,
        handlers: dict[str, Handler],
        classifier: Callable[[str], Classification] | None = None,
    ) -> None:
        missing = set(self.TASK_NODES) - set(handlers)
        if missing:
            raise ValueError(f"no handler for {sorted(missing)}")
        self._handlers = handlers
        self._classify = classifier or classify_keywords

    async def step(
        self,
        state: ConversationState,
        text: str,
        *,
        session: Any = None,
        language: str | None = None,
    ) -> TurnResult:
        """Run one founder turn through the machine and record both sides of it."""
        state.add_message("user", text)
        r = await self._run(state, text, session, language)
        r.paused = [c["swarm"] for c in state.context_stack]
        if r.action != "error":  # a failed turn leaves the machine where it was
            state.node = r.node
        state.add_message("assistant", r.reply)
        return r

    async def _run(
        self, state: ConversationState, text: str, session: Any, language: str | None
    ) -> TurnResult:
        if _GREETING.match(text):
            return self._greeting(state)
        if state.context_stack and _RESUME.search(text):
            return self._resume(state, lead="Sure.")

        # intent_recognition
        c = self._classify(text)
        if c.swarm in SWARM_NODE and c.confidence >= AUTO_ROUTE:
            same = c.swarm == state.active_swarm
            action = "continue" if same or not self._switches(state, text, c) else "route"
        elif state.active_swarm:
            # No clear new topic: the founder is answering the task in hand.
            action = "continue"
        else:
            return TurnResult(
                CLARIFY, "clarification", "clarify", c.intent.value, None, c.confidence, c.matched
            )

        # conditional edge → task node
        swarm = c.swarm if action == "route" else state.active_swarm
        intent = c.intent.value if action == "route" else state.current_intent
        node = SWARM_NODE[swarm]
        before = copy.deepcopy(state.to_dict())  # to put back if the node fails
        if action == "route" and state.active_swarm:
            state.push_context()  # pause the current task
            # coming back to a paused swarm by name: that older entry is now stale
            state.context_stack = [
                ctx for ctx in state.context_stack[:-1] if ctx["swarm"] != swarm
            ] + state.context_stack[-1:]
        state.current_intent, state.active_swarm, state.node = intent, swarm, node

        try:
            out = await self._handlers[node](TurnContext(state, session, text, c, language))
        except Exception as exc:  # error_handling: the turn fails, the conversation does not
            log.warning("orchestrator.node_failed", node=node, error=type(exc).__name__)
            restored = ConversationState.from_dict(before)
            restored.messages = state.messages
            state.__dict__.update(restored.__dict__)
            return TurnResult(ERROR, "error_handling", "error", intent, swarm, c.confidence)

        r = TurnResult(out.reply, node, action, intent, swarm, c.confidence, c.matched)
        r.data = out.data
        state.last_question = out.reply
        if out.done:
            state.active_swarm = None
            if state.context_stack:
                back = self._resume(state, lead=out.reply)
                r.reply, r.node, r.resumed = back.reply, back.node, back.resumed
        return r

    @staticmethod
    def _switches(state: ConversationState, text: str, c: Classification) -> bool:
        """Whether a turn that names another swarm leaves the task in hand.

        With no task in hand, any confident topic routes. Mid-task, the founder is
        usually answering the task's own question ("How do you expect to fund it — a
        loan, a grant, investors?" → "a grant"), so a keyword only switches when the
        turn is a clear request: a question or an ask, or two or more topic keywords.
        Keywords the task's own question used never count.
        """
        if not state.active_swarm:
            return True
        asked = (state.last_question or "").lower()
        hits = [k for k in c.matched if k.strip() not in asked]
        if not hits:
            return False
        return len(hits) >= 2 or "?" in text or bool(_ASKING.search(text))

    def _greeting(self, state: ConversationState) -> TurnResult:
        reply = GREETING
        if state.active_swarm and state.last_question:
            label = SWARM_LABEL[state.active_swarm]
            reply = f"Vanakkam again! We were working on {label}. {state.last_question}"
        return TurnResult(reply, "greeting", "greet", swarm=state.active_swarm)

    def _resume(self, state: ConversationState, lead: str) -> TurnResult:
        saved = state.pop_context()
        label = SWARM_LABEL.get(saved["swarm"], "where we were")
        reply = f"{lead} Now, back to {label}."
        if saved.get("last_question"):
            reply += f" {saved['last_question']}"
        return TurnResult(
            reply,
            saved.get("node") or SWARM_NODE[saved["swarm"]],
            "resume",
            saved["intent"],
            saved["swarm"],
            resumed=saved,
        )
