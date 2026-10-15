"""Conversation state for the orchestrator (design Req 5.1).

Holds the running conversation, the active swarm, and a context stack so a founder
can pause one task ("actually, what schemes am I eligible for?") and return to the
original. Persisted via the LangGraph checkpointer in the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ConversationState:
    user_id: str
    session_id: str
    messages: list[Turn] = field(default_factory=list)
    current_intent: str | None = None
    active_swarm: str | None = None
    entities: dict = field(default_factory=dict)
    language: str = "en"
    context_stack: list[dict] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(Turn(role, content))

    def push_context(self) -> None:
        """Remember the current task before switching to another."""
        self.context_stack.append(
            {
                "intent": self.current_intent,
                "swarm": self.active_swarm,
                "entities": dict(self.entities),
            }
        )

    def pop_context(self) -> dict | None:
        """Resume the most recently paused task, if any."""
        if not self.context_stack:
            return None
        saved = self.context_stack.pop()
        self.current_intent = saved["intent"]
        self.active_swarm = saved["swarm"]
        self.entities = saved["entities"]
        return saved
