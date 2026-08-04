"""News domain models (Task 6.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RawArticle:
    """What a fetcher returns. `extract` is a short lead, never the full body."""

    source_id: str
    title: str
    url: str
    published: str  # ISO date
    extract: str = ""
    language: str = "en"
    tags: tuple[str, ...] = ()


@dataclass
class NewsItem:
    """A ranked, summarised, attributed item ready for the board."""

    id: str
    title: str
    summary: str
    url: str
    source_id: str
    source_name: str
    tier: str
    published: str
    language: str
    tags: list[str] = field(default_factory=list)
    score: int = 0
    why: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "tier": self.tier,
            "published": self.published,
            "language": self.language,
            "tags": self.tags,
            "score": self.score,
            "why": self.why,
            "duplicates": self.duplicates,
        }


@dataclass
class FounderContext:
    """What the board ranks against. Every field optional — an anonymous
    visitor still gets a sensible, if less personal, ordering."""

    sector: str | None = None
    stage: str | None = None
    district: str | None = None
    interests: tuple[str, ...] = ()
    language: str = "en"

    @classmethod
    def from_dict(cls, d: dict | None) -> FounderContext:
        d = d or {}
        return cls(
            sector=d.get("sector"),
            stage=d.get("stage"),
            district=d.get("district"),
            interests=tuple(d.get("interests") or ()),
            language=str(d.get("language") or "en"),
        )


def today_iso() -> str:
    return date.today().isoformat()
