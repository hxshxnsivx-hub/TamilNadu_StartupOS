"""Seats backed by the model: one call for the whole panel (R175).

Every seat judged the same evidence pack, so seven separate calls bought no real
diversity and spent seven requests of a small free-tier quota on every panel run.
One call now returns every seat's opinion as a JSON array; each opinion is still
validated on its own, and a seat the reply leaves out or gets wrong falls back to
its rules. A failed call is recorded on the provider's breaker, so a quota that is
gone stops costing the full wait on every panel.

The system prompt is instructions first, then the evidence pack marked for prompt
caching; the seats' briefs, the idea and the levers to score go in the user message.
"""

from __future__ import annotations

import json
import re

import httpx

from app.agents import providers
from app.agents.council.evidence import LEVER, EvidencePack
from app.agents.council.seats import CRITERIA, Seat
from app.agents.providers import Provider

INSTRUCTIONS = (
    """You are Vanigam's review panel for a Tamil Nadu founder's idea. You speak for each
seat listed in the user message, separately, from that seat's point of view.
Judge only from the evidence listed below; every claim must cite evidence IDs from the list.
A claim without a valid ID is discarded. Never say the idea is new or unique.
Scores run 1 (poor) to 5 (strong) on these criteria: """
    + ", ".join(CRITERIA)
    + """.
Each seat scores only the criteria it can judge, and names the criterion each claim is about.
Each seat may also score the ways to stand out (evidence IDs starting """
    + LEVER
    + """) that its question
can judge, 1 (weak) to 5 (best), by the part of the ID after that prefix.

Reply with one JSON object and nothing else:
{"opinions": [
 {"seat": "<seat id>",
  "stance": "support" | "conditional" | "oppose",
  "scores": {"<criterion>": 1-5},
  "confidence": 0.0-1.0,
  "claims": [{"text": "...", "evidence": ["<id>", ...], "criterion": "<criterion>"}],
  "blocker": null | {"text": "...", "evidence": ["<id>"]},
  "ask_founder": "one question for the founder" | null,
  "variant": "one concrete change to the idea" | null,
  "levers": {"<lever id>": 1-5}}
]}
At most 3 claims per seat; a blocker only for a reason it cannot work.
"""
)
# Seven opinions in one reply need room; still far below seven separate calls.
MAX_TOKENS = 2400


def _system(pack: EvidencePack) -> list[dict]:
    return [
        {"type": "text", "text": INSTRUCTIONS},
        {
            "type": "text",
            "text": "Evidence (id | fact):\n" + pack.lines(),
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _user(seats: list[Seat], idea: str, slots: dict) -> str:
    known = ", ".join(f"{k}={v}" for k, v in sorted(slots.items())) or "nothing yet"
    rows = "\n".join(
        f"- {s.id} ({s.name}): {s.brief} Question: {s.question}"
        f" Focus on evidence of these kinds: {', '.join(sorted(s.kinds))}."
        for s in seats
    )
    return f"The seats:\n{rows}\n\nThe idea: {idea}\nKnown: {known}"


def _json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


async def ask_panel(
    client: httpx.AsyncClient,
    seats: list[Seat],
    pack: EvidencePack,
    idea: str,
    slots: dict,
    provider: Provider | None = None,
) -> tuple[dict[str, dict], dict]:
    """(seat id -> raw opinion, token usage) from one call to the first provider fit to
    judge. A failure is recorded on that provider's breaker and raised."""
    provider = provider or providers.judge()
    if provider is None:
        raise providers.ModelError("no model available for the review panel")
    # Claude caches the shared evidence block; other models take the same text plainly.
    system: list[dict] | str = _system(pack)
    if provider.name != "anthropic":
        system = "\n\n".join(b["text"] for b in system)
    try:
        text, usage = await provider.complete(client, system, _user(seats, idea, slots), MAX_TOKENS)
    except (providers.ModelError, httpx.HTTPError) as e:
        provider.breaker.fail(f"review panel: {e}")
        raise
    provider.breaker.succeed()
    wanted = {s.id for s in seats}
    rows = (_json(text) or {}).get("opinions")
    out: dict[str, dict] = {}
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and row.get("seat") in wanted and row["seat"] not in out:
            out[row["seat"]] = row
    return out, usage
