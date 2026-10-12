"""Record the mentor's fixed sentences with Indic Parler-TTS, once.

    cd backend && python -m app.voice.phrasebook      # writes phrasebook/wanted.json
    cd voice-worker && .venv/Scripts/python record_phrases.py
    .venv/Scripts/python record_phrases.py --polish   # re-polish existing recordings only

Reads phrasebook/wanted.json and writes phrasebook/<key>.wav for every sentence
not yet recorded, so it can be stopped and run again. On a laptop CPU each
sentence takes 15 seconds to a minute on the charger, several times longer on
battery.

Every recording is polished: silence trimmed at both ends (so the mentor starts
speaking as soon as the audio plays), the same loudness for every sentence, and
a short fade so nothing clicks. A take whose length is far off what the text
needs (the model sometimes mumbles or runs on) is recorded again.

Setup, once: python -m venv .venv; .venv/Scripts/pip install -r requirements.txt;
accept the model's terms at huggingface.co/ai4bharat/indic-parler-tts and run
.venv/Scripts/hf auth login with a read token.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

BOOK = Path(__file__).parent / "phrasebook"
STYLE = (
    "speaks warmly and calmly at a slightly slow pace, with a clear, close recording"
    " and no background noise."
)

TARGET_RMS = 0.1  # about -20 dBFS for the spoken part
PEAK_MAX = 0.97
LEAD_S, TAIL_S, FADE_S = 0.06, 0.15, 0.01
TAKES = 3
# Plausible speaking rate, characters per second (Tamil and Hindi script is denser).
CHARS_PER_S = {"en-IN": 13.0, "hi-IN": 10.0, "ta-IN": 9.0}


def polish(audio: np.ndarray, rate: int) -> np.ndarray:
    audio = audio.astype(np.float32)
    peak = float(np.abs(audio).max()) or 1.0
    frame = max(1, int(rate * 0.01))
    n = len(audio) // frame
    if n == 0:
        return audio
    levels = np.abs(audio[: n * frame]).reshape(n, frame).max(axis=1)
    voiced = np.nonzero(levels > 0.05 * peak)[0]
    if len(voiced):
        start = max(0, voiced[0] * frame - int(LEAD_S * rate))
        end = min(len(audio), (voiced[-1] + 1) * frame + int(TAIL_S * rate))
        audio = audio[start:end]
    body = audio[np.abs(audio) > 0.05 * peak]
    rms = float(np.sqrt(np.mean(body**2))) if len(body) else 0.0
    if rms > 0:
        audio = audio * min(TARGET_RMS / rms, PEAK_MAX / (float(np.abs(audio).max()) or 1.0))
    fade = min(len(audio) // 2, int(FADE_S * rate))
    if fade:
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        audio[:fade] *= ramp
        audio[-fade:] *= ramp[::-1]
    return audio


def plausible(seconds: float, text: str, language: str) -> bool:
    expected = max(0.6, len(text) / CHARS_PER_S.get(language, 12.0))
    return 0.45 * expected <= seconds <= 2.2 * expected


def polish_existing() -> None:
    for path in sorted(BOOK.glob("*.wav")):
        if path.name.endswith(".part.wav"):
            continue
        audio, rate = sf.read(path, dtype="float32")
        sf.write(path, polish(audio, rate), rate)
    print("polished", len(list(BOOK.glob("*.wav"))), "recordings")


def record(rows: list[dict]) -> None:
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    model = ParlerTTSForConditionalGeneration.from_pretrained("ai4bharat/indic-parler-tts")
    tok = AutoTokenizer.from_pretrained("ai4bharat/indic-parler-tts")
    desc_tok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    rate = model.config.sampling_rate
    for i, r in enumerate(rows, 1):
        d = desc_tok(f"{r['voice']} {STYLE}", return_tensors="pt")
        p = tok(r["text"], return_tensors="pt")
        t = time.perf_counter()
        for take in range(TAKES):
            torch.manual_seed(int(r["key"][:8], 16) + take)  # the same take every run
            with torch.inference_mode():
                raw = model.generate(
                    input_ids=d.input_ids,
                    attention_mask=d.attention_mask,
                    prompt_input_ids=p.input_ids,
                    prompt_attention_mask=p.attention_mask,
                )
            audio = polish(raw.numpy().squeeze(), rate)
            seconds = len(audio) / rate
            if plausible(seconds, r["text"], r["language"]):
                break
            print(f"  take {take + 1}: {seconds:.1f}s is off for this text; again")
        tmp = BOOK / f"{r['key']}.part.wav"  # never leave a half-written recording
        sf.write(tmp, audio, rate)
        tmp.replace(BOOK / f"{r['key']}.wav")
        took = time.perf_counter() - t
        print(f"[{i}/{len(rows)}] {r['language']} {r['voice']}: {r['text']} ({took:.0f}s)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--polish", action="store_true", help="only re-polish existing recordings")
    args = ap.parse_args()
    if args.polish:
        return polish_existing()
    rows = json.loads((BOOK / "wanted.json").read_text(encoding="utf8"))
    todo = [r for r in rows if not (BOOK / f"{r['key']}.wav").exists()]
    print(f"{len(rows) - len(todo)} of {len(rows)} already recorded; {len(todo)} to go")
    if todo:
        record(todo)


if __name__ == "__main__":
    main()
