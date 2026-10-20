"""The mentor's fixed sentences, recorded once in a local voice and played back.

Free local voices (Indic Parler-TTS) are far too slow on a laptop to speak live,
but most of what the offline mentor says never changes: the questions, the
greeting, the confirmation, the short acknowledgements. Those are recorded once
by voice-worker/record_phrases.py and served from disk, instantly. Any other
sentence is not here, and the browser's own voice speaks it.

    python -m app.voice.phrasebook     # write the list of sentences to record

Files, in PHRASEBOOK_DIR:
    wanted.json        the sentences to record (written here)
    <key>.wav          one recording per sentence (written by the voice worker)
"""

from __future__ import annotations

import hashlib
import json
from functools import cache
from pathlib import Path

from app.agents.grounding import SentenceSplitter
from app.elicitation.slots import SLOTS

PHRASEBOOK_DIR = Path(__file__).resolve().parents[3] / "voice-worker" / "phrasebook"

# The chosen voices, one per language (from the listening test of 2026-10-10).
VOICES = {"ta-IN": "Kavitha", "hi-IN": "Rohit", "en-IN": "Thoma"}

# Kept identical to ACKS in frontend/src/voice/mentorVoice.ts.
ACKS = {
    "ta-IN": ["சரி.", "ம்ம், சரி."],
    "hi-IN": ["अच्छा।", "हाँ, ठीक है।"],
    "en-IN": ["Okay.", "Mm, I see."],
}

# The fixed sentences in Tamil and Hindi, keyed by the English (drafts until a
# native speaker reviews them; see the file).
TRANSLATIONS = Path(__file__).parent / "data" / "translations.json"


@cache
def _translations() -> dict[str, dict]:
    if not TRANSLATIONS.exists():
        return {}
    return json.loads(TRANSLATIONS.read_text(encoding="utf8"))["phrases"]


def translation(text: str, language: str) -> str | None:
    """The fixed sentence in Tamil or Hindi, or None."""
    return _translations().get(normalise(text), {}).get(language)


# Template sentences that recur across conversations, found by replaying the
# quality set (scripts/voice_coverage.py --write); none holds a figure or a name.
RECURRING = Path(__file__).parent / "data" / "recurring.json"

# Fixed English sentences from the agent (app/agents/ideation.py, app/elicitation).
FIXED_EN = [
    "Tell me about the idea you are working on, in your own words.",
    "It can be a product, a machine, an app or a service.",
    "I will look up what already exists for it, papers, patents, projects and products,"
    " and we will shape it together.",
    "You chose private mode, so I will search only Vanigam's own data.",
    "Here is what I understood.",
    "Is that right?",
    "Sorry, I didn't catch that.",
]


def normalise(text: str) -> str:
    return " ".join(text.split())


def key(text: str, language: str) -> str:
    return hashlib.sha1(f"{language}|{normalise(text)}".encode()).hexdigest()[:20]


def _sentences(text: str) -> list[str]:
    sp = SentenceSplitter()
    return sp.feed(text) + sp.flush()


def wanted() -> list[dict]:
    """Every sentence worth recording, split the way the agent splits its replies."""
    rows: dict[str, dict] = {}

    def add(text: str, language: str) -> None:
        for s in _sentences(text):
            k = key(s, language)
            rows[k] = {"key": k, "language": language, "voice": VOICES[language], "text": s}

    for language, acks in ACKS.items():
        for a in acks:
            add(a, language)
    recurring = json.loads(RECURRING.read_text(encoding="utf8")) if RECURRING.exists() else []
    # each slot's question in every conversation's words (R089)
    questions = [s.question for s in SLOTS if s.question] + [q for s in SLOTS for _, q in s.by_mode]
    for text in FIXED_EN + questions + recurring:
        add(text, "en-IN")
    for langs in _translations().values():  # the same sentences for Kavitha and Rohit
        for language in ("ta-IN", "hi-IN"):
            if langs.get(language):
                add(langs[language], language)
    return list(rows.values())


def lookup(text: str, language: str) -> Path | None:
    path = PHRASEBOOK_DIR / f"{key(text, language)}.wav"
    return path if path.exists() else None


def recorded() -> int:
    return len(list(PHRASEBOOK_DIR.glob("*.wav"))) if PHRASEBOOK_DIR.exists() else 0


if __name__ == "__main__":
    PHRASEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    rows = wanted()
    out = PHRASEBOOK_DIR / "wanted.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"{len(rows)} sentences -> {out}")
