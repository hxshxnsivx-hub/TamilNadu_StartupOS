"""Seats backed by the model: one short call each, in parallel, on a shared prefix.

The system prompt is the same for every seat and every turn of the council:
instructions first, then the evidence pack marked for prompt caching. Only the
seat's own brief goes in the user message, so seven calls share one cached
prefix (SYSTEM-DESIGN.md §3.3).
"""

from __future__ import annotations

import json
import re

import httpx

from app.agents import providers
from app.agents.council.evidence import EvidencePack
from app.agents.council.seats import CRITERIA, Seat
from app.agents.providers import Provider

INSTRUCTIONS = (
    """You are one seat on Vanigam's review panel for a Tamil Nadu founder's idea.
Judge only from the evidence listed below; every claim must cite evidence IDs from the list.
A claim without a valid ID is discarded. Never say the idea is new or unique.
Scores run 1 (poor) to 5 (strong) on these criteria: """
    + ", ".join(CRITERIA)
    + """.
Score only the criteria your seat can judge.

Reply with one JSON object and nothing else:
{"stance": "support" | "conditional" | "oppose",
 "scores": {"<criterion>": 1-5},
 "confidence": 0.0-1.0,
 "claims": [{"text": "...", "evidence": ["<id>", ...]}],   (at most 3)
 "blocker": null | {"text": "...", "evidence": ["<id>"]},   (only for a reason it cannot work)
 "ask_founder": "one question for the founder" | null,
 "variant": "one concrete change to the idea" | null}
"""
)


def _system(pack: EvidencePack) -> list[dict]:
    return [
        {"type": "text", "text": INSTRUCTIONS},
        {
            "type": "text",
            "text": "Evidence (id | fact):\n" + pack.lines(),
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _user(seat: Seat, idea: str, slots: dict) -> str:
    known = ", ".join(f"{k}={v}" for k, v in sorted(slots.items())) or "nothing yet"
    focus = ", ".join(sorted(seat.kinds))
    return (
        f"Your seat: {seat.name}. {seat.brief}\nYour question: {seat.question}\n"
        f"Focus on evidence of these kinds: {focus}.\n\nThe idea: {idea}\nKnown: {known}"
    )


def _json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


async def ask_seat(
    client: httpx.AsyncClient,
    seat: Seat,
    pack: EvidencePack,
    idea: str,
    slots: dict,
    provider: Provider | None = None,
) -> tuple[dict | None, dict]:
    """(the raw opinion or None, token usage), from the first provider fit to judge."""
    provider = provider or providers.judge()
    if provider is None:
        raise providers.ModelError("no model available for the review panel")
    # Claude caches the shared evidence block; other models take the same text plainly.
    system: list[dict] | str = _system(pack)
    if provider.name != "anthropic":
        system = "\n\n".join(b["text"] for b in system)
    text, usage = await provider.complete(client, system, _user(seat, idea, slots), 700)
    return _json(text), usage
