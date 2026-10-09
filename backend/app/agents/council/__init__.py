"""The advocate council (architecture dashboard properties 7–9, build spec §7–9).

    evidence pack (one ID per fact) → seven seats in parallel (model or rules)
    → opinions validated (uncited claims dropped) → weighted vote (code)
    → synthesis (what the founder hears) + one question
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

import httpx

from app.agents.council import evidence as evidence_mod
from app.agents.council.model import ask_seat
from app.agents.council.rules import RULES
from app.agents.council.seats import SEATS, Opinion, validate
from app.agents.council.synthesis import synthesise
from app.agents.council.vote import idea_type, vote
from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("council")
SEAT_TIMEOUT_S = 8.0


async def convene(
    idea: str,
    slots: dict,
    *,
    scan: dict | None,
    novelty: dict | None,
    seats: tuple[str, ...] | None = None,
    previous: list[dict] | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """Run the council. `seats` limits the run to those seats; `previous`
    opinions fill in the others (a partial re-run after a small change)."""
    started = time.monotonic()
    district = slots.get("district")
    pack = evidence_mod.build(idea, scan, novelty, str(district) if district else None)
    use_model = bool(get_settings().anthropic_api_key)
    wanted = [s for s in SEATS if seats is None or s.id in seats]
    opinions: dict[str, Opinion] = {}
    usage: dict[str, int] = {}
    fallback: list[str] = []

    if use_model:
        own = client is None
        client = client or httpx.AsyncClient(timeout=SEAT_TIMEOUT_S + 2)
        try:
            tasks = {
                s.id: asyncio.create_task(ask_seat(client, s, pack, idea, slots)) for s in wanted
            }
            done, pending = await asyncio.wait(tasks.values(), timeout=SEAT_TIMEOUT_S)
            for t in pending:
                t.cancel()
            for s in wanted:
                t = tasks[s.id]
                if t in done and not t.exception():
                    raw, use = t.result()
                    for k, v in use.items():
                        if isinstance(v, int):
                            usage[k] = usage.get(k, 0) + v
                    op = validate(raw or {}, s, pack.ids, "model") if raw else None
                    if op:
                        opinions[s.id] = op
                        continue
                fallback.append(s.id)
        finally:
            if own:
                await client.aclose()
    else:
        fallback = [s.id for s in wanted]

    for s in wanted:  # rules stand in for any seat the model could not answer
        if s.id in fallback:
            op = validate(RULES[s.id](pack, slots), s, pack.ids, "rules")
            if op:
                opinions[s.id] = op

    for row in previous or []:  # seats not re-run keep their last opinion
        if row["seat"] not in opinions and (seats is not None and row["seat"] not in seats):
            opinions[row["seat"]] = Opinion.model_validate(row)

    ops = list(opinions.values())
    kind = idea_type((scan or {}).get("vanigam_categories", []), slots)
    result = vote(ops, kind, slots)
    brief = synthesise(result, ops, pack)
    took = round(time.monotonic() - started, 2)
    log.info("council.done", seats=len(ops), fallback=fallback, band=result["band"], seconds=took)
    return {
        "at": datetime.now(UTC).isoformat(),
        "seconds": took,
        "basis": "model" if use_model and len(fallback) < len(wanted) else "rules",
        "fallback_seats": fallback,
        "evidence_ids": len(pack.ids),
        "evidence": pack.items,
        "domain_id": pack.domain_id,
        "opinions": [o.model_dump() for o in ops],
        "vote": result,
        "synthesis": brief,
        "usage": usage,
    }


__all__ = ["convene"]
