"""The mentor's fixed sentences in Tamil and Hindi: complete, in the right script, and used."""

from __future__ import annotations

import json
import re

import httpx
import pytest
from app.agents import ideation as agent
from app.core.config import get_settings
from app.elicitation.slots import SLOTS
from app.voice import phrasebook

from tests.unit.test_ideation_agent import BCI
from tests.unit.test_providers import _env, _line, _ndjson, _turn  # noqa: F401 (fixture)

SCRIPT = {"ta-IN": re.compile("[஀-௿]"), "hi-IN": re.compile("[ऀ-ॿ]")}
MUST = (
    [s.question for s in SLOTS if s.question]
    + phrasebook.FIXED_EN
    + [agent.SEARCHING, agent.PANEL_BUSY]
)


@pytest.mark.parametrize("language", ["ta-IN", "hi-IN"])
def test_every_question_and_fixed_sentence_has_a_translation(language):
    missing = [t for t in MUST if not phrasebook.translation(t, language)]
    assert not missing, f"no {language} for: {missing}"


def test_translations_are_in_their_own_script_and_keep_questions_questions():
    data = json.loads(phrasebook.TRANSLATIONS.read_text(encoding="utf8"))["phrases"]
    for english, t in data.items():
        for language, script in SCRIPT.items():
            assert script.search(t[language]), (language, english)
            assert t[language].rstrip().endswith("?") == english.rstrip().endswith("?"), english
        assert "reviewed" in t  # drafts stay marked until a native speaker checks them


def test_the_recordings_include_tamil_and_hindi():
    rows = phrasebook.wanted()
    tamil = [r for r in rows if r["language"] == "ta-IN"]
    assert len(tamil) > 20 and all(r["voice"] == "Kavitha" for r in tamil)
    assert any(r["voice"] == "Rohit" for r in rows if r["language"] == "hi-IN")


def test_a_tamil_turn_says_fixed_sentences_as_written_without_the_model(monkeypatch):
    monkeypatch.setattr(get_settings(), "ollama_model", "gemma3:4b")
    asked: list[str] = []

    def handle(req: httpx.Request) -> httpx.Response:
        asked.append(_line(req))
        return httpx.Response(200, content=_ndjson("சரி, இது ஒரு சோதனை வாக்கியம்."))

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:
            return [ev async for ev in agent.turn_stream(s, BCI, client=c, language="ta-IN")]

    import asyncio

    s = agent.new_session("Kavya")[0]
    events = asyncio.run(go())
    said = [e["data"] for e in events if e["event"] == "sentence"]
    written = {phrasebook.translation(t, "ta-IN") for t in MUST}
    assert any(x in written for x in said)  # the question, in its written Tamil
    assert not any(a in MUST for a in asked)  # and the model was not asked to translate it
    assert _turn  # (imported helper kept for symmetry with test_providers)
