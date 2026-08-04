"""API test for the news board (stateless, offline corpus)."""

from __future__ import annotations

import pytest_asyncio
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_board_returns_ranked_attributed_items(client: AsyncClient):
    r = await client.post("/api/v1/news/board", json={"founder": {}, "limit": 5})
    assert r.status_code == 200
    b = r.json()

    assert len(b["items"]) <= 5
    scores = [i["score"] for i in b["items"]]
    assert scores == sorted(scores, reverse=True)

    for i in b["items"]:
        assert i["source_name"], "an item must name its publisher"
        assert i["url"].startswith("http")
        assert i["why"], "an item must explain why it ranked here"
        assert len(i["summary"]) <= 240


async def test_board_declares_that_it_is_not_live(client: AsyncClient):
    """The board must never let a demo corpus pass as real reporting."""
    r = await client.post("/api/v1/news/board", json={})
    b = r.json()
    assert b["is_live"] is False
    assert b["provider"] == "fixture"
    assert "synthetic" in b["notice"].lower()


async def test_board_lists_its_sources_and_their_status(client: AsyncClient):
    r = await client.post("/api/v1/news/board", json={})
    sources = r.json()["sources"]
    assert len(sources) >= 10
    assert {s["tier"] for s in sources} <= {"government", "mainstream", "trade", "aggregator"}
    # nothing is cleared for live fetching until a human verifies it
    assert all(s["fetchable"] is False for s in sources)


async def test_founder_context_changes_the_order(client: AsyncClient):
    plain = await client.post("/api/v1/news/board", json={"limit": 10})
    tuned = await client.post(
        "/api/v1/news/board",
        json={"founder": {"sector": "agritech", "district": "Coimbatore"}, "limit": 10},
    )
    assert plain.status_code == tuned.status_code == 200
    assert [i["id"] for i in plain.json()["items"]] != [i["id"] for i in tuned.json()["items"]]


async def test_limit_is_validated(client: AsyncClient):
    r = await client.post("/api/v1/news/board", json={"limit": 500})
    assert r.status_code == 422
