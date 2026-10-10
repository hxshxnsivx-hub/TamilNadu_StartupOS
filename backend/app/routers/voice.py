"""Voice endpoints: the mentor's voice out, the founder's speech in.

    GET  /api/v1/voice/status       which voice is available, and its languages
    POST /api/v1/voice/speak        one sentence -> audio: a recorded phrase (free, local),
                                    else Sarvam MP3 when a key is set (cached), else 204 (no audio)
                                    and the browser speaks it
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
from app.voice import phrasebook, sarvam

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
    return {
        # who listens: Sarvam when a key is set, otherwise the browser
        "provider": "sarvam" if sarvam.configured() else "browser",
        # who speaks: Sarvam, else the recorded phrasebook with the browser for the rest
        "speech": "sarvam" if sarvam.configured() else "phrasebook" if recorded else "browser",
        "phrases_recorded": recorded,
        "languages": sarvam.LANGUAGES,
        "voice": st.sarvam_tts_speaker if sarvam.configured() else phrasebook.VOICES,
    }


def _cache_path(text: str, language: str) -> Path:
    st = get_settings()
    key = f"{st.sarvam_tts_model}|{st.sarvam_tts_speaker}|{st.sarvam_tts_pace}|{language}|{text}"
    return Path(st.voice_cache_dir) / (hashlib.sha1(key.encode()).hexdigest() + ".mp3")


@router.post("/speak")
async def speak(body: SpeakIn) -> Response:
    # without Sarvam, the recorded phrases speak; with it, one voice says everything
    if not sarvam.configured() and (recorded := phrasebook.lookup(body.text, body.language)):
        return Response(
            content=recorded.read_bytes(),
            media_type="audio/wav",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    if not sarvam.configured():
        return Response(status_code=204)  # no recording of this sentence: the browser says it
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
