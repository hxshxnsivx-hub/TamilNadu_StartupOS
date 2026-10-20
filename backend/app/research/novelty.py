"""Novelty check and ways to add novelty (IDEATION-PIPELINE-DESIGN.md §2).

Vanigam never calls an idea new. It reports what was and was not found, at
three levels, and turns the gaps into concrete ways to stand out:

    element      does each part of the idea exist on its own?
    combination  do the parts exist together? (known parts, rare together)
    context      does it exist in India and in Tamil Nadu?

Counts come from OpenAlex (one cheap count request each, cached seven days).
Spaces mean AND, so a pair is searched as both parts' queries side by side.

The thresholds are heuristics on counts and are stated as such: they say
where to look, not what is true.
"""

from __future__ import annotations

import asyncio
from itertools import combinations

import httpx

from app.core.config import get_settings
from app.research import levers, sources
from app.research.scan import domain_id
from app.research.terms import (
    BENEFICIARY,
    element_query,
    is_health_product,
    or_query,
    public_vocabulary,
    term_groups,
)

MAX_ELEMENTS = 6  # 15 pairs at most
AUTO_ELEMENTS = 4  # parts found by the lexicon alone: 6 pairs at most
ACTIVE = 300  # papers: a part is well studied at or above this
CROWDED = 5000
PAIR_RARE_SHARE = 0.02  # a pair is rare below 2% of the smaller part...
PAIR_RARE_COUNT = 30  # ...or below 30 papers
INDIA_LOW_SHARE = 0.05
CAVEAT = (
    "Not found in these sources is not proof of novelty; have a patent attorney search"
    " before filing."
)


NOT_SEARCHED_WELL = "not searched well"
NO_PARTS = (
    "I couldn't split the idea into parts to search: none of its words are in the"
    " vocabulary I may send to the sources yet."
)


def _label(n: int | None) -> str:
    if n is None:
        return "not searched"
    if n >= CROWDED:
        return "crowded"
    if n >= ACTIVE:
        return "active"
    return "sparse" if n > 0 else "nothing found"


def _parts(idea: str, elements: list[str] | None) -> list[dict]:
    """The parts to count. Found by the lexicon, they leave out who is served (the
    re-target lever covers that) and any part that only restates another more broadly:
    "solar" beside "solar inverters", "coconut" beside "virgin coconut oil" (1.2.1.4)."""
    if elements:
        rows = [{"element": e, "query": element_query(e)} for e in elements[:MAX_ELEMENTS]]
    else:
        groups = [(p, t) for p, t in term_groups(idea) if p not in BENEFICIARY]
        groups = [(p, t) for p, t in groups if not _broader(t, groups)]
        rows = [{"element": p, "query": or_query(t)} for p, t in groups[:AUTO_ELEMENTS]]
    return [r for r in rows if r["query"]]


def _broader(terms: list[str], groups: list[tuple[str, list[str]]]) -> bool:
    """Every term of this part sits inside a longer term of another part."""
    others = [o.lower() for _, ts in groups if ts != terms for o in ts]
    return all(any(t.lower() in o and t.lower() != o for o in others) for t in terms)


def _one_term(query: str) -> bool:
    """A single name: one word or one quoted phrase, not an OR group or several words."""
    q = query.strip()
    if q.startswith('"') and q.endswith('"'):
        return q.count('"') == 2
    return " " not in q and not q.startswith("(")


async def check(
    idea: str,
    *,
    elements: list[str] | None = None,
    scan: dict | None = None,
    beneficiary: str | None = None,
    slots: dict | None = None,
    client: httpx.AsyncClient | None = None,
    private: bool = False,
) -> dict:
    """The novelty map, one statement, and the levers the gaps support. `slots`: what
    the founder has said so far, for the health-product rule (R139)."""
    parts = _parts(idea, elements)
    if private:
        return _unclear(parts, "Private mode: nothing was searched outside Vanigam.", "private")
    if not parts:  # the lexicon knows none of its words: say so, not "nothing found" (1.2.1.6)
        return _unclear(parts, NO_PARTS, "skipped")

    settings = get_settings()
    cache = sources.Cache(settings.research_cache_dir, settings.research_cache_days)
    own = client is None
    client = client or httpx.AsyncClient(timeout=60, headers={"User-Agent": sources.UA})
    try:
        counts = await asyncio.gather(
            *(sources.paper_count(client, p["query"], cache) for p in parts)
        )
        statuses = {c.status for c in counts}
        for p, c in zip(parts, counts, strict=True):
            p["papers"] = c.total if c.status == "ok" else None
            p["label"] = _label(p["papers"])
            # One name with no paper at all is a name the literature does not use, not a
            # gap: "dry-run" searched as "pump dry running protection" finds nothing.
            if p["papers"] == 0 and _one_term(p["query"]):
                p["label"] = NOT_SEARCHED_WELL
        if "ok" not in statuses:
            return _unclear(parts, "I couldn't search papers this time.", counts[0].status)

        searched = [p for p in parts if p["papers"] is not None and p["label"] != NOT_SEARCHED_WELL]
        if not searched:
            return _unclear(
                parts,
                "None of the idea's parts found a paper under the names I searched, so the"
                " names are probably not the ones research uses.",
                "not_searched_well",
                keep_counts=True,
            )
        pairs = [{"a": a, "b": b} for a, b in combinations(searched, 2)]
        pair_counts = await asyncio.gather(
            *(
                sources.paper_count(client, f"{x['a']['query']} {x['b']['query']}", cache)
                for x in pairs
            )
        )
        pair_rows = []
        for x, c in zip(pairs, pair_counts, strict=True):
            if c.status != "ok":
                continue
            a, b = x["a"], x["b"]
            smaller = min(a["papers"], b["papers"])
            share = c.total / smaller if smaller else None
            # Rare means a low count, not just a small share: 1,118 papers is not rare
            # even when it is 1.5% of a field of 74,000.
            gap = (
                a["papers"] >= ACTIVE
                and b["papers"] >= ACTIVE
                and c.total < ACTIVE
                and (c.total < PAIR_RARE_COUNT or (share is not None and share < PAIR_RARE_SHARE))
            )
            pair_rows.append(
                {
                    "a": a["element"],
                    "b": b["element"],
                    "a_papers": a["papers"],
                    "b_papers": b["papers"],
                    "papers": c.total,
                    "share_pct": round(100 * share, 2) if share is not None else None,
                    "gap": gap,
                }
            )

        context = await _context(client, cache, searched, scan)
        retarget = await _retarget(client, cache, searched, beneficiary)
    finally:
        if own:
            await client.aclose()

    expected = len(searched) * (len(searched) - 1) // 2
    statement = _statement(searched, pair_rows, context, expected)
    return {
        "elements": [{k: p.get(k) for k in ("element", "query", "papers", "label")} for p in parts],
        "pairs": sorted(pair_rows, key=lambda r: (not r["gap"], r["papers"])),
        "context": context,
        "coverage": {"pairs_expected": expected, "pairs_counted": len(pair_rows)},
        "statement": statement,
        "levers": _levers(
            searched,
            pair_rows,
            context,
            retarget,
            scan,
            statement,
            is_health_product(idea, scan, slots),
            domain_id(idea, scan),
        ),
        "thresholds": {
            "active_papers": ACTIVE,
            "crowded_papers": CROWDED,
            "rare_pair_share_pct": PAIR_RARE_SHARE * 100,
            "rare_pair_papers": PAIR_RARE_COUNT,
            "india_low_share_pct": INDIA_LOW_SHARE * 100,
        },
        "caveat": CAVEAT,
    }


def _core_query(parts: list[dict]) -> str:
    """The idea as one search: its two best-studied parts together."""
    top = sorted(parts, key=lambda p: -(p["papers"] or 0))[:2]
    return " ".join(p["query"] for p in top)


async def _context(client, cache, parts: list[dict], scan: dict | None) -> dict:
    query = _core_query(parts)
    world, india = await asyncio.gather(
        sources.paper_count(client, query, cache),
        sources.paper_count(
            client, query, cache, filter="authorships.institutions.country_code:IN"
        ),
    )
    # Tamil Nadu startups count only when the local lookup ran, and only for what it
    # covered: a failed lookup is not "no startup does this" (R023).
    local = (scan or {}).get("local", {})
    searched_tn = local.get("status") == "ok" and bool(local.get("scope"))
    tn = len(local.get("startups", [])) if searched_tn else None
    scope = local.get("scope") if searched_tn else None
    if world.status != "ok" or india.status != "ok":
        return {
            "query": query,
            "searched": False,
            "tn_startups": tn,
            "tn_scope": scope,
            "gap": False,
        }
    share = india.total / world.total if world.total else None
    return {
        "query": query,
        "searched": True,
        "world_papers": world.total,
        "india_papers": india.total,
        "india_share_pct": round(100 * share, 1) if share is not None else None,
        "tn_startups": tn,
        "tn_scope": scope,
        # India-affiliated papers: affiliation data is incomplete, so this is a hint
        "gap": world.total >= ACTIVE and share is not None and share < INDIA_LOW_SHARE and tn == 0,
    }


async def _retarget(client, cache, parts: list[dict], beneficiary: str | None) -> dict | None:
    """Is the founder's user group rare in the work on this idea?"""
    if not beneficiary:
        return None
    words = [w for w in beneficiary.lower().split() if w in public_vocabulary()][:2]
    if not words:
        return None
    core = _core_query(parts)
    with_users = await sources.paper_count(client, f"{core} {' '.join(words)}", cache)
    if with_users.status != "ok":
        return None
    return {"who": " ".join(words), "papers": with_users.total}


def _statement(parts: list[dict], pairs: list[dict], context: dict, expected: int) -> dict:
    """One statement from the counts. "Crowded" and "active" need every combination and
    the context counted; anything less is "unclear", since not searched is never
    nothing found (R030)."""
    gaps = [p for p in pairs if p["gap"]]
    if gaps:
        g = min(gaps, key=lambda p: p["papers"])
        return {
            "type": "combination",
            "text": (
                f"Both parts are well studied on their own: {g['a']} ({g['a_papers']:,}"
                f" papers) and {g['b']} ({g['b_papers']:,}). Together, I found"
                f" {_few(g['papers'], 'paper', 'papers', none='none')}."
            ),
        }
    if context.get("gap"):
        return {
            "type": "context",
            "text": (
                f"Work on this is active worldwide ({context['world_papers']:,} papers), but"
                f" {_few(context['india_papers'], 'comes', 'come', none='none')} from Indian"
                f" institutions, and none of {context['tn_scope']} does it."
            ),
        }
    sparse = [p for p in parts if p["label"] in ("sparse", "nothing found")]
    if sparse and len(sparse) < len(parts):
        s = min(sparse, key=lambda p: p["papers"])
        return {
            "type": "element",
            "text": f"The rarest part is {s['element']}: {_few(s['papers'], 'paper', 'papers')}.",
        }
    if sparse:
        return {
            "type": "element",
            "text": "Every part is thinly studied, so the evidence is weak either way.",
        }
    if len(parts) < 2:
        p = parts[0]
        return {
            "type": "unclear",
            "text": (
                f"I could search only one part on its own, {p['element']}"
                f" ({_count(p['papers'], 'paper')}), so I can't say how new the idea is as a"
                " whole."
            ),
        }
    if len(pairs) < expected or not context.get("searched"):
        return {
            "type": "unclear",
            "text": (
                "Each part is well studied, but I could not count every combination this"
                " time, so I can't say whether the idea as a whole is crowded."
            ),
        }
    if all(p["label"] == "crowded" for p in parts):
        return {
            "type": "crowded",
            "text": (
                "Each part is well studied, and so are their combinations. The edge has to"
                " come from who you serve, the cost, or how you deliver it."
            ),
        }
    return {
        "type": "active",
        "text": (
            "Each part is actively studied, and the combinations I counted are studied too."
            " The edge is likely to come from who you serve, the cost, or how you deliver it."
        ),
    }


def _count(n: int, noun: str) -> str:
    return f"{n:,} {noun}" + ("" if n == 1 else "s")


def _few(n: int, one: str, many: str, none: str = "") -> str:
    """'only 3 papers', 'only 1 paper', and 'no papers' rather than 'only 0 papers'."""
    if n == 0:
        return none or f"no {many}"
    return f"only 1 {one}" if n == 1 else f"only {n:,} {many}"


def _has_pack(domain_id: str | None) -> bool:
    from app.planner import registry

    return bool(domain_id and registry.load()["domains"].get(domain_id, {}).get("pack"))


def _levers(parts, pairs, context, retarget, scan, statement, health, domain_id) -> list[dict]:
    """Ways to stand out. Each is offered only with the gap that justifies it, and kept
    as its kind and facts; levers.render words it for the domain and sector (R190)."""
    out: list[dict] = []
    for g in [p for p in pairs if p["gap"]][:2]:
        out.append({"kind": "combine", "facts": {"a": g["a"], "b": g["b"], "papers": g["papers"]}})
    if context.get("gap"):
        out.append(
            {
                "kind": "localise",
                "facts": {
                    "india_papers": context["india_papers"],
                    "world_papers": context["world_papers"],
                    "tn_scope": context["tn_scope"],
                },
            }
        )
    if retarget and retarget["papers"] < PAIR_RARE_COUNT:
        out.append({"kind": "re-target", "facts": dict(retarget)})
    if health:
        trials = (scan or {}).get("trials", {}).get("total") or 0
        out.append({"kind": "regulatory route", "facts": {"trials": trials}})
    if _has_pack(domain_id):
        out.append({"kind": "cost-down", "facts": {"domain": domain_id}})
    if statement["type"] == "crowded":
        out.append({"kind": "business model", "facts": {}})
    # Search-time words for readers without a session (the API, the panel's evidence);
    # the conversation rewords them from the founder's current sector when it says them.
    return [levers.render(lv, domain_id=domain_id) for lv in out]


def _unclear(parts: list[dict], why: str, status: str, keep_counts: bool = False) -> dict:
    return {
        "elements": [
            {
                "element": p["element"],
                "query": p["query"],
                "papers": p.get("papers") if keep_counts else None,
                "label": p.get("label") if keep_counts else "not searched",
            }
            for p in parts
        ],
        "pairs": [],
        "context": {"searched": False},
        "statement": {"type": "unclear", "text": f"{why} I can't judge novelty yet."},
        "levers": [],
        "status": status,
        "caveat": CAVEAT,
    }
