"""Source connectors for prior-art research. Each returns a SourceResult.

  papers    OpenAlex works (free; a key lifts the small shared daily budget)
  trials    ClinicalTrials.gov v2 (free, no key) — health ideas
  projects  GitHub repository search (free; a token lifts the rate limit)
  patents   PatentsView PatentSearch API (free key required)

Every result says what happened — ok, no_key, budget_exhausted, error — so a
report never implies "nothing exists" when the truth is "not searched".
Responses are cached for `research_cache_days`, in Redis when it runs and on disk.
A 429 pauses that source for everyone until its Retry-After; RESEARCH_DAILY_LIMIT
caps requests per source per day (0: no cap).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.redis import get_redis

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
    """Research responses: Redis first when it is running, then disk (SYSTEM-DESIGN.md §4).

    Keys are hashes of the request, so API keys in parameters never appear in a
    key. A disk hit is copied into Redis so other workers find it there.
    """

    def __init__(self, root: str | Path, days: int) -> None:
        self.root = Path(root)
        self.ttl = days * 86400

    @staticmethod
    def _hash(key: str) -> str:
        return hashlib.sha1(key.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self.root / (self._hash(key) + ".json")

    def get(self, key: str) -> Any | None:
        p = self._path(key)
        if not p.exists() or time.time() - p.stat().st_mtime > self.ttl:
            return None
        return json.loads(p.read_text(encoding="utf8"))

    def put(self, key: str, value: Any) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(json.dumps(value), encoding="utf8")

    async def aget(self, key: str) -> Any | None:
        r = await get_redis()
        if r is not None:
            try:
                if (doc := await r.get(f"rs:{self._hash(key)}")) is not None:
                    return json.loads(doc)
            except Exception:  # Redis trouble is never a reason to fail a search
                r = None
        hit = self.get(key)
        if hit is not None and r is not None:
            await _quiet(r.set(f"rs:{self._hash(key)}", json.dumps(hit), ex=self.ttl))
        return hit

    async def aput(self, key: str, value: Any) -> None:
        self.put(key, value)
        r = await get_redis()
        if r is not None:
            await _quiet(r.set(f"rs:{self._hash(key)}", json.dumps(value), ex=self.ttl))


async def _quiet(awaitable) -> None:
    with contextlib.suppress(Exception):  # Redis trouble never fails a search
        await awaitable


# ---- rate limits: remembered pauses and an optional daily cap per source ----------

_SOURCE_BY_HOST = {
    "api.openalex.org": "openalex",
    "clinicaltrials.gov": "ctgov",
    "api.github.com": "github",
    "search.patentsview.org": "patentsview",
    "ops.epo.org": "epo",
}
MAX_PAUSE_S = 86400
_local_pause: dict[str, float] = {}  # source -> monotonic time the pause ends
_local_count: dict[str, int] = {}  # "source:date" -> requests sent


def _source(url: str) -> str:
    return _SOURCE_BY_HOST.get(httpx.URL(url).host, "other")


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


async def _paused(source: str) -> bool:
    r = await get_redis()
    if r is not None:
        try:
            return bool(await r.exists(f"rs:neg:{source}"))
        except Exception:
            pass
    return _local_pause.get(source, 0) > time.monotonic()


async def _pause(source: str, retry_after: str | None) -> None:
    """A 429: stop calling this source until it says to retry, for everyone."""
    try:
        seconds = int(float(retry_after)) if retry_after else 60
    except ValueError:
        seconds = 60
    seconds = max(1, min(seconds, MAX_PAUSE_S))
    _local_pause[source] = time.monotonic() + seconds
    r = await get_redis()
    if r is not None:
        await _quiet(r.set(f"rs:neg:{source}", "1", ex=seconds))


async def _over_budget(source: str) -> bool:
    """Count one request; True when today's cap for this source is used up."""
    limit = get_settings().research_daily_limit
    key = f"{source}:{_today()}"
    r = await get_redis()
    used = None
    if r is not None:
        try:
            used = await r.incr(f"budget:{key}")
            if used == 1:
                await r.expire(f"budget:{key}", 2 * 86400)
        except Exception:
            used = None
    if used is None:
        _local_count[key] = used = _local_count.get(key, 0) + 1
    return bool(limit) and used > limit


async def _get_json(
    client: httpx.AsyncClient, cache: Cache | None, url: str, **kw
) -> tuple[int, Any]:
    key = f"GET {url} {json.dumps(kw.get('params', {}), sort_keys=True)}"
    if cache and (hit := await cache.aget(key)) is not None:
        return 200, hit
    source = _source(url)
    if await _paused(source):
        return 429, f"{source} asked us to wait; paused"
    if await _over_budget(source):
        return 429, f"daily request limit for {source} reached"
    r = await client.get(url, **kw)
    if r.status_code == 200:
        data = r.json()
        if cache:
            await cache.aput(key, data)
        return 200, data
    if r.status_code == 429:
        await _pause(source, r.headers.get("Retry-After"))
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


async def paper_count(
    client: httpx.AsyncClient,
    query: str,
    cache: Cache | None = None,
    filter: str | None = None,
) -> SourceResult:
    """How many works match: one cheap request, for novelty checks.

    OpenAlex reads spaces as AND, supports OR inside parentheses and exact
    phrases in quotes, so `(EEG OR "brain-computer interface") "nurse call system"`
    counts works on both parts together.
    """
    key = get_settings().openalex_api_key
    params = {"search": query, "per_page": 1, "select": "id", **({"api_key": key} if key else {})}
    if filter:
        params["filter"] = filter
    status, data = await _get_json(client, cache, OPENALEX, params=params)
    if status == 429:
        return SourceResult(
            "papers",
            "budget_exhausted",
            note="OpenAlex daily budget used up for this network; add OPENALEX_API_KEY",
        )
    if status != 200:
        return SourceResult("papers", "error", note=f"OpenAlex returned {status}")
    return SourceResult("papers", "ok", total=data.get("meta", {}).get("count", 0))


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
    """Worldwide patents with the Indian filings among them (EPO, free registration);
    else US patents (PatentsView, free key); else reported as not searched."""
    st = get_settings()
    if st.epo_ops_key and st.epo_ops_secret:
        return await epo_patents(client, query, cache)
    key = st.patentsview_api_key
    if not key:
        return SourceResult(
            "patents",
            "no_key",
            note="Patents not searched: register free with the EPO (EPO_OPS_KEY and"
            " EPO_OPS_SECRET) for worldwide and Indian patents",
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


# ---- EPO Open Patent Services: worldwide patents, Indian filings included -----------
#
# Free with registration (developers.epo.org; fair use up to 4 GB a week, about ten
# searches a minute). OAuth client credentials give a token for about 20 minutes.
# Two searches per idea: worldwide (closest ten) and Indian publications only
# (pn=IN). A search with no hits answers 404, which means none found, not an error.

EPO_TOKEN = "https://ops.epo.org/3.2/auth/accesstoken"
EPO_SEARCH = "https://ops.epo.org/3.2/rest-services/published-data/search/biblio"
EPO_TERMS = 3  # all of these words in the title or abstract: precise without being empty
_epo_token: tuple[str, float] | None = None  # (token, monotonic expiry)


async def _epo_auth(client: httpx.AsyncClient) -> str | None:
    global _epo_token
    if _epo_token and _epo_token[1] > time.monotonic():
        return _epo_token[0]
    st = get_settings()
    r = await client.post(
        EPO_TOKEN,
        auth=(st.epo_ops_key, st.epo_ops_secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": UA},
    )
    if r.status_code != 200:
        return None
    data = r.json()
    ttl = int(float(data.get("expires_in") or 1200))
    _epo_token = (data["access_token"], time.monotonic() + max(60, ttl - 60))
    return _epo_token[0]


def epo_cql(query: str, country: str | None = None) -> str:
    """Public-vocabulary words to a CQL search on titles and abstracts."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]*", query)[:EPO_TERMS]
    cql = f'ta all "{" ".join(words)}"'
    return f"{cql} and pn={country}" if country else cql


def _text(v: Any) -> str:
    """OPS JSON wraps text as {"$": "..."}."""
    if isinstance(v, dict):
        return str(v.get("$", ""))
    return "" if v is None else str(v)


def _as_list(v: Any) -> list:
    return v if isinstance(v, list) else ([] if v is None else [v])


def epo_documents(data: dict) -> tuple[int, list[dict]]:
    """(total hits, the documents) from a biblio search answer."""
    found = (data.get("ops:world-patent-data") or {}).get("ops:biblio-search") or {}
    total = int(found.get("@total-result-count") or 0)
    docs = _as_list((found.get("ops:search-result") or {}).get("exchange-documents"))
    items = []
    for d in docs:
        ex = d.get("exchange-document", d) if isinstance(d, dict) else {}
        ex = _as_list(ex)[0] if ex else {}
        bib = ex.get("bibliographic-data") or {}
        titles = _as_list(bib.get("invention-title"))
        title = next((_text(t) for t in titles if t.get("@lang") == "en"), "")
        title = title or (_text(titles[0]) if titles else "")
        ids = _as_list((bib.get("publication-reference") or {}).get("document-id"))
        date = next((_text(i.get("date")) for i in ids if i.get("date")), "")
        applicants = []
        for a in _as_list(((bib.get("parties") or {}).get("applicants") or {}).get("applicant")):
            if a.get("@data-format") == "docdb":
                continue  # the same names again, in capitals
            name = _text((a.get("applicant-name") or {}).get("name")).strip(" ,")
            if name and name not in applicants:
                applicants.append(name)
        country, number, kind = (
            ex.get("@country", ""),
            ex.get("@doc-number", ""),
            ex.get("@kind", ""),
        )
        items.append(
            {
                "id": f"{country}{number}{kind}",
                "country": country,
                "title": title,
                "date": f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) == 8 else date,
                "assignees": applicants[:3],
                "url": f"https://worldwide.espacenet.com/patent/search?q=pn%3D{country}{number}",
            }
        )
    return total, items


async def epo_patents(
    client: httpx.AsyncClient, query: str, cache: Cache | None = None
) -> SourceResult:
    if not re.search(r"[A-Za-z]", query):
        return SourceResult("patents", "skipped", note="Patents not searched: no safe terms")
    token = await _epo_auth(client)
    if token is None:
        return SourceResult(
            "patents", "error", note="EPO did not accept the key; check EPO_OPS_KEY and SECRET"
        )
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": UA}
    found: dict[str, tuple[int, list[dict]]] = {}
    for scope, country, size in (("world", None, 10), ("india", "IN", 5)):
        params = {"q": epo_cql(query, country), "Range": f"1-{size}"}
        status, data = await _get_json(client, cache, EPO_SEARCH, params=params, headers=headers)
        if status == 404:  # OPS answers "no entity found" for zero hits
            found[scope] = (0, [])
        elif status == 200:
            found[scope] = epo_documents(data)
        elif scope == "world":
            if status == 429:
                return SourceResult("patents", "budget_exhausted", note="EPO asked us to wait")
            return SourceResult("patents", "error", note=f"EPO returned {status}")
        else:
            found[scope] = (0, [])  # India is a refinement: the world result still stands
    world_total, world_items = found["world"]
    india_total, india_items = found.get("india", (0, []))
    return SourceResult(
        "patents",
        "ok",
        total=world_total,
        items=world_items,
        note="Worldwide patents, Indian filings included (EPO Open Patent Services)",
        extra={"india": {"total": india_total, "items": india_items}},
    )
