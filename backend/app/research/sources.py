"""Source connectors for prior-art research. Each returns a SourceResult.

  papers    OpenAlex works (free; a key lifts the small shared daily budget)
  trials    ClinicalTrials.gov v2 (free, no key) — health ideas
  projects  GitHub repository search (free; a token lifts the rate limit)
  patents   PatentsView PatentSearch API (free key required)

Every result says what happened — ok, no_key, budget_exhausted, error — so a
report never implies "nothing exists" when the truth is "not searched".
Responses are cached on disk for `research_cache_days`.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings

OPENALEX = "https://api.openalex.org/works"
CTGOV = "https://clinicaltrials.gov/api/v2/studies"
GITHUB = "https://api.github.com/search/repositories"
PATENTSVIEW = "https://search.patentsview.org/api/v1/patent/"
UA = "VanigamResearch/0.1 (prior-art scan)"


@dataclass
class SourceResult:
    source: str
    status: str  # ok | no_key | budget_exhausted | error | skipped | private
    total: int = 0
    items: list[dict] = field(default_factory=list)
    note: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class Cache:
    def __init__(self, root: str | Path, days: int) -> None:
        self.root = Path(root)
        self.ttl = days * 86400

    def _path(self, key: str) -> Path:
        return self.root / (hashlib.sha1(key.encode()).hexdigest() + ".json")

    def get(self, key: str) -> Any | None:
        p = self._path(key)
        if not p.exists() or time.time() - p.stat().st_mtime > self.ttl:
            return None
        return json.loads(p.read_text(encoding="utf8"))

    def put(self, key: str, value: Any) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(json.dumps(value), encoding="utf8")


async def _get_json(
    client: httpx.AsyncClient, cache: Cache | None, url: str, **kw
) -> tuple[int, Any]:
    key = f"GET {url} {json.dumps(kw.get('params', {}), sort_keys=True)}"
    if cache and (hit := cache.get(key)) is not None:
        return 200, hit
    r = await client.get(url, **kw)
    if r.status_code == 200:
        data = r.json()
        if cache:
            cache.put(key, data)
        return 200, data
    return r.status_code, r.text[:300]


def _work(w: dict) -> dict:
    src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
    return {
        "title": w.get("display_name"),
        "year": w.get("publication_year"),
        "cited_by": w.get("cited_by_count", 0),
        "venue": src,
        "url": w.get("doi") or w.get("id"),
        "topics": [
            {
                "topic": t.get("display_name"),
                "subfield": (t.get("subfield") or {}).get("display_name"),
                "field": (t.get("field") or {}).get("display_name"),
                "domain": (t.get("domain") or {}).get("display_name"),
                "score": t.get("score", 0),
            }
            for t in (w.get("topics") or [])
        ],
    }


async def papers(client: httpx.AsyncClient, query: str, cache: Cache | None = None) -> SourceResult:
    key = get_settings().openalex_api_key
    base = {"search": query, **({"api_key": key} if key else {})}
    select = "id,display_name,publication_year,cited_by_count,doi,primary_location,topics"
    status, rel = await _get_json(
        client, cache, OPENALEX, params={**base, "per_page": 25, "select": select}
    )
    if status == 429:
        return SourceResult(
            "papers",
            "budget_exhausted",
            note="OpenAlex daily budget used up for this network; add OPENALEX_API_KEY",
        )
    if status != 200:
        return SourceResult("papers", "error", note=f"OpenAlex returned {status}")
    _, cited = await _get_json(
        client,
        cache,
        OPENALEX,
        params={**base, "per_page": 5, "select": select, "sort": "cited_by_count:desc"},
    )
    _, years = await _get_json(
        client, cache, OPENALEX, params={**base, "group_by": "publication_year"}
    )
    by_year = {}
    if isinstance(years, dict):
        by_year = {
            int(g["key"]): g["count"] for g in years.get("group_by", []) if str(g["key"]).isdigit()
        }
    items = [_work(w) for w in rel.get("results", [])]
    most_cited = [_work(w) for w in (cited.get("results", []) if isinstance(cited, dict) else [])]
    return SourceResult(
        "papers",
        "ok",
        total=rel.get("meta", {}).get("count", len(items)),
        items=items,
        extra={"most_cited": most_cited, "by_year": by_year},
    )


async def trials(client: httpx.AsyncClient, query: str, cache: Cache | None = None) -> SourceResult:
    status, data = await _get_json(
        client, cache, CTGOV, params={"query.term": query, "pageSize": 10, "countTotal": "true"}
    )
    if status != 200:
        return SourceResult("trials", "error", note=f"ClinicalTrials.gov returned {status}")
    items = []
    for s in data.get("studies", []):
        p = s.get("protocolSection", {})
        ident, st = p.get("identificationModule", {}), p.get("statusModule", {})
        items.append(
            {
                "id": ident.get("nctId"),
                "title": ident.get("briefTitle"),
                "status": st.get("overallStatus"),
                "phases": (p.get("designModule") or {}).get("phases"),
                "sponsor": (p.get("sponsorCollaboratorsModule") or {})
                .get("leadSponsor", {})
                .get("name"),
                "start": (st.get("startDateStruct") or {}).get("date"),
                "url": f"https://clinicaltrials.gov/study/{ident.get('nctId')}",
            }
        )
    return SourceResult("trials", "ok", total=data.get("totalCount", len(items)), items=items)


async def projects(
    client: httpx.AsyncClient, query: str, cache: Cache | None = None
) -> SourceResult:
    token = get_settings().github_token
    headers = {"Accept": "application/vnd.github+json", "User-Agent": UA}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, data = await _get_json(
        client,
        cache,
        GITHUB,
        params={"q": query, "sort": "stars", "per_page": 10},
        headers=headers,
    )
    if status in (403, 429):
        return SourceResult(
            "projects", "budget_exhausted", note="GitHub rate limit; add GITHUB_TOKEN"
        )
    if status != 200:
        return SourceResult("projects", "error", note=f"GitHub returned {status}")
    items = [
        {
            "name": g.get("full_name"),
            "description": g.get("description"),
            "stars": g.get("stargazers_count", 0),
            "updated": g.get("pushed_at"),
            "license": (g.get("license") or {}).get("spdx_id"),
            "url": g.get("html_url"),
        }
        for g in data.get("items", [])
    ]
    return SourceResult("projects", "ok", total=data.get("total_count", len(items)), items=items)


async def patents(
    client: httpx.AsyncClient, query: str, cache: Cache | None = None
) -> SourceResult:
    key = get_settings().patentsview_api_key
    if not key:
        return SourceResult(
            "patents",
            "no_key",
            note="Patents not searched: add a free PatentsView key (PATENTSVIEW_API_KEY)",
        )
    body = {
        "q": {"_text_any": {"patent_abstract": query}},
        "f": ["patent_id", "patent_title", "patent_date", "assignees.assignee_organization"],
        "o": {"size": 10},
        "s": [{"patent_date": "desc"}],
    }
    r = await client.post(PATENTSVIEW, json=body, headers={"X-Api-Key": key, "User-Agent": UA})
    if r.status_code != 200:
        return SourceResult("patents", "error", note=f"PatentsView returned {r.status_code}")
    data = r.json()
    items = [
        {
            "id": p.get("patent_id"),
            "title": p.get("patent_title"),
            "date": p.get("patent_date"),
            "assignees": [a.get("assignee_organization") for a in p.get("assignees") or [] if a],
            "url": f"https://patents.google.com/patent/US{p.get('patent_id')}",
        }
        for p in data.get("patents", [])
    ]
    return SourceResult(
        "patents",
        "ok",
        total=data.get("total_hits", len(items)),
        items=items,
        note="US patents (PatentsView); Indian and other filings are not covered by this source",
    )
