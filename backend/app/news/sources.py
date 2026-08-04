"""Allowlisted news sources (Task 6.1 · P-44).

An allowlist, never open crawling. Three reasons:

  1. **Legal.** Fetching is restricted to feeds a publisher offers for syndication
     (RSS/Atom) or to government portals that publish openly. `robots_ok` records
     that a source's robots.txt has actually been checked; nothing is fetched
     until it has.
  2. **Copyright.** We store a short extract and our own summary, never article
     bodies. See `news.pipeline.MAX_EXTRACT_CHARS`.
  3. **Trust.** A founder acting on a scheme deadline needs to know whether it
     came from a government portal or an aggregator. `tier` encodes that, and it
     weights ranking.

`verified=False` means the feed URL is a best-effort guess that no one has
confirmed. Those sources are **excluded from fetching** until checked — an
unverified URL silently 404ing is worse than an admitted gap.
"""

from __future__ import annotations

from dataclasses import dataclass

# tier → trust weight used by ranking
TIER_TRUST = {
    "government": 1.00,  # official portals, primary source for schemes
    "mainstream": 0.80,  # established newspapers with editorial standards
    "trade": 0.65,  # startup/business trade press
    "aggregator": 0.45,  # syndicators; useful for breadth, weakest for fact
}


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    domain: str
    feed_url: str
    tier: str
    language: str  # en | ta | hi
    focus: tuple[str, ...]
    verified: bool = False
    robots_ok: bool = False

    @property
    def trust(self) -> float:
        return TIER_TRUST.get(self.tier, 0.4)

    @property
    def fetchable(self) -> bool:
        """Only fetch what has been confirmed to exist and to permit it."""
        return self.verified and self.robots_ok


# ---------------------------------------------------------------------------
# The allowlist.
#
# HONESTY NOTE: every feed_url below is unverified. They are plausible
# conventional paths for each publisher, not confirmed endpoints, and none has
# had its robots.txt checked from this environment. So `fetchable` is False for
# all of them and the live fetcher will refuse every one until a human verifies
# the URL and the crawl terms. The offline fixture provider is what actually
# runs today. Do not flip `verified=True` without opening the feed.
# ---------------------------------------------------------------------------

SOURCES: list[Source] = [
    Source(
        "startuptn",
        "StartupTN",
        "startuptn.in",
        "https://startuptn.in/feed/",
        "government",
        "en",
        ("schemes", "tn", "startups", "events"),
    ),
    Source(
        "tansim",
        "TANSIM (TN Startup and Innovation Mission)",
        "tansim.tn.gov.in",
        "https://tansim.tn.gov.in/feed/",
        "government",
        "en",
        ("schemes", "tn", "policy"),
    ),
    Source(
        "startupindia",
        "Startup India",
        "startupindia.gov.in",
        "https://www.startupindia.gov.in/rss/notifications.xml",
        "government",
        "en",
        ("schemes", "dpiit", "policy", "national"),
    ),
    Source(
        "msme",
        "Ministry of MSME",
        "msme.gov.in",
        "https://msme.gov.in/feed",
        "government",
        "en",
        ("schemes", "msme", "credit"),
    ),
    Source(
        "businessline",
        "The Hindu BusinessLine",
        "thehindubusinessline.com",
        "https://www.thehindubusinessline.com/economy/feeder/default.rss",
        "mainstream",
        "en",
        ("business", "economy", "tn"),
    ),
    Source(
        "newindianexpress",
        "The New Indian Express — Tamil Nadu",
        "newindianexpress.com",
        "https://www.newindianexpress.com/states/tamil-nadu/rss",
        "mainstream",
        "en",
        ("tn", "business", "policy"),
    ),
    Source(
        "dinamalar",
        "Dinamalar (தினமலர்)",
        "dinamalar.com",
        "https://www.dinamalar.com/rss.asp?cat=business",
        "mainstream",
        "ta",
        ("tn", "business", "tamil"),
    ),
    Source(
        "dinamani",
        "Dinamani (தினமணி)",
        "dinamani.com",
        "https://www.dinamani.com/business/rss",
        "mainstream",
        "ta",
        ("tn", "business", "tamil"),
    ),
    Source(
        "yourstory",
        "YourStory",
        "yourstory.com",
        "https://yourstory.com/feed",
        "trade",
        "en",
        ("startups", "funding", "founders"),
    ),
    Source(
        "inc42",
        "Inc42",
        "inc42.com",
        "https://inc42.com/feed/",
        "trade",
        "en",
        ("startups", "funding", "policy"),
    ),
    Source(
        "entrackr",
        "Entrackr",
        "entrackr.com",
        "https://entrackr.com/feed/",
        "trade",
        "en",
        ("funding", "startups"),
    ),
]

BY_ID = {s.id: s for s in SOURCES}


def fetchable_sources() -> list[Source]:
    """Sources cleared for live fetching. Empty until a human verifies them."""
    return [s for s in SOURCES if s.fetchable]


def is_allowlisted(url: str) -> bool:
    """True only if the URL's host matches an allowlisted domain.

    Checked on every fetch, so a redirect cannot walk the crawler off the list.
    """
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower()
    # NOT lstrip("www."): that strips any leading char in {w, .}, so the
    # unrelated domain "wwwstartuptn.in" would reduce to "startuptn.in" and be
    # accepted. Remove the literal prefix instead.
    if host.startswith("www."):
        host = host[4:]
    return any(host == s.domain or host.endswith("." + s.domain) for s in SOURCES)
