"""Gemini text-to-speech: the mentor's voice for any sentence, on the free tier.

Same key as the conversation (GEMINI_API_KEY). The language is detected from
the text, so Tamil, Hindi and English each come out in their own sounds; the
voice is chosen per language and the delivery (calm, warm, unhurried) is set
once as a style for every sentence.

    POST https://generativelanguage.googleapis.com/v1beta/interactions
    {"model": ..., "input": [{"type": "user_input", "content": [{"type": "text",
      "text": <verbatim>, "annotations": [{"type": "speech_metadata", "style": ...}]}]}],
     "response_format": {"type": "audio", "mime_type": "audio/wav"},
     "generation_config": {"speech_config": [{"voice": ...}]}}
    -> steps[].content[] of type audio, base64 in "data" (24 kHz mono 16-bit)
"""

from __future__ import annotations

import base64
import io
import wave

import httpx

from app.core.config import get_settings
from app.services.breaker import Breaker

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
RATE = 24000
breaker = Breaker("gemini-tts")


class SpeechError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def configured() -> bool:
    return bool(get_settings().gemini_api_key)


def ready() -> bool:
    return configured() and breaker.allow()


def voice_for(language: str) -> str:
    st = get_settings()
    return {
        "ta-IN": st.gemini_tts_voice_ta,
        "hi-IN": st.gemini_tts_voice_hi,
    }.get(language, st.gemini_tts_voice_en)


def _wav(pcm: bytes, rate: int = RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def _audio(data: dict) -> bytes:
    """The last audio part of the reply, as WAV (raw PCM gets a header)."""
    parts = [
        c
        for step in data.get("steps") or []
        for c in step.get("content") or []
        if c.get("type") == "audio" and c.get("data")
    ]
    if not parts:
        raise SpeechError(502, "Gemini returned no audio")
    raw = base64.b64decode(parts[-1]["data"])
    return raw if raw[:4] == b"RIFF" else _wav(raw)


async def speak(text: str, language: str, client: httpx.AsyncClient) -> bytes:
    st = get_settings()
    body = {
        "model": st.gemini_tts_model,
        "input": [
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                        "annotations": [{"type": "speech_metadata", "style": st.gemini_tts_style}],
                    }
                ],
            }
        ],
        "response_format": {"type": "audio", "mime_type": "audio/wav", "sample_rate": RATE},
        "generation_config": {"speech_config": [{"voice": voice_for(language)}]},
        "store": False,
    }
    r = await client.post(
        URL,
        json=body,
        headers={"x-goog-api-key": st.gemini_api_key, "content-type": "application/json"},
    )
    if r.status_code == 429:
        raise SpeechError(429, "Gemini voice: free quota reached for now")
    if r.status_code != 200:
        try:
            msg = (r.json().get("error") or {}).get("message") or r.text[:200]
        except ValueError:
            msg = r.text[:200]
        raise SpeechError(r.status_code, f"Gemini voice {r.status_code}: {msg}")
    return _audio(r.json())
