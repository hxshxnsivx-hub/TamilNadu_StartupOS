"""The language models the mentor can use, behind one interface.

    anthropic   Claude (paid; used only when a key is set)
    gemini      Google Gemini API, free tier (a key from AI Studio, no payment)
    ollama      a model on this machine (free, offline, slow on a CPU)

The conversation is kept in one format (Anthropic's: user/assistant messages
with text, tool_use and tool_result blocks), whatever model wrote it, so a
session can move from one provider to the next mid-conversation. Each adapter
translates to its API and back.

Every provider streams the same events:

    ("text", chunk)                       while the reply is written
    ("message", (content, stop, extra))   at the end: blocks, "tool_use" or
                                          "end_turn", and fields to keep on
                                          the assistant message (Gemini's raw
                                          steps, which it needs back verbatim)

`chain()` lists the providers to try, in settings.llm_order, that are
configured and whose breaker is closed. A quota error (HTTP 429) or any other
failure opens the way to the next one.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.breaker import Breaker, model_breaker

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

Event = tuple[str, Any]


class ModelError(RuntimeError):
    """A provider answered, but not with a usable reply (quota, refusal, bad stream)."""


def _usage(total: dict | None, input_tokens: int = 0, output_tokens: int = 0) -> None:
    if total is None:
        return
    total["input_tokens"] = total.get("input_tokens", 0) + int(input_tokens or 0)
    total["output_tokens"] = total.get("output_tokens", 0) + int(output_tokens or 0)


def _check(r: httpx.Response, name: str) -> None:
    if r.status_code == 429:
        raise ModelError(f"{name}: quota or rate limit reached")
    if r.status_code != 200:
        r.raise_for_status()


@dataclass
class Provider:
    name: str
    breaker: Breaker
    tools: bool = True  # can call the research tools itself
    can_judge: bool = True  # fit for the review panel's many short calls
    extra: dict = field(default_factory=dict)

    def configured(self) -> bool:
        raise NotImplementedError

    def ready(self) -> bool:
        return self.configured() and self.breaker.allow()

    def stream(
        self,
        client: httpx.AsyncClient,
        system: str,
        messages: list[dict],
        tools: list[dict] | None,
        usage: dict | None = None,
    ) -> AsyncIterator[Event]:
        raise NotImplementedError

    async def complete(
        self, client: httpx.AsyncClient, system: str, user: str, max_tokens: int = 700
    ) -> tuple[str, dict]:
        raise NotImplementedError


# ---- Anthropic ----------------------------------------------------------------


def _plain_messages(messages: list[dict]) -> list[dict]:
    """Only what the Messages API accepts: role and content."""
    return [{"role": m["role"], "content": m["content"]} for m in messages]


class Anthropic(Provider):
    def configured(self) -> bool:
        return bool(get_settings().anthropic_api_key)

    def _headers(self) -> dict:
        return {
            "x-api-key": get_settings().anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def stream(self, client, system, messages, tools, usage=None):
        st = get_settings()
        body = {
            "model": st.llm_model_main,
            "max_tokens": 1024,
            "system": system,
            "messages": _plain_messages(messages),
            "stream": True,
        }
        if tools:
            body["tools"] = tools
        blocks: dict[int, dict] = {}
        partial_json: dict[int, str] = {}
        stop = None
        async with client.stream("POST", ANTHROPIC_URL, headers=self._headers(), json=body) as r:
            if r.status_code != 200:
                await r.aread()
                _check(r, self.name)
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                ev = json.loads(line[5:].strip())
                kind = ev.get("type")
                use = (ev.get("message") or {}).get("usage") or ev.get("usage")
                if use and usage is not None:
                    for k, v in use.items():
                        if isinstance(v, int):
                            usage[k] = usage.get(k, 0) + v
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
                    raise ModelError(ev.get("error", {}).get("message", "model stream error"))
        for i, raw in partial_json.items():
            blocks[i]["input"] = json.loads(raw) if raw.strip() else {}
        yield "message", ([blocks[i] for i in sorted(blocks)], stop, {})

    async def complete(self, client, system, user, max_tokens=700):
        st = get_settings()
        r = await client.post(
            ANTHROPIC_URL,
            headers=self._headers(),
            json={
                "model": st.llm_model_fast,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        _check(r, self.name)
        data = r.json()
        text = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )
        return text, data.get("usage", {})


# ---- Gemini (Interactions API) ---------------------------------------------------


def gemini_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
        }
        for t in tools
    ]


def _text(content: Any) -> str:
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)


def gemini_input(messages: list[dict]) -> list[dict]:
    """The conversation as Interactions steps. Gemini's own earlier steps go back
    verbatim (they can carry signatures it requires); others are translated."""
    steps: list[dict] = []
    names: dict[str, str] = {}  # tool call id -> function name
    for m in messages:
        content = m["content"]
        if m["role"] == "assistant":
            if m.get("gemini_steps"):
                for st in m["gemini_steps"]:
                    if st.get("type") == "function_call":
                        names[st.get("id", "")] = st.get("name", "")
                steps += m["gemini_steps"]
                continue
            blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content
            texts = [b["text"] for b in blocks if b.get("type") == "text" and b.get("text")]
            if texts:
                steps.append(
                    {"type": "model_output", "content": [{"type": "text", "text": " ".join(texts)}]}
                )
            for b in blocks:
                if b.get("type") == "tool_use":
                    names[b["id"]] = b["name"]
                    steps.append(
                        {
                            "type": "function_call",
                            "id": b["id"],
                            "name": b["name"],
                            "arguments": b.get("input") or {},
                        }
                    )
        elif isinstance(content, str):
            steps.append({"type": "user_input", "content": [{"type": "text", "text": content}]})
        else:
            for b in content:
                if b.get("type") == "tool_result":
                    steps.append(
                        {
                            "type": "function_result",
                            "name": names.get(b["tool_use_id"], ""),
                            "call_id": b["tool_use_id"],
                            "result": [{"type": "text", "text": _text(b.get("content"))}],
                        }
                    )
                elif b.get("type") == "text":
                    steps.append(
                        {"type": "user_input", "content": [{"type": "text", "text": b["text"]}]}
                    )
    return steps


def gemini_output(steps: list[dict]) -> tuple[list[dict], str, list[dict]]:
    """(blocks in the shared format, stop reason, the model's own steps to keep)."""
    own = [s for s in steps if s.get("type") not in ("user_input", "function_result")]
    blocks: list[dict] = []
    for s in own:
        if s.get("type") == "model_output":
            text = "".join(
                p.get("text", "") for p in s.get("content") or [] if p.get("type") == "text"
            )
            if text:
                blocks.append({"type": "text", "text": text})
        elif s.get("type") == "function_call":
            args = s.get("arguments") or {}
            if isinstance(args, str):
                args = json.loads(args) if args.strip() else {}
            blocks.append(
                {
                    "type": "tool_use",
                    "id": s.get("id", ""),
                    "name": s.get("name", ""),
                    "input": args,
                }
            )
    stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
    return blocks, stop, own


class Gemini(Provider):
    def configured(self) -> bool:
        return bool(get_settings().gemini_api_key)

    def _headers(self) -> dict:
        return {"x-goog-api-key": get_settings().gemini_api_key, "content-type": "application/json"}

    def _body(self, model: str, system: str, input_: Any, max_tokens: int) -> dict:
        return {
            "model": model,
            "system_instruction": system,
            "input": input_,
            "store": False,  # nothing kept on Google's side between turns
            "generation_config": {
                "max_output_tokens": max_tokens,
                "thinking_level": get_settings().gemini_thinking,
            },
        }

    async def stream(self, client, system, messages, tools, usage=None):
        st = get_settings()
        body = self._body(st.gemini_model, system, gemini_input(messages), 2048)
        body["stream"] = True
        if tools:
            body["tools"] = gemini_tools(tools)
        streamed: list[str] = []
        final: dict | None = None
        async with client.stream("POST", GEMINI_URL, headers=self._headers(), json=body) as r:
            if r.status_code != 200:
                await r.aread()
                _check(r, self.name)
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw or raw == "[DONE]":
                    continue
                ev = json.loads(raw)
                kind = ev.get("event_type")
                if kind == "step.delta":
                    d = ev.get("delta") or {}
                    if d.get("type") == "text" and d.get("text"):
                        streamed.append(d["text"])
                        yield "text", d["text"]
                elif kind == "interaction.completed":
                    final = ev.get("interaction") or {}
                elif kind == "error":
                    err = ev.get("error") or {}
                    raise ModelError(f"gemini: {err.get('message') or err.get('code')}")
        if final is None:
            raise ModelError("gemini: the stream ended without a finished reply")
        if final.get("status") in ("failed", "cancelled"):
            raise ModelError(f"gemini: reply {final['status']}")
        use = final.get("usage") or {}
        _usage(usage, use.get("total_input_tokens", 0), use.get("total_output_tokens", 0))
        blocks, stop, own = gemini_output(final.get("steps") or [])
        if streamed and not any(b["type"] == "text" for b in blocks):
            blocks.insert(0, {"type": "text", "text": "".join(streamed)})
        yield "message", (blocks, stop, {"gemini_steps": own})

    async def complete(self, client, system, user, max_tokens=700):
        st = get_settings()
        body = self._body(st.gemini_model_fast, system, user, max_tokens)
        body["generation_config"]["thinking_level"] = "minimal"
        r = await client.post(GEMINI_URL, headers=self._headers(), json=body)
        _check(r, self.name)
        data = r.json()
        blocks, _, _ = gemini_output(data.get("steps") or [])
        use = data.get("usage") or {}
        return "".join(b.get("text", "") for b in blocks if b["type"] == "text"), {
            "input_tokens": use.get("total_input_tokens", 0),
            "output_tokens": use.get("total_output_tokens", 0),
        }


# ---- Ollama (local) -----------------------------------------------------------------


def ollama_messages(system: str, messages: list[dict]) -> list[dict]:
    out = [{"role": "system", "content": system}]
    for m in messages:
        c = m["content"]
        if isinstance(c, str):
            text = c
        else:
            text = " ".join(b.get("text", "") for b in c if b.get("type") == "text")
        if text:
            out.append({"role": m["role"], "content": text})
    return out


class Ollama(Provider):
    def configured(self) -> bool:
        return bool(get_settings().ollama_model)

    async def stream(self, client, system, messages, tools, usage=None):
        st = get_settings()
        body = {
            "model": st.ollama_model,
            "messages": ollama_messages(system, messages),
            "stream": True,
            "keep_alive": "30m",  # stay loaded between turns: loading takes seconds
            "options": {"temperature": 0.4, "num_predict": 400},
        }
        parts: list[str] = []
        async with client.stream("POST", f"{st.ollama_url}/api/chat", json=body) as r:
            if r.status_code != 200:
                await r.aread()
                _check(r, self.name)
            async for line in r.aiter_lines():
                if not line.strip():
                    continue
                ev = json.loads(line)
                if ev.get("error"):
                    raise ModelError(f"ollama: {ev['error']}")
                chunk = (ev.get("message") or {}).get("content") or ""
                if chunk:
                    parts.append(chunk)
                    yield "text", chunk
                if ev.get("done"):
                    _usage(usage, ev.get("prompt_eval_count", 0), ev.get("eval_count", 0))
        yield "message", ([{"type": "text", "text": "".join(parts)}], "end_turn", {})

    async def complete(self, client, system, user, max_tokens=700):
        text, use = "", {}
        async for kind, payload in self.stream(
            client, system, [{"role": "user", "content": user}], None, use
        ):
            if kind == "message":
                text = payload[0][0]["text"]
        return text, use


# ---- the chain ------------------------------------------------------------------------

PROVIDERS: dict[str, Provider] = {
    "anthropic": Anthropic("anthropic", model_breaker),
    "gemini": Gemini("gemini", Breaker("gemini")),
    # one call per turn at most, never the review panel's seven: too slow on a CPU
    "ollama": Ollama("ollama", Breaker("ollama"), tools=False, can_judge=False),
}


def chain() -> list[Provider]:
    """The providers to try for a turn, in order: configured, breaker closed."""
    names = [n.strip() for n in get_settings().llm_order.split(",") if n.strip()]
    return [PROVIDERS[n] for n in names if n in PROVIDERS and PROVIDERS[n].ready()]


def judge() -> Provider | None:
    """The first provider fit for the review panel's seats, if any."""
    return next((p for p in chain() if p.can_judge), None)
