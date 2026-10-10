"""Record the mentor's fixed sentences with Indic Parler-TTS, once.

    cd backend && python -m app.voice.phrasebook      # writes phrasebook/wanted.json
    cd voice-worker && .venv/Scripts/python record_phrases.py

Reads phrasebook/wanted.json and writes phrasebook/<key>.wav for every sentence
not yet recorded, so it can be stopped and run again. On a laptop CPU each
sentence takes about a minute: keep the charger in.

Setup, once: python -m venv .venv; .venv/Scripts/pip install -r requirements.txt;
accept the model's terms at huggingface.co/ai4bharat/indic-parler-tts and run
.venv/Scripts/hf auth login with a read token.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import soundfile as sf
import torch

BOOK = Path(__file__).parent / "phrasebook"
STYLE = (
    "speaks warmly and calmly at a slightly slow pace, with a clear, close recording"
    " and no background noise."
)


def main() -> None:
    rows = json.loads((BOOK / "wanted.json").read_text(encoding="utf8"))
    todo = [r for r in rows if not (BOOK / f"{r['key']}.wav").exists()]
    print(f"{len(rows) - len(todo)} of {len(rows)} already recorded; {len(todo)} to go")
    if not todo:
        return

    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    model = ParlerTTSForConditionalGeneration.from_pretrained("ai4bharat/indic-parler-tts")
    tok = AutoTokenizer.from_pretrained("ai4bharat/indic-parler-tts")
    desc_tok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    for i, r in enumerate(todo, 1):
        d = desc_tok(f"{r['voice']} {STYLE}", return_tensors="pt")
        p = tok(r["text"], return_tensors="pt")
        t = time.perf_counter()
        with torch.inference_mode():
            audio = model.generate(
                input_ids=d.input_ids,
                attention_mask=d.attention_mask,
                prompt_input_ids=p.input_ids,
                prompt_attention_mask=p.attention_mask,
            )
        tmp = BOOK / f"{r['key']}.part.wav"  # never leave a half-written recording
        sf.write(tmp, audio.numpy().squeeze(), model.config.sampling_rate)
        tmp.replace(BOOK / f"{r['key']}.wav")
        took = time.perf_counter() - t
        print(f"[{i}/{len(todo)}] {r['language']} {r['voice']}: {r['text']} ({took:.0f}s)")


if __name__ == "__main__":
    main()
