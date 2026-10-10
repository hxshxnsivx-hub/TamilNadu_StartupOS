"""Voice endpoints against a mock Sarvam: requests, caching, errors, no key."""

from __future__ import annotations

import base64
import json

import httpx
import pytest
from app.core.config import get_settings
from app.routers import voice
from app.voice import phrasebook
from httpx import AsyncClient

MP3 = b"ID3fake-mp3-bytes"


@pytest.fixture
def sarvam(monkeypatch, tmp_path):
    st = get_settings()
    monkeypatch.setattr(st, "sarvam_api_key", "sk-test")
    monkeypatch.setattr(st, "voice_cache_dir", str(tmp_path / "voice"))
    sent: list[httpx.Request] = []

    def handle(req: httpx.Request) -> httpx.Response:
        sent.append(req)
        assert req.headers["api-subscription-key"] == "sk-test"
        if req.url.path == "/text-to-speech":
            body = json.loads(req.content)
            if body["text"] == "fail":
                return httpx.Response(429, json={"error": {"message": "quota", "code": "x"}})
            return httpx.Response(200, json={"audios": [base64.b64encode(MP3).decode()]})
        if req.url.path == "/speech-to-text":
            return httpx.Response(
                200,
                json={"transcript": " நான் ஒரு சாதனம் உருவாக்குகிறேன் ", "language_code": "ta-IN",
                      "language_probability": 0.97},
            )  # fmt: skip
        return httpx.Response(404)

    monkeypatch.setattr(voice, "_client", httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    yield sent
    monkeypatch.setattr(voice, "_client", None)


async def test_status_without_a_key_falls_back_to_the_browser(
    client: AsyncClient, monkeypatch, tmp_path
):
    monkeypatch.setattr(get_settings(), "sarvam_api_key", "")
    monkeypatch.setattr(phrasebook, "PHRASEBOOK_DIR", tmp_path)
    r = await client.get("/api/v1/voice/status")
    assert r.json()["provider"] == "browser" and r.json()["speech"] == "browser"
    r = await client.post("/api/v1/voice/speak", json={"text": "Hello", "language": "en-IN"})
    assert r.status_code == 204 and not r.content


async def test_recorded_phrases_speak_without_a_key(client: AsyncClient, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "sarvam_api_key", "")
    monkeypatch.setattr(phrasebook, "PHRASEBOOK_DIR", tmp_path)
    (tmp_path / f"{phrasebook.key('Is that right?', 'en-IN')}.wav").write_bytes(b"RIFFwav")
    st = (await client.get("/api/v1/voice/status")).json()
    assert st["speech"] == "phrasebook" and st["provider"] == "browser"  # listening stays local
    assert st["phrases_recorded"] == 1 and st["voice"]["en-IN"] == "Thoma"
    # spacing does not matter; the sentence does
    r = await client.post(
        "/api/v1/voice/speak", json={"text": "  Is that   right? ", "language": "en-IN"}
    )
    assert r.status_code == 200 and r.content == b"RIFFwav"
    assert r.headers["content-type"] == "audio/wav"
    r = await client.post(
        "/api/v1/voice/speak", json={"text": "Is that right?", "language": "ta-IN"}
    )
    assert r.status_code == 204  # recorded in English only


def test_the_phrasebook_lists_every_fixed_question_once():
    rows = phrasebook.wanted()
    texts = {(r["language"], r["text"]) for r in rows}
    assert ("en-IN", "Which district will you operate from?") in texts
    assert ("en-IN", "Is that right?") in texts and ("ta-IN", "சரி.") in texts
    assert len(rows) == len({r["key"] for r in rows})
    assert all(r["voice"] == phrasebook.VOICES[r["language"]] for r in rows)


async def test_speak_sends_the_mentor_voice_and_caches_repeats(client: AsyncClient, sarvam):
    r = await client.post("/api/v1/voice/speak", json={"text": "சரி.", "language": "ta-IN"})
    assert r.status_code == 200 and r.content == MP3
    assert r.headers["content-type"] == "audio/mpeg"
    body = json.loads(sarvam[0].content)
    st = get_settings()
    assert body["language_code"] == "ta-IN" and body["speaker"] == st.sarvam_tts_speaker
    assert body["model"] == st.sarvam_tts_model and body["output_audio_codec"] == "mp3"
    assert body["pace"] == st.sarvam_tts_pace
    await client.post("/api/v1/voice/speak", json={"text": "சரி.", "language": "ta-IN"})
    assert len(sarvam) == 1  # second time from the cache


async def test_speak_reports_provider_errors_and_rejects_other_languages(
    client: AsyncClient, sarvam
):
    r = await client.post("/api/v1/voice/speak", json={"text": "fail", "language": "en-IN"})
    assert r.status_code == 502 and "quota" in r.json()["error_message"]
    r = await client.post("/api/v1/voice/speak", json={"text": "hi", "language": "fr-FR"})
    assert r.status_code == 422


async def test_transcribe_detects_the_language_and_sends_key_terms(client: AsyncClient, sarvam):
    r = await client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("turn.webm", b"\x1aE\xdf\xa3fake", "audio/webm")},
        data={"language": "auto"},
    )
    out = r.json()
    assert r.status_code == 200 and out["language"] == "ta-IN"
    assert out["text"] == "நான் ஒரு சாதனம் உருவாக்குகிறேன்"
    req = sarvam[0].content.decode("utf8", "ignore")
    assert 'name="language_code"' in req and "unknown" in req  # auto-detect
    assert "TANSEED" in req  # key terms bias recognition toward startup words


async def test_transcribe_rejects_empty_audio(client: AsyncClient, sarvam):
    r = await client.post(
        "/api/v1/voice/transcribe", files={"file": ("turn.webm", b"", "audio/webm")}
    )
    assert r.status_code == 400
