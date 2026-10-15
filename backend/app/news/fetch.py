"""News fetch providers (Task 6.1).

Same managed-API-first shape as the LLM/translation services: one interface, a
deterministic offline provider that the whole test suite runs against, and a
live provider that is refused until sources are verified.

The live fetcher is deliberately hard to switch on. It will not fetch a URL that
is not allowlisted, will not fetch a source whose robots.txt has not been
checked, and re-checks the allowlist after redirects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.logging import get_logger
from app.news import fixtures
from app.news.models import RawArticle
from app.news.pipeline import MAX_EXTRACT_CHARS
from app.news.sources import fetchable_sources, is_allowlisted

log = get_logger("news")


class NewsFetcher(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> list[RawArticle]: ...


class FixtureNewsFetcher(NewsFetcher):
    """Deterministic offline corpus. What runs today, and in every test."""

    name = "fixture"

    async def fetch(self) -> list[RawArticle]:
        return [_clamp(a) for a in fixtures.ARTICLES]


class HttpNewsFetcher(NewsFetcher):
    """Live RSS/Atom fetching over the allowlist.

    Unimplemented on purpose. Turning this on is a deliberate act that needs:
      1. each source's feed URL opened and confirmed,
      2. its robots.txt and terms read, then `verified`/`robots_ok` set,
      3. a polite crawl policy — conditional GETs, backoff, a real User-Agent.
    Shipping a crawler that silently 404s or ignores robots would be worse than
    shipping none, so this raises instead of guessing.
    """

    name = "http"

    async def fetch(self) -> list[RawArticle]:
        allowed = fetchable_sources()
        if not allowed:
            raise RuntimeError(
                "No source has been verified for live fetching. Confirm each feed "
                "URL and its robots.txt, then set verified/robots_ok in sources.py."
            )
        raise NotImplementedError(
            "Live fetching is not implemented yet — see the class docstring for "
            "the steps it requires."
        )

    @staticmethod
    def guard(url: str) -> None:
        """Refuse anything off the allowlist. Call again after every redirect."""
        if not is_allowlisted(url):
            raise PermissionError(f"Refusing to fetch off-allowlist URL: {url}")


def _clamp(a: RawArticle) -> RawArticle:
    """Enforce the extract cap at the boundary, whatever a provider hands back."""
    if len(a.extract) <= MAX_EXTRACT_CHARS:
        return a
    return RawArticle(
        source_id=a.source_id,
        title=a.title,
        url=a.url,
        published=a.published,
        extract=a.extract[:MAX_EXTRACT_CHARS].rstrip(),
        language=a.language,
        tags=a.tags,
    )


@lru_cache(maxsize=1)
def get_fetcher() -> NewsFetcher:
    """Fixtures until a live source is verified; then the HTTP provider."""
    if fetchable_sources():
        log.info("news.fetcher", provider="http")
        return HttpNewsFetcher()
    return FixtureNewsFetcher()
