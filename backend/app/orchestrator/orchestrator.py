"""Central Orchestrator (design Req 5.1) — classify, route, manage context.

This is the routing brain. It classifies each turn (confidence cascade), routes
to the owning swarm, and maintains the context stack for task switching. Swarm
execution itself lands in later tasks (11+); here the orchestrator returns a
routing decision the API/swarm layer acts on.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.orchestrator.intent import Classification, classify_keywords
from app.orchestrator.state import ConversationState


@dataclass
class RouteDecision:
    intent: str
    swarm: str
    confidence: float
    action: str  # "route" | "clarify"
    matched: tuple[str, ...]


class Orchestrator:
    def __init__(self, classifier: Callable[[str], Classification] | None = None) -> None:
        self._classify = classifier or classify_keywords

    def handle_turn(self, state: ConversationState, message: str) -> RouteDecision:
        state.add_message("user", message)
        c = self._classify(message)

        if c.should_clarify:
            return RouteDecision(c.intent.value, "orchestrator", c.confidence, "clarify", c.matched)

        # Context switch: pausing a swarm task to jump to a different swarm.
        if state.active_swarm and c.swarm != "orchestrator" and state.active_swarm != c.swarm:
            state.push_context()

        state.current_intent = c.intent.value
        state.active_swarm = c.swarm
        return RouteDecision(c.intent.value, c.swarm, c.confidence, "route", c.matched)

    def resume(self, state: ConversationState) -> dict | None:
        """Return to the most recently paused task."""
        return state.pop_context()
