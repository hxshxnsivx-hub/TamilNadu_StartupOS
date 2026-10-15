"""Sarvam AI speech: text-to-speech (Bulbul) and speech-to-text (Saaras).

REST endpoints, as documented at docs.sarvam.ai (checked 2026-10-10):

    POST https://api.sarvam.ai/text-to-speech   JSON  -> {"audios": [base64 audio]}
    POST https://api.sarvam.ai/speech-to-text   multipart file -> {"transcript", "language_code"}
    auth header: api-subscription-key

The key stays on the server; the browser only ever talks to Vanigam.
"""

from __future__ import annotations

import base64
import json

import httpx

from app.core.config import get_settings

TTS_URL = "https://api.sarvam.ai/text-to-speech"
STT_URL = "https://api.sarvam.ai/speech-to-text"

LANGUAGES = {"ta-IN": "Tamil", "en-IN": "English", "hi-IN": "Hindi"}
TTS_MAX_CHARS = 1500  # the lowest documented per-request limit across Bulbul models

# Words a Tamil Nadu founder says that a general recogniser may miss.
# Saaras v4 accepts up to 50 key terms of up to 64 characters each.
KEYTERMS = [
    "Vanigam", "StartupTN", "TANSEED", "DPIIT", "MSME", "Udyam", "GST", "FSSAI", "CDSCO",
    "PMEGP", "NEEDS", "UYEGP", "CGTMSE", "Mudra", "SIDBI", "incubator", "prototype", "MVP",
    "pilot", "proof of concept", "co-founder", "EEG", "brain-computer interface", "IoT",
    "SaaS", "fintech", "agritech", "edtech", "FPO", "Tiruppur", "Coimbatore", "Madurai",
    "Tiruchirappalli", "Chennai", "Salem", "Erode", "Hosur", "lakh", "crore", "patent",
    "trademark", "nurse call", "copra", "jasmine", "banana", "coir", "knitwear",
]  # fmt: skip


class SpeechError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def configured() -> bool:
    return bool(get_settings().sarvam_api_key)


def _headers() -> dict[str, str]:
    return {"api-subscription-key": get_settings().sarvam_api_key}


def _error(r: httpx.Response) -> SpeechError:
    try:
        msg = r.json().get("error", {}).get("message") or r.text[:200]
    except ValueError:
        msg = r.text[:200]
    return SpeechError(r.status_code, f"Sarvam {r.status_code}: {msg}")


async def speak(text: str, language: str, client: httpx.AsyncClient) -> bytes:
    """One sentence to MP3 audio in the mentor's voice."""
    st = get_settings()
    body = {
        "text": text[:TTS_MAX_CHARS],
        "language_code": language if language in LANGUAGES else "en-IN",
        "model": st.sarvam_tts_model,
        "speaker": st.sarvam_tts_speaker,
        "pace": st.sarvam_tts_pace,
        "speech_sample_rate": 24000,
        "output_audio_codec": "mp3",
    }
    r = await client.post(TTS_URL, json=body, headers=_headers())
    if r.status_code != 200:
        raise _error(r)
    audios = r.json().get("audios") or []
    if not audios:
        raise SpeechError(502, "Sarvam returned no audio")
    return base64.b64decode(audios[0])


async def transcribe(
    audio: bytes, filename: str, content_type: str, language: str | None, client: httpx.AsyncClient
) -> dict:
    """One utterance to text. `language` None or "auto" lets Saaras detect it."""
    st = get_settings()
    data = {
        "model": st.sarvam_stt_model,
        "language_code": language if language in LANGUAGES else "unknown",
    }
    if st.sarvam_stt_model.startswith("saaras:v4"):
        data["keyterms"] = json.dumps(KEYTERMS[:50])
    files = {"file": (filename, audio, content_type)}
    r = await client.post(STT_URL, data=data, files=files, headers=_headers())
    if r.status_code != 200:
        raise _error(r)
    out = r.json()
    lang = out.get("language_code")
    return {
        "text": (out.get("transcript") or "").strip(),
        "language": lang if lang in LANGUAGES else ("en-IN" if lang is None else lang),
        "confidence": out.get("language_probability"),
    }
