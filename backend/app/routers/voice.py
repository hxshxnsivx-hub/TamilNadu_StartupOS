"""Voice endpoints: the mentor's voice out, the founder's speech in.

    GET  /api/v1/voice/status       which voice is available, and its languages
    POST /api/v1/voice/speak        one or more sentences -> the mentor's voice:
                                    Sarvam (paid, if a key is set), else Gemini (free
                                    tier), else a recorded phrase; else 204 and the
                                    sentence is shown, not spoken
    POST /api/v1/voice/transcribe   one utterance (audio file) -> text + detected language

Audio is passed straight through and never stored; only synthesised speech
for repeated sentences is cached, keyed by a hash of text, language and voice.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.voice import gemini_tts, phrasebook, sarvam

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

MAX_UPLOAD = 5 * 1024 * 1024  # about 30 s of compressed speech; Sarvam's REST limit is ~30 s
_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=20)
    return _client


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=sarvam.TTS_MAX_CHARS)
    language: str = Field(default="en-IN", pattern=r"^(ta|en|hi)-IN$")


@router.get("/status")
async def status() -> dict:
    st = get_settings()
    recorded = phrasebook.recorded()
    if sarvam.configured():
        speech, voice = "sarvam", st.sarvam_tts_speaker
    elif gemini_tts.configured():
        speech, voice = "gemini", {lang: gemini_tts.voice_for(lang) for lang in sarvam.LANGUAGES}
    elif recorded:
        speech, voice = "phrasebook", phrasebook.VOICES
    else:
        speech, voice = "none", None  # the mentor's words are shown, not spoken
    return {
        # who listens: Sarvam when a key is set, otherwise the browser
        "provider": "sarvam" if sarvam.configured() else "browser",
        "speech": speech,
        "phrases_recorded": recorded,
        "languages": sarvam.LANGUAGES,
        "voice": voice,
    }


def _cache_path(text: str, language: str) -> Path:
    st = get_settings()
    key = f"{st.sarvam_tts_model}|{st.sarvam_tts_speaker}|{st.sarvam_tts_pace}|{language}|{text}"
    return Path(st.voice_cache_dir) / (hashlib.sha1(key.encode()).hexdigest() + ".mp3")


def _gemini_cache_path(text: str, language: str) -> Path:
    st = get_settings()
    voice = gemini_tts.voice_for(language)
    key = f"gemini|{st.gemini_tts_model}|{voice}|{st.gemini_tts_style}|{language}|{text}"
    return Path(st.voice_cache_dir) / (hashlib.sha1(key.encode()).hexdigest() + ".wav")


async def _gemini(text: str, language: str) -> bytes | None:
    """Gemini's voice, cached so a repeated sentence costs one request ever. None
    when it cannot speak now (quota, outage): the next voice down takes over."""
    path = _gemini_cache_path(text, language)
    if path.exists():
        return path.read_bytes()
    if not gemini_tts.ready():
        return None
    try:
        audio = await gemini_tts.speak(text, language, _http())
    except (gemini_tts.SpeechError, httpx.HTTPError) as exc:
        gemini_tts.breaker.fail(type(exc).__name__)
        return None
    gemini_tts.breaker.succeed()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    return audio


@router.post("/speak")
async def speak(body: SpeakIn) -> Response:
    text = body.text.strip()
    if not sarvam.configured():
        if gemini_tts.configured() and (audio := await _gemini(text, body.language)):
            return Response(content=audio, media_type="audio/wav")
        if recorded := phrasebook.lookup(text, body.language):
            return Response(
                content=recorded.read_bytes(),
                media_type="audio/wav",
                headers={"Cache-Control": "public, max-age=86400"},
            )
        return Response(status_code=204)  # no voice for this now: the words are shown
    path = _cache_path(body.text.strip(), body.language)
    if path.exists():
        audio = path.read_bytes()
    else:
        try:
            audio = await sarvam.speak(body.text.strip(), body.language, _http())
        except sarvam.SpeechError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=504, detail="The voice service did not answer") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(audio)
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(default="auto"),
) -> dict:
    if not sarvam.configured():
        raise HTTPException(status_code=503, detail="No speech service configured")
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio")
    if len(audio) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Speak in shorter turns (under 30 seconds)")
    try:
        return await sarvam.transcribe(
            audio,
            file.filename or "speech.webm",
            file.content_type or "audio/webm",
            None if language == "auto" else language,
            _http(),
        )
    except sarvam.SpeechError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=504, detail="The speech service did not answer") from exc
