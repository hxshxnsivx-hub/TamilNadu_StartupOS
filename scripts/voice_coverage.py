"""How much of a real conversation the recorded phrasebook covers.

    cd backend && python ../scripts/voice_coverage.py [--top 40] [--write]

Replays the ten quality-set conversations offline (tests/eval), splits every
mentor reply into sentences as the agent does, and reports the share of
sentences that have a recording, and the unrecorded sentences that recur
across different ideas.

--write saves every sentence said in 2+ different ideas, minus any with a
figure or a name, to backend/app/voice/data/recurring.json; the phrasebook
then lists them for recording (voice-worker/record_phrases.py).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.voice import phrasebook  # noqa: E402
from tests.eval.runner import Result, converse, load_fixture, load_ideas, offline  # noqa: E402

MIN_IDEAS = 2
# a figure, an amount or the founder's name belongs to one founder: never recorded
PERSONAL = re.compile(r"\d|₹|\bEval\b|Vanakkam")


async def spoken() -> dict[str, list[str]]:
    out = {}
    for idea in load_ideas():
        result = Result(idea["id"])
        with offline(load_fixture(idea["id"])):
            await converse(idea, result)
        out[idea["id"]] = [
            s
            for who, text in result.transcript
            if who == "agent"
            for s in phrasebook._sentences(text)
        ]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    said = asyncio.run(spoken())

    def recorded(s: str) -> bool:
        return phrasebook.lookup(s, "en-IN") is not None

    total = sum(len(v) for v in said.values())
    covered = sum(1 for v in said.values() for s in v if recorded(s))
    print(f"{covered} of {total} sentences recorded ({covered / max(total, 1):.0%})")
    for idea, sents in said.items():
        print(f"  {idea:20} {sum(1 for s in sents if recorded(s)):3}/{len(sents)}")

    ideas_per: dict[str, set[str]] = defaultdict(set)
    count: Counter[str] = Counter()
    for idea, sents in said.items():
        for s in sents:
            ideas_per[s].add(idea)
            count[s] += 1
    recurring = sorted(
        (s for s in count if len(ideas_per[s]) >= MIN_IDEAS),
        key=lambda s: (-len(ideas_per[s]), -count[s], s),
    )
    missing = [s for s in recurring if not recorded(s)]
    print(f"\nUnrecorded sentences said in {MIN_IDEAS}+ different ideas ({len(missing)}):")
    for s in missing[: args.top]:
        print(f"  [{len(ideas_per[s])} ideas, {count[s]}x] {s}")

    if args.write:
        fixed = {r["text"] for r in phrasebook.wanted() if r["language"] == "en-IN"}
        prior = (
            set(json.loads(phrasebook.RECURRING.read_text("utf8")))
            if phrasebook.RECURRING.exists()
            else set()
        )
        keep = sorted({s for s in recurring if not PERSONAL.search(s)} - (fixed - prior))
        phrasebook.RECURRING.parent.mkdir(parents=True, exist_ok=True)
        phrasebook.RECURRING.write_text(
            json.dumps(keep, ensure_ascii=False, indent=1) + "\n", encoding="utf8"
        )
        print(f"\n{len(keep)} recurring sentences -> {phrasebook.RECURRING}")


if __name__ == "__main__":
    main()
