"""The advocate council (architecture dashboard properties 7–9, build spec §7–9).

    evidence pack (one ID per fact) → seven seats (one model call, or rules)
    → opinions validated (uncited claims dropped) → weighted vote (code)
    → synthesis (what the founder hears) + one question
    → the ways to stand out, ranked by the seats' scores (task 1.3.1)
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

import httpx

from app.agents import providers
from app.agents.council import evidence as evidence_mod
from app.agents.council.model import ask_panel
from app.agents.council.rules import RULES
from app.agents.council.seats import SEATS, Opinion, validate
from app.agents.council.synthesis import synthesise
from app.agents.council.vote import idea_type, vote
from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("council")


def _timeout() -> float:
    """How long the one panel call may take. One call answers for every seat (R175),
    which is more to write than one seat's reply, but it must still land inside the
    wait of the turn that asked for a view (`opinion_wait_s`): a panel the founder
    asked for and that arrives later is heard a turn late."""
    return get_settings().opinion_wait_s


async def convene(
    idea: str,
    slots: dict,
    *,
    scan: dict | None,
    novelty: dict | None,
    seats: tuple[str, ...] | None = None,
    previous: list[dict] | None = None,
    client: httpx.AsyncClient | None = None,
    use_model: bool | None = None,
) -> dict:
    """Run the council. `seats` limits the run to those seats; `previous`
    opinions fill in the others (a partial re-run after a small change).
    `use_model=False` forces rules (spend cap reached, or the model is down)."""
    started = time.monotonic()
    district = slots.get("district")
    pack = evidence_mod.build(idea, scan, novelty, str(district) if district else None, slots)
    judge = providers.judge()
    if use_model is None:
        use_model = judge is not None
    use_model = use_model and judge is not None
    wanted = [s for s in SEATS if seats is None or s.id in seats]
    opinions: dict[str, Opinion] = {}
    usage: dict[str, int] = {}
    fallback: list[str] = []

    if use_model:
        own = client is None
        timeout = _timeout()
        client = client or httpx.AsyncClient(timeout=timeout + 2)
        raws: dict[str, dict] = {}
        try:
            raws, use = await asyncio.wait_for(
                ask_panel(client, wanted, pack, idea, slots, judge), timeout
            )
            usage = {k: v for k, v in use.items() if isinstance(v, int)}
        except TimeoutError:
            judge.breaker.fail("review panel: no reply in time")
            log.info("council.model_failed", error="timeout")
        except (providers.ModelError, httpx.HTTPError) as e:  # on the breaker already
            log.info("council.model_failed", error=str(e)[:200])
        finally:
            if own:
                await client.aclose()
        for s in wanted:
            op = validate(raws[s.id], s, pack.ids, "model") if s.id in raws else None
            if op:
                opinions[s.id] = op
            else:
                fallback.append(s.id)
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
    result = vote(ops, kind, slots, [lv["id"] for lv in pack.levers])
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
