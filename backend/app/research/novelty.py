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
from app.research import sources
from app.research.terms import element_query, or_query, public_vocabulary, term_groups

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


def _label(n: int | None) -> str:
    if n is None:
        return "not searched"
    if n >= CROWDED:
        return "crowded"
    if n >= ACTIVE:
        return "active"
    return "sparse" if n > 0 else "nothing found"


def _parts(idea: str, elements: list[str] | None) -> list[dict]:
    if elements:
        rows = [{"element": e, "query": element_query(e)} for e in elements[:MAX_ELEMENTS]]
    else:
        rows = [
            {"element": phrase, "query": or_query(terms)}
            for phrase, terms in term_groups(idea)[:AUTO_ELEMENTS]
        ]
    return [r for r in rows if r["query"]]


async def check(
    idea: str,
    *,
    elements: list[str] | None = None,
    scan: dict | None = None,
    beneficiary: str | None = None,
    client: httpx.AsyncClient | None = None,
    private: bool = False,
) -> dict:
    """The novelty map, one statement, and the levers the gaps support."""
    parts = _parts(idea, elements)
    if private:
        return _unclear(parts, "Private mode: nothing was searched outside Vanigam.", "private")
    if not parts:
        return _unclear(parts, "I couldn't split the idea into searchable parts.", "skipped")

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
        if "ok" not in statuses:
            return _unclear(parts, "I couldn't search papers this time.", counts[0].status)

        searched = [p for p in parts if p["papers"] is not None]
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

    statement = _statement(searched, pair_rows, context)
    return {
        "elements": [{k: p.get(k) for k in ("element", "query", "papers", "label")} for p in parts],
        "pairs": sorted(pair_rows, key=lambda r: (not r["gap"], r["papers"])),
        "context": context,
        "statement": statement,
        "levers": _levers(searched, pair_rows, context, retarget, scan, statement),
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
    tn = len((scan or {}).get("local", {}).get("startups", []))
    if world.status != "ok" or india.status != "ok":
        return {"query": query, "searched": False, "tn_startups": tn, "gap": False}
    share = india.total / world.total if world.total else None
    return {
        "query": query,
        "searched": True,
        "world_papers": world.total,
        "india_papers": india.total,
        "india_share_pct": round(100 * share, 1) if share is not None else None,
        "tn_startups": tn,
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


def _statement(parts: list[dict], pairs: list[dict], context: dict) -> dict:
    gaps = [p for p in pairs if p["gap"]]
    if gaps:
        g = min(gaps, key=lambda p: p["papers"])
        return {
            "type": "combination",
            "text": (
                f"Both parts are well studied on their own: {g['a']} ({g['a_papers']:,}"
                f" papers) and {g['b']} ({g['b_papers']:,}). Together, I found only"
                f" {g['papers']:,}."
            ),
        }
    if context.get("gap"):
        return {
            "type": "context",
            "text": (
                f"Work on this is active worldwide ({context['world_papers']:,} papers), but"
                f" only {context['india_papers']:,} come from Indian institutions, and I found no"
                " Tamil Nadu startup doing it."
            ),
        }
    sparse = [p for p in parts if p["label"] in ("sparse", "nothing found")]
    if sparse and len(sparse) < len(parts):
        s = min(sparse, key=lambda p: p["papers"])
        return {
            "type": "element",
            "text": f"The rarest part is {s['element']}: only {s['papers']:,} papers.",
        }
    if sparse:
        return {
            "type": "element",
            "text": "Every part is thinly studied, so the evidence is weak either way.",
        }
    return {
        "type": "crowded",
        "text": (
            "Each part is well studied, and so are their combinations. The edge has to come"
            " from who you serve, the cost, or how you deliver it."
        ),
    }


def _levers(parts, pairs, context, retarget, scan, statement) -> list[dict]:
    """Ways to stand out. Each is offered only with the gap that justifies it."""
    out: list[dict] = []
    for g in [p for p in pairs if p["gap"]][:2]:
        out.append(
            {
                "kind": "combine",
                "text": f"Build your version around joining {g['a']} with {g['b']}.",
                "because": f"only {g['papers']:,} papers cover both",
            }
        )
    if context.get("gap"):
        out.append(
            {
                "kind": "localise",
                "text": (
                    "Make it fit Tamil Nadu, with the Tamil language, local hospital or market"
                    " routines, and a local price."
                ),
                "because": (
                    f"{context['india_papers']:,} of {context['world_papers']:,} papers are from"
                    " India, and no Tamil Nadu startup was found"
                ),
            }
        )
    if retarget and retarget["papers"] < PAIR_RARE_COUNT:
        out.append(
            {
                "kind": "re-target",
                "text": f"Design it specifically for {retarget['who']}.",
                "because": f"only {retarget['papers']:,} papers focus on them",
            }
        )
    fields = {f["name"] for f in (scan or {}).get("associated_domains", {}).get("fields", [])}
    if "Medicine" in fields:
        trials = (scan or {}).get("trials", {}).get("total", 0)
        out.append(
            {
                "kind": "regulatory route",
                "text": (
                    "Check whether a first version can avoid medical-device claims, for example"
                    " as a communication aid, and add clinical claims after a validation study."
                ),
                "because": f"the idea sits in medicine, with {trials} clinical trials found",
            }
        )
    if _has_pack(scan):
        out.append(
            {
                "kind": "cost-down",
                "text": "Compete on cost: the costing for this domain shows where to cut.",
                "because": "a Vanigam cost pack exists for this domain",
            }
        )
    if statement["type"] == "crowded":
        out.append(
            {
                "kind": "business model",
                "text": (
                    "Compete on how it is delivered: as a service, a rental, or a"
                    " scheme-backed rollout rather than a product sale."
                ),
                "because": "every part and combination is crowded",
            }
        )
    return out


def _has_pack(scan: dict | None) -> bool:
    from app.planner import registry

    doms = registry.load()["domains"]
    return any(
        doms.get(d["id"], {}).get("pack")
        for d in (scan or {}).get("local", {}).get("registry_domains", [])
    )


def _unclear(parts: list[dict], why: str, status: str) -> dict:
    return {
        "elements": [
            {"element": p["element"], "query": p["query"], "papers": None, "label": "not searched"}
            for p in parts
        ],
        "pairs": [],
        "context": {"searched": False},
        "statement": {"type": "unclear", "text": f"{why} I can't judge novelty yet."},
        "levers": [],
        "status": status,
        "caveat": CAVEAT,
    }
