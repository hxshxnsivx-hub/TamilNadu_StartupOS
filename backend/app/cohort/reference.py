"""Reference cohort: where an idea sits among Tamil Nadu startups and companies.

    idea text (+ sector, district)
      -> similar startups on the TN Startup Map, by words shared with their
         descriptions (rare words count more) and sector
      -> registered companies in the same sector, by district, age and size
         (MCA master data)
      -> plain observations: how many, where, how established, and where
         there is no one doing it yet

Coverage is partial: the map lists the startups that registered on it, and most
records carry no stage or founding year. The response says so.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from functools import lru_cache

from app.ecosystem.index import get_ecosystem
from app.planner.registry import _terms

MIN_SHARED = 2
SECTOR_BONUS = 1.5
DISTRICTS = ("chennai", "coimbatore", "madurai")  # the districts the data covers today


@lru_cache
def _startup_index() -> tuple[list[dict], list[set[str]], dict[str, float]]:
    eco = get_ecosystem()
    startups = list(eco.startups) if eco else []
    terms = [_terms(f"{s.get('name', '')} {s.get('description') or ''}") for s in startups]
    df = Counter(w for t in terms for w in t)
    n = max(1, len(startups))
    return startups, terms, {w: math.log(n / c) for w, c in df.items()}


def _snippet(text: str | None, n: int = 160) -> str:
    t = (text or "").replace("**", "").strip()
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def similar_startups(text: str, sector: str | None = None, limit: int = 8) -> list[dict]:
    startups, terms, idf = _startup_index()
    words = _terms(text)
    # show the founder's own words, not the stems used for matching
    spoken = {next(iter(_terms(w)), ""): w.lower() for w in text.replace("-", " ").split()}
    scored = []
    for s, t in zip(startups, terms, strict=True):
        shared = words & t
        in_sector = bool(sector and sector in (s.get("sectors") or []))
        if len(shared) < MIN_SHARED and not (in_sector and shared):
            continue
        score = sum(idf.get(w, 0) for w in shared) + (SECTOR_BONUS if in_sector else 0)
        scored.append((score, s, sorted(spoken.get(w, w) for w in shared)))
    scored.sort(key=lambda r: (-r[0], r[1]["name"]))
    return [
        {
            "name": s["name"],
            "district": s.get("district"),
            "sectors": s.get("sectors") or [],
            "tier": s.get("tier"),
            "status": s.get("status"),
            "stage": s.get("stage"),
            "about": _snippet(s.get("description")),
            "shared_words": shared,
            "url": s.get("website") or s.get("source_url"),
            "source": s.get("source_url"),
        }
        for _, s, shared in scored[:limit]
    ]


def sector_companies(sector: str) -> dict:
    eco = get_ecosystem()
    rows = [c for c in (eco.companies if eco else []) if c.get("sector") == sector]
    years = [c["year"] for c in rows if isinstance(c.get("year"), int) and c["year"] > 1900]
    sizes = Counter(
        "large" if (c.get("paidup_lakh") or 0) >= 1000
        else "medium" if (c.get("paidup_lakh") or 0) >= 100
        else "small"
        for c in rows
    )  # fmt: skip
    return {
        "sector": sector,
        "total": len(rows),
        "by_district": dict(Counter(c.get("district") for c in rows).most_common()),
        "median_year": int(statistics.median(years)) if years else None,
        "registered_since_2015": sum(1 for y in years if y >= 2015),
        "by_size": dict(sizes),
        "source": "MCA company master data, Tamil Nadu (data.gov.in, 2020)",
    }


def reference_cohort(
    text: str, sector: str | None = None, district: str | None = None, limit: int = 8
) -> dict:
    similar = similar_startups(text, sector, limit=max(limit, 25))
    shown = similar[:limit]
    by_district = Counter(s["district"] for s in similar)
    by_tier = Counter(s["tier"] for s in similar if s["tier"])
    stages = Counter(s["stage"] for s in similar if s["stage"])
    companies = sector_companies(sector) if sector else None

    obs: list[str] = []
    if similar:
        where = ", ".join(f"{d.title()} {n}" for d, n in by_district.most_common())
        obs.append(f"{len(similar)} similar startups on the Tamil Nadu Startup Map ({where}).")
        if district and district in DISTRICTS and not by_district.get(district):
            obs.append(f"None of them is in {district.title()}: room to be the local option.")
        established = by_tier.get("Tier 1", 0) + by_tier.get("Tier 2", 0)
        if established:
            verb = "is" if established == 1 else "are"
            obs.append(f"{established} of them {verb} established (Tier 1 or 2 on the map).")
        if stages:
            known = ", ".join(f"{k} {v}" for k, v in stages.most_common())
            obs.append(f"Funding stage is known for {sum(stages.values())}: {known}.")
    else:
        obs.append("No similar startup found on the Tamil Nadu Startup Map.")
    if companies and companies["total"]:
        obs.append(
            f"{companies['total']:,} registered companies in {sector}"
            + (
                f", typically registered around {companies['median_year']}"
                if companies["median_year"]
                else ""
            )
            + "."
        )
    return {
        "idea": text,
        "sector": sector,
        "district": district,
        "similar_startups": shown,
        "summary": {
            "similar_total": len(similar),
            "by_district": dict(by_district),
            "by_tier": dict(by_tier),
            "stages_known": dict(stages),
        },
        "sector_companies": companies,
        "observations": obs,
        "coverage": (
            "The map lists startups that registered on it (654, in Chennai, Coimbatore and"
            " Madurai); most records have no stage or founding year. Company data is the MCA"
            " master list from 2020. Absence here is not proof that no one does this."
        ),
    }
