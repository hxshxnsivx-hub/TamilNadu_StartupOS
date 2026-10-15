"""News board endpoint (Task 6.1 · P-44)."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.news_schemas import NewsBoardIn, NewsBoardOut
from app.news.fetch import FixtureNewsFetcher, get_fetcher
from app.news.models import FounderContext, today_iso
from app.news.pipeline import rank
from app.news.sources import SOURCES

router = APIRouter(prefix="/api/v1/news", tags=["news"])

_DEMO_NOTICE = (
    "Demonstration corpus. No source has been verified for live fetching yet, so "
    "these items are synthetic stand-ins, not real reporting."
)
_LIVE_NOTICE = "Live items from allowlisted publishers. Follow the link for the full article."


@router.post("/board", response_model=NewsBoardOut)
async def board(body: NewsBoardIn) -> NewsBoardOut:
    """Ranked, attributed news for a founder.

    Every item links back to its publisher and carries the reason it was ranked
    where it was. The response states plainly whether the corpus is live or a
    demonstration set — a board that looked real while serving fixtures would
    mislead a founder acting on a deadline.
    """
    fetcher = get_fetcher()
    articles = await fetcher.fetch()

    ctx = FounderContext.from_dict(body.founder)
    if body.language:
        ctx.language = body.language

    items = rank(articles, ctx)

    is_live = not isinstance(fetcher, FixtureNewsFetcher)
    return NewsBoardOut(
        provider=fetcher.name,
        is_live=is_live,
        generated=today_iso(),
        total_fetched=len(articles),
        items=[i.to_dict() for i in items[: body.limit]],
        sources=[
            {
                "id": s.id,
                "name": s.name,
                "domain": s.domain,
                "tier": s.tier,
                "language": s.language,
                "verified": s.verified,
                "fetchable": s.fetchable,
            }
            for s in SOURCES
        ],
        notice=_LIVE_NOTICE if is_live else _DEMO_NOTICE,
    )
