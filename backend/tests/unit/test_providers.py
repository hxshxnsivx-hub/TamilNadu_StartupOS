"""Free models: Gemini (tools, streamed) and Ollama (rewording), and the chain between them."""

from __future__ import annotations

import asyncio
import base64
import json

import httpx
import pytest
from app.agents import ideation as agent
from app.agents import providers, tools
from app.agents.providers import PROVIDERS, gemini_input, gemini_output
from app.core.config import get_settings
from app.voice import gemini_tts

from tests.unit.test_ideation_agent import BCI, NOVELTY, SCAN


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    async def fake_scan(text, *, elements=None, queries=None, client=None, private=False):
        return SCAN

    async def fake_novelty(idea, **_kw):
        return NOVELTY

    monkeypatch.setattr("app.research.scan.scan", fake_scan)
    monkeypatch.setattr(tools.research, "scan", fake_scan)
    monkeypatch.setattr("app.research.novelty.check", fake_novelty)
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")


def _sse(*events: dict) -> bytes:
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events).encode()


def _gemini_reply(text: str, *calls: dict) -> bytes:
    """A streamed Gemini turn: text deltas, then the finished interaction."""
    steps = [{"type": "model_output", "content": [{"type": "text", "text": text}]}] if text else []
    steps += [{"type": "function_call", **c, "signature": "sig"} for c in calls]
    words = [w + " " for w in text.split(" ")] if text else []
    return _sse(
        {"event_type": "interaction.created", "interaction": {"id": "i1"}},
        *(
            {"event_type": "step.delta", "index": 0, "delta": {"type": "text", "text": w}}
            for w in words
        ),  # fmt: skip
        {
            "event_type": "interaction.completed",
            "interaction": {
                "status": "requires_action" if calls else "completed",
                "steps": steps,
                "usage": {"total_input_tokens": 100, "total_output_tokens": 20},
            },
        },
    )


def _ndjson(text: str) -> bytes:
    lines = [{"message": {"role": "assistant", "content": w + " "}, "done": False}
             for w in text.split(" ")]  # fmt: skip
    lines.append({"message": {"content": ""}, "done": True, "prompt_eval_count": 50,
                  "eval_count": 30})  # fmt: skip
    return "\n".join(json.dumps(x) for x in lines).encode()


def _transport(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _turn(s, text, handler):
    async def go():
        async with _transport(handler) as c:
            return await agent.turn(s, text, client=c)

    return asyncio.run(go())


# ---- translation ----------------------------------------------------------------------


def test_the_conversation_becomes_gemini_steps_and_back():
    messages = [
        {"role": "user", "content": "I make jasmine garlands"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me look."},
                {"type": "tool_use", "id": "c1", "name": "scan_prior_art", "input": {"idea": "x"}},
            ],
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "c1", "content": "{}"}],
        },
    ]
    steps = gemini_input(messages)
    assert [s["type"] for s in steps] == [
        "user_input", "model_output", "function_call", "function_result",
    ]  # fmt: skip
    assert steps[3]["name"] == "scan_prior_art" and steps[3]["call_id"] == "c1"

    # Gemini's own steps go back exactly as it sent them (they carry signatures)
    raw = [{"type": "function_call", "id": "c2", "name": "find_domains", "arguments": {},
            "signature": "abc"}]  # fmt: skip
    again = gemini_input([{"role": "assistant", "content": [], "gemini_steps": raw}])
    assert again == raw

    blocks, stop, own = gemini_output(raw)
    assert stop == "tool_use" and blocks[0] == {
        "type": "tool_use", "id": "c2", "name": "find_domains", "input": {},
    }  # fmt: skip
    assert own == raw


def test_only_configured_providers_with_closed_breakers_are_tried(monkeypatch):
    st = get_settings()
    assert providers.chain() == []
    monkeypatch.setattr(st, "gemini_api_key", "g")
    monkeypatch.setattr(st, "ollama_model", "gemma3:4b")
    assert [p.name for p in providers.chain()] == ["gemini", "ollama"]
    assert providers.judge().name == "gemini"  # Ollama never sits on the panel
    for _ in range(3):
        PROVIDERS["gemini"].breaker.fail("429")
    assert [p.name for p in providers.chain()] == ["ollama"] and providers.judge() is None
    monkeypatch.setattr(st, "llm_order", "ollama,gemini")
    PROVIDERS["gemini"].breaker.succeed()
    assert [p.name for p in providers.chain()] == ["ollama", "gemini"]


# ---- Gemini talks, with tools ------------------------------------------------------------


def test_gemini_runs_the_turn_with_tools_and_the_fact_check(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "g-key")
    sent: list[dict] = []
    replies = [
        _gemini_reply("", {"id": "c1", "name": "scan_prior_art", "arguments": {"idea": BCI}}),
        _gemini_reply(
            "I found 23 clinical trials on this. About 9,999 hospitals would buy it."
            " Which district will you work from?"
        ),
    ]

    def handle(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        assert req.headers["x-goog-api-key"] == "g-key"
        if not body.get("stream"):  # a review-panel seat: quota used up, rules take over
            return httpx.Response(429, json={"error": {"message": "quota"}})
        sent.append(body)
        return httpx.Response(200, content=replies[len(sent) - 1],
                              headers={"content-type": "text/event-stream"})  # fmt: skip

    s = agent.new_session("Kavya")[0]
    r = _turn(s, BCI, handle)
    assert r["model"] == "model" and r["provider"] == "gemini"
    assert "23 clinical trials" in r["reply"]
    assert "9,999" not in r["reply"] and r["dropped"] == 1  # an invented figure is not said
    assert r["tools_used"][0] == "scan_prior_art"
    assert sent[0]["tools"] and sent[0]["store"] is False
    assert "system_instruction" in sent[0] and sent[0]["input"][-1]["type"] == "user_input"
    # the tool result went back to Gemini, after its own call with the signature intact
    kinds = [st["type"] for st in sent[1]["input"]]
    assert kinds[-2:] == ["function_call", "function_result"]
    assert sent[1]["input"][-2]["signature"] == "sig"
    assert s.usage["input_tokens"] >= 200


def _line(req: httpx.Request) -> str:
    """The one sentence Ollama was asked to reword."""
    return json.loads(req.content)["messages"][1]["content"]


def test_a_used_up_gemini_quota_moves_the_turn_to_ollama(monkeypatch):
    st = get_settings()
    monkeypatch.setattr(st, "gemini_api_key", "g-key")
    monkeypatch.setattr(st, "ollama_model", "gemma3:4b")
    asked: list[str] = []

    def handle(req: httpx.Request) -> httpx.Response:
        if "googleapis" in str(req.url):
            asked.append("gemini")
            return httpx.Response(429, json={"error": {"message": "quota"}})
        body = json.loads(req.content)
        asked.append(_line(req))
        assert body["model"] == "gemma3:4b" and body["messages"][0]["role"] == "system"
        # a model that runs on: only its first sentence is taken
        return httpx.Response(200, content=_ndjson(f"Kavya, {_line(req)} Also, great idea!"))

    s = agent.new_session("Kavya")[0]
    r = _turn(s, BCI, handle)
    lines = [a for a in asked if a != "gemini"]
    assert asked[0] == "gemini" and len(lines) >= 3  # one sentence of the reply per call
    assert r["provider"] == "ollama" and r["model"] == "model"
    assert "Kavya, I found 23 clinical trials" in r["reply"]
    assert "great idea" not in r["reply"]
    assert r["reply"].rstrip().endswith("?")  # the question survives, last
    assert s.messages[-1] == {"role": "assistant", "content": r["reply"]}


def test_ollama_rewording_is_fact_checked_and_falls_back_sentence_by_sentence(monkeypatch):
    monkeypatch.setattr(get_settings(), "ollama_model", "gemma3:4b")

    def handle(req: httpx.Request) -> httpx.Response:
        line = _line(req)
        if "clinical trials" in line:  # an invented figure in place of the real one
            return httpx.Response(200, content=_ndjson("It will earn ₹73 lakh in a year."))
        return httpx.Response(200, content=_ndjson(f"“{line}”"))  # quoted, as small models do

    s = agent.new_session("Kavya")[0]
    r = _turn(s, BCI, handle)
    assert "73 lakh" not in r["reply"] and r["dropped"] == 1
    assert "I found 23 clinical trials" in r["reply"]  # the code's sentence instead
    assert "“" not in r["reply"]

    def down(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("ollama is not running")

    s2 = agent.new_session("Kavya")[0]
    r2 = _turn(s2, BCI, down)
    assert r2["model"] == "offline (model failed)"
    assert "23 clinical trials" in r2["reply"]  # the code's own reply, unchanged
    assert PROVIDERS["ollama"].breaker.failures  # counted once, not once per sentence
    assert len(PROVIDERS["ollama"].breaker.failures) == 1


def test_the_reply_follows_the_founders_language_with_a_model(monkeypatch):
    monkeypatch.setattr(get_settings(), "ollama_model", "gemma3:4b")
    seen: list[str] = []

    def handle(req: httpx.Request) -> httpx.Response:
        seen.append(json.loads(req.content)["messages"][0]["content"])
        if "clinical trials" in _line(req):  # a sentence repeated in English: not said
            return httpx.Response(200, content=_ndjson("(Clinical trials) I found trials."))
        return httpx.Response(200, content=_ndjson("சரி, எந்த மாவட்டத்தில் தொடங்குவீர்கள்? (Sari, entha?)"))

    async def go():
        async with _transport(handle) as c:
            return [ev async for ev in agent.turn_stream(s, BCI, client=c, language="ta-IN")]

    s = agent.new_session("Kavya")[0]
    events = asyncio.run(go())
    said = [e["data"] for e in events if e["event"] == "sentence"]
    assert events[0]["data"]["reply_language"] == "ta-IN"
    assert "Reply in Tamil" in seen[0] and "Tamil script only" in seen[0]
    assert "சரி, எந்த மாவட்டத்தில் தொடங்குவீர்கள்?" in said  # the bracketed transliteration gone
    assert not any("Sari" in x for x in said)
    assert any("23 clinical trials" in x for x in said)  # the English repeat replaced by the code's
    assert events[-1]["data"]["language"] == "ta-IN"


# ---- Gemini's voice -------------------------------------------------------------------------


def _audio_reply(raw: bytes) -> dict:
    part = {"type": "audio", "mime_type": "audio/l16", "data": base64.b64encode(raw).decode()}
    return {"steps": [{"type": "model_output", "content": [part]}]}


async def test_gemini_speaks_any_sentence_and_caches_it(client, monkeypatch, tmp_path):
    from app.routers import voice

    st = get_settings()
    monkeypatch.setattr(st, "sarvam_api_key", "")
    monkeypatch.setattr(st, "gemini_api_key", "g-key")
    monkeypatch.setattr(st, "voice_cache_dir", str(tmp_path))
    gemini_tts.breaker.succeed()
    sent: list[dict] = []

    def handle(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        sent.append(body)
        if body["input"][0]["content"][0]["text"] == "quota":
            return httpx.Response(429, json={"error": {"message": "quota"}})
        return httpx.Response(200, json=_audio_reply(b"\x01\x00" * 2400))

    monkeypatch.setattr(voice, "_client", _transport(handle))
    status = (await client.get("/api/v1/voice/status")).json()
    assert status["speech"] == "gemini" and status["voice"]["ta-IN"] == st.gemini_tts_voice_ta

    text = "உங்கள் யோசனை நன்றாக இருக்கிறது."
    r = await client.post("/api/v1/voice/speak", json={"text": text, "language": "ta-IN"})
    assert r.status_code == 200 and r.content[:4] == b"RIFF"  # raw PCM got a WAV header
    body = sent[0]
    assert body["generation_config"]["speech_config"] == [{"voice": st.gemini_tts_voice_ta}]
    part = body["input"][0]["content"][0]
    assert part["text"] == text and part["annotations"][0]["style"] == st.gemini_tts_style
    await client.post("/api/v1/voice/speak", json={"text": text, "language": "ta-IN"})
    assert len(sent) == 1  # the second time from the cache

    # quota used up: no browser voice, the sentence is shown instead
    r = await client.post("/api/v1/voice/speak", json={"text": "quota", "language": "en-IN"})
    assert r.status_code == 204
    gemini_tts.breaker.succeed()
    monkeypatch.setattr(voice, "_client", None)
