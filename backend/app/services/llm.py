"""LLM provider abstraction (Task 5.1 · managed-API-first).

One interface, swappable providers. A deterministic stub keeps the orchestrator
and swarms testable and locally runnable without an API key; the Anthropic
adapter is used in real deployments. Cost controls (prompt caching, model
routing) live above this layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("llm")


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, *, system: str, prompt: str, max_tokens: int = 512) -> str: ...


class StubLLMProvider(LLMProvider):
    """Deterministic, offline provider for dev/test.

    Not intelligent — it echoes a compact, structured acknowledgement so callers
    can exercise flow without a network. Swarms that need real generation degrade
    gracefully to templated output when this provider is active.
    """

    name = "stub"

    async def complete(self, *, system: str, prompt: str, max_tokens: int = 512) -> str:
        return f"[stub] {prompt.strip()[:200]}"


class AnthropicLLMProvider(LLMProvider):
    """Managed generation via Anthropic (lazy client)."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def complete(self, *, system: str, prompt: str, max_tokens: int = 512) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._api_key)
        resp = await client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")


def _select_provider() -> LLMProvider:
    s = get_settings()
    if s.llm_provider == "anthropic" and s.anthropic_api_key:
        return AnthropicLLMProvider(s.anthropic_api_key, s.llm_model_main)
    log.info("llm.using_stub_provider")
    return StubLLMProvider()


@lru_cache
def get_llm_provider() -> LLMProvider:
    return _select_provider()
