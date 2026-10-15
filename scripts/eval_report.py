"""Write docs/eval/report.md: the quality test set, idea by idea, check by check.

    python scripts/eval_report.py

Runs the same offline conversations as backend/tests/eval/test_eval.py and
writes a readable report: a summary table, every failed check with its reason,
and each conversation in full.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from tests.eval.runner import load_fixture, load_ideas, run_idea  # noqa: E402

OUT = ROOT / "docs" / "eval" / "report.md"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


async def main() -> int:
    ideas = load_ideas()
    results = [await run_idea(i) for i in ideas]
    passed = sum(r.passed for r in results)
    checks = sum(len(r.checks) for r in results)
    ok_checks = sum(c.passed for r in results for c in r.checks)

    lines = [
        "# Quality test set report",
        "",
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')} UTC"
        " by `scripts/eval_report.py`.",
        "Offline conversations: no model, no Redis, research replayed from recordings.",
        "",
        f"**{passed} of {len(results)} ideas pass; {ok_checks} of {checks} checks hold.**",
        "",
        "| Idea | Result | Checks | Questions asked | Research recorded |",
        "|---|---|---|---|---|",
    ]
    for idea, r in zip(ideas, results, strict=True):
        fx = load_fixture(idea["id"])
        held = sum(c.passed for c in r.checks)
        lines.append(
            f"| `{r.id}` | {'pass' if r.passed else '**fail**'} | {held}/{len(r.checks)}"
            f" | {len([a for a in r.asked if a])} | {fx.get('recorded', '?')} |"
        )

    failed = [r for r in results if not r.passed]
    lines += ["", "## Failed checks", ""]
    if not failed:
        lines.append("None.")
    for r in failed:
        lines.append(f"### `{r.id}`")
        lines += [f"- **{c.name}**: {_cell(c.detail)}" for c in r.failures()]
        lines.append("")

    lines += ["", "## Conversations", ""]
    for idea, r in zip(ideas, results, strict=True):
        lines += [
            "<details>",
            f"<summary><code>{r.id}</code>: {'pass' if r.passed else 'fail'}</summary>",
            "",
            f"Idea: {idea['idea']}",
            "",
            "| Check | Holds | Detail |",
            "|---|---|---|",
        ]
        for c in r.checks:
            detail = "" if c.passed else _cell(c.detail)
            lines.append(f"| {_cell(c.name)} | {'yes' if c.passed else '**no**'} | {detail} |")
        lines.append("")
        for who, text in r.transcript:
            lines.append(f"**{'Founder' if who == 'founder' else 'Vanigam'}:** {text}")
            lines.append("")
        lines += ["</details>", ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf8")
    print(f"{passed}/{len(results)} ideas pass; report written to {OUT.relative_to(ROOT)}")
    print(json.dumps({r.id: r.passed for r in results}))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
