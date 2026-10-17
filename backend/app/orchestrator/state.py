"""Conversation state for the orchestrator (design Req 5.1).

Holds the running conversation, the active swarm, and a context stack so a founder
can pause one task ("actually, what schemes am I eligible for?") and return to the
original. Saved inside the conversation's session document between turns
(``to_dict``/``from_dict``; docs/decisions/0003-sessions-as-json-document.md).
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
    node: str = "greeting"  # the node that answered last (not error_handling)
    last_question: str | None = None  # the active task's latest reply, repeated on resume

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(Turn(role, content))

    def push_context(self) -> None:
        """Remember the current task before switching to another."""
        self.context_stack.append(
            {
                "intent": self.current_intent,
                "swarm": self.active_swarm,
                "entities": dict(self.entities),
                "node": self.node,
                "last_question": self.last_question,
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
        self.node = saved.get("node", self.node)
        self.last_question = saved.get("last_question")
        return saved

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "messages": [{"role": t.role, "content": t.content} for t in self.messages],
            "current_intent": self.current_intent,
            "active_swarm": self.active_swarm,
            "entities": self.entities,
            "language": self.language,
            "context_stack": self.context_stack,
            "node": self.node,
            "last_question": self.last_question,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ConversationState:
        return cls(
            user_id=d["user_id"],
            session_id=d["session_id"],
            messages=[Turn(m["role"], m["content"]) for m in d.get("messages", [])],
            current_intent=d.get("current_intent"),
            active_swarm=d.get("active_swarm"),
            entities=d.get("entities", {}),
            language=d.get("language", "en"),
            context_stack=d.get("context_stack", []),
            node=d.get("node", "greeting"),
            last_question=d.get("last_question"),
        )
