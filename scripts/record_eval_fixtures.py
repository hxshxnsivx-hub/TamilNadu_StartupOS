"""Record research results for the quality test set (backend/tests/eval).

For each idea in tests/eval/ideas.json, run the prior-art scan and the novelty
check once against the free live sources, and save the results as
tests/eval/fixtures/<id>.json. The test set replays these files, so it runs the
same way every time, with no network.

Run again when the research code or the ideas change:

    python scripts/record_eval_fixtures.py            # every idea
    python scripts/record_eval_fixtures.py banana_trichy tea_madurai
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.research import novelty  # noqa: E402
from app.research.scan import scan  # noqa: E402

EVAL = BACKEND / "tests" / "eval"


async def record(idea: dict) -> dict:
    s = await scan(idea["idea"])
    n = await novelty.check(idea["idea"], scan=s)
    return {
        "id": idea["id"],
        "idea": idea["idea"],
        "recorded": datetime.now(UTC).date().isoformat(),
        "coverage": [{"source": c["source"], "status": c["status"]} for c in s["coverage"]],
        "scan": s,
        "novelty": n,
    }


async def main(only: list[str]) -> None:
    ideas = json.loads((EVAL / "ideas.json").read_text(encoding="utf8"))["ideas"]
    out_dir = EVAL / "fixtures"
    out_dir.mkdir(exist_ok=True)
    for idea in ideas:
        if only and idea["id"] not in only:
            continue
        doc = await record(idea)
        (out_dir / f"{idea['id']}.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=1, default=str) + "\n",
            encoding="utf8",
        )
        missing = [c["source"] for c in doc["coverage"] if c["status"] not in ("ok", "skipped")]
        note = f" (not searched: {', '.join(missing)})" if missing else ""
        print(f"recorded {idea['id']}{note}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
