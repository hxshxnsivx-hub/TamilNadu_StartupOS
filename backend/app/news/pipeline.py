"""News pipeline (Task 6.1 · P-44) — dedupe → rank → summarise → attribute.

Deterministic and offline-testable, like every other engine here. The only
non-deterministic step is optional live fetching, which is behind a provider and
disabled until sources are verified.

Copyright posture, enforced rather than intended:
  · we never store or serve an article body — `MAX_EXTRACT_CHARS` caps what a
    fetcher may keep, and the cap is asserted in tests
  · summaries are our own compression, held under `MAX_SUMMARY_CHARS`
  · every item carries source name, publisher domain and a link back
  · nothing is served without attribution — an item with no source is dropped
"""

from __future__ import annotations

import hashlib
import re
from datetime import date

from app.news.models import FounderContext, NewsItem, RawArticle
from app.news.sources import BY_ID

# Hard limits. These are the copyright guardrails; the tests assert them.
MAX_EXTRACT_CHARS = 320
MAX_SUMMARY_CHARS = 240

# Ranking weights
W_RELEVANCE = 0.40
W_RECENCY = 0.25
W_TRUST = 0.20
W_ACTION = 0.15

# Words that mark something a founder can act on rather than merely read about.
_ACTIONABLE = (
    "deadline",
    "apply",
    "application",
    "last date",
    "opens",
    "launch",
    "scheme",
    "grant",
    "subsidy",
    "tender",
    "registration",
    "funding",
    "cohort",
    "incubat",
)

_STOP = {
    "the",
    "a",
    "an",
    "of",
    "for",
    "to",
    "in",
    "on",
    "and",
    "with",
    "at",
    "by",
    "from",
    "as",
    "is",
    "are",
    "its",
    "it",
    "new",
    "after",
    "over",
    "amid",
}


def item_id(source_id: str, url: str) -> str:
    """A stable id for an article.

    Not `hash()`: Python randomises string hashing per process, so ids would
    change on every restart and break client caching, list keys and any
    "already seen" tracking. A digest of the URL is stable everywhere.
    """
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{source_id}:{digest}"


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _days_old(published: str, today: date | None = None) -> int:
    try:
        d = date.fromisoformat(published)
    except ValueError:
        return 999
    return max(0, ((today or date.today()) - d).days)


def summarise(article: RawArticle) -> str:
    """Compress an extract to a short, attributable summary.

    Deliberately extractive and deterministic: takes the opening sentences up to
    the cap. An LLM could paraphrase better, but a paraphrase that drifts from
    the source is worse than a faithful trim on a board a founder may act on.
    """
    text = " ".join((article.extract or article.title).split())
    if len(text) <= MAX_SUMMARY_CHARS:
        return text
    cut = text[:MAX_SUMMARY_CHARS]
    # prefer a sentence boundary, else a word boundary
    for stop in (". ", "। ", "! ", "? "):
        i = cut.rfind(stop)
        if i > MAX_SUMMARY_CHARS * 0.5:
            return cut[: i + 1].strip()
    i = cut.rfind(" ")
    return (cut[:i] if i > 0 else cut).rstrip() + "…"


def _relevance(article: RawArticle, ctx: FounderContext) -> tuple[float, list[str]]:
    why: list[str] = []
    hay = f"{article.title} {article.extract} {' '.join(article.tags)}".lower()
    score = 0.35  # a floor, so an anonymous visitor still gets a sane order

    if ctx.sector and ctx.sector.lower() in hay:
        score += 0.30
        why.append(f"mentions {ctx.sector}")
    if ctx.district and ctx.district.lower() in hay:
        score += 0.15
        why.append(f"local to {ctx.district}")
    if ctx.stage and ctx.stage.lower() in hay:
        score += 0.10
        why.append(f"relevant at {ctx.stage} stage")
    for interest in ctx.interests:
        if interest.lower() in hay:
            score += 0.08
            why.append(f"matches your interest in {interest}")
            break
    if "tn" in article.tags or "tamil nadu" in hay:
        score += 0.12
        why.append("Tamil Nadu")

    return min(1.0, score), why


def _actionability(article: RawArticle) -> tuple[float, list[str]]:
    hay = f"{article.title} {article.extract}".lower()
    hits = [w for w in _ACTIONABLE if w in hay]
    if not hits:
        return 0.0, []
    return min(1.0, 0.4 + 0.2 * len(hits)), ["something to act on"]


def rank(
    articles: list[RawArticle],
    ctx: FounderContext | None = None,
    *,
    today: date | None = None,
) -> list[NewsItem]:
    """Dedupe near-identical stories, score the survivors, return them ordered."""
    ctx = ctx or FounderContext()
    today = today or date.today()

    # --- dedupe: the same story from several outlets is one story ---
    kept: list[tuple[RawArticle, set[str], list[str]]] = []
    for art in articles:
        toks = _tokens(art.title)
        for i, (other, other_toks, dupes) in enumerate(kept):
            if _jaccard(toks, other_toks) >= 0.6:
                # keep whichever source is more trustworthy as the canonical one
                if BY_ID[art.source_id].trust > BY_ID[other.source_id].trust:
                    kept[i] = (art, toks, [*dupes, other.source_id])
                else:
                    kept[i] = (other, other_toks, [*dupes, art.source_id])
                break
        else:
            kept.append((art, toks, []))

    items: list[NewsItem] = []
    for art, _toks, dupes in kept:
        src = BY_ID.get(art.source_id)
        if src is None:
            continue  # never serve an item we cannot attribute

        rel, why_rel = _relevance(art, ctx)
        age = _days_old(art.published, today)
        recency = max(0.0, 1.0 - age / 30)  # linear decay over a month
        act, why_act = _actionability(art)

        raw = W_RELEVANCE * rel + W_RECENCY * recency + W_TRUST * src.trust + W_ACTION * act
        why = [*why_rel, *why_act]
        if src.tier == "government":
            why.append("official source")
        if age <= 2:
            why.append("published in the last 48 hours")

        items.append(
            NewsItem(
                id=item_id(art.source_id, art.url),
                title=art.title,
                summary=summarise(art),
                url=art.url,
                source_id=src.id,
                source_name=src.name,
                tier=src.tier,
                published=art.published,
                language=art.language,
                tags=list(art.tags),
                score=int(round(raw * 100)),
                why=why[:3],
                duplicates=sorted(set(dupes)),
            )
        )

    items.sort(key=lambda i: (-i.score, i.published, i.id))
    return items
