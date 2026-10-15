"""Try free, local mentor voices in Tamil, Hindi and English, and time them.

    python try_voices.py            # Indic Parler-TTS (the candidate) + MMS (fast baseline)
    python try_voices.py --only mms # just the small, fast baseline

Writes out/<model>_<lang>_<voice>.wav and out/report.md. Every voice speaks the
same mentor line, so you can compare by ear; the report gives seconds to
generate per second of speech (below 1.0 means faster than it can be spoken).
Runs on the CPU; the first run downloads the models (Parler about 3.7 GB).
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import soundfile as sf
import torch

OUT = Path(__file__).parent / "out"

# One mentor line per language: a question back, as the agent speaks.
LINES = {
    "ta": "வணக்கம். உங்கள் யோசனை நன்றாக இருக்கிறது. முதலில், உங்கள் முதல் வாடிக்கையாளர் யார் என்று சொல்லுங்கள்.",
    "hi": "नमस्ते। आपका विचार अच्छा है। पहले बताइए, आपका पहला ग्राहक कौन होगा?",
    "en": "Hello. Your idea has promise. First, tell me who your very first customer will be.",
}

# Indic Parler-TTS: the description sets the voice. Named speakers are the
# model card's recommended ones for each language; the rest is the mentor style.
STYLE = (
    "speaks warmly and calmly at a slightly slow pace, with a clear, close recording"
    " and no background noise."
)
PARLER_VOICES = {
    "ta": ["Jaya", "Kavitha"],
    "hi": ["Rohit", "Divya"],
    "en": ["Thoma", "Mary"],
}
MMS = {"ta": "facebook/mms-tts-tam", "hi": "facebook/mms-tts-hin", "en": "facebook/mms-tts-eng"}


def _write(name: str, audio, rate: int, took: float) -> dict:
    path = OUT / f"{name}.wav"
    sf.write(path, audio, rate)
    seconds = len(audio) / rate
    row = {"file": path.name, "audio_s": seconds, "took_s": took, "rtf": took / max(seconds, 0.01)}
    print(f"  {path.name}: {seconds:.1f}s of speech in {took:.1f}s (x{row['rtf']:.2f})")
    return row


def run_parler() -> list[dict]:
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    t = time.perf_counter()
    model = ParlerTTSForConditionalGeneration.from_pretrained("ai4bharat/indic-parler-tts")
    tok = AutoTokenizer.from_pretrained("ai4bharat/indic-parler-tts")
    desc_tok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    print(f"Parler loaded in {time.perf_counter() - t:.0f}s")
    rows = []
    for lang, voices in PARLER_VOICES.items():
        for voice in voices:
            d = desc_tok(f"{voice} {STYLE}", return_tensors="pt")
            p = tok(LINES[lang], return_tensors="pt")
            t = time.perf_counter()
            with torch.inference_mode():
                audio = model.generate(
                    input_ids=d.input_ids,
                    attention_mask=d.attention_mask,
                    prompt_input_ids=p.input_ids,
                    prompt_attention_mask=p.attention_mask,
                )
            took = time.perf_counter() - t
            rows.append(
                _write(
                    f"parler_{lang}_{voice.lower()}",
                    audio.numpy().squeeze(),
                    model.config.sampling_rate,
                    took,
                )
            )
    return rows


def run_mms() -> list[dict]:
    from transformers import AutoTokenizer, VitsModel

    rows = []
    for lang, repo in MMS.items():
        model, tok = VitsModel.from_pretrained(repo), AutoTokenizer.from_pretrained(repo)
        t = time.perf_counter()
        with torch.inference_mode():
            audio = model(**tok(LINES[lang], return_tensors="pt")).waveform
        took = time.perf_counter() - t
        rows.append(
            _write(f"mms_{lang}", audio.numpy().squeeze(), model.config.sampling_rate, took)
        )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["parler", "mms"])
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    torch.set_num_threads(max(1, (torch.get_num_threads() or 4)))
    rows: list[dict] = []
    if args.only in (None, "mms"):
        print("MMS (fast baseline, non-commercial licence)")
        rows += run_mms()
    if args.only in (None, "parler"):
        print("Indic Parler-TTS (candidate, Apache 2.0)")
        rows += run_parler()
    lines = [
        "| file | speech (s) | generated in (s) | x real time |",
        "|---|---|---|---|",
        *(
            f"| {r['file']} | {r['audio_s']:.1f} | {r['took_s']:.1f} | {r['rtf']:.2f} |"
            for r in rows
        ),
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
