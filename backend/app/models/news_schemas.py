"""Pydantic schemas for the news board (Task 6.1)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NewsBoardIn(BaseModel):
    founder: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=8, ge=1, le=40)
    language: str | None = None


class NewsItemOut(BaseModel):
    id: str
    title: str
    summary: str
    url: str
    source_id: str
    source_name: str
    tier: str
    published: str
    language: str
    tags: list[str]
    score: int
    why: list[str]
    duplicates: list[str]


class SourceOut(BaseModel):
    id: str
    name: str
    domain: str
    tier: str
    language: str
    verified: bool
    fetchable: bool


class NewsBoardOut(BaseModel):
    provider: str
    is_live: bool
    generated: str
    total_fetched: int
    items: list[NewsItemOut]
    sources: list[SourceOut]
    notice: str
