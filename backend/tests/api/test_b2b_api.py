"""API test for the B2B match endpoint (stateless, no DB)."""

from __future__ import annotations

import pytest_asyncio
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_b2b_match_endpoint(client: AsyncClient):
    payload = {
        "category": "yarn",
        "spec": "combed cotton yarn 40s count",
        "quantity": 2000,
        "budget_per_unit": 190,
        "district": "Tiruppur",
        "state": "Tamil Nadu",
    }
    r = await client.post("/api/v1/b2b/match", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    top = body["matches"][0]
    assert top["supply"]["id"] == "y1"
    assert 0 <= top["weight"] <= 100
    # per-component breakdown present
    assert set(top["breakdown"]) == {
        "spec_similarity",
        "price_fit",
        "capacity_fit",
        "geo_proximity",
    }


async def test_b2b_match_validation(client: AsyncClient):
    r = await client.post(
        "/api/v1/b2b/match", json={"category": "yarn", "quantity": 0, "budget_per_unit": 10}
    )
    assert r.status_code == 422
