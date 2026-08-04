"""API test for the scheme eligibility endpoint (stateless, no DB)."""

from __future__ import annotations

import pytest_asyncio
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_eligibility_endpoint(client: AsyncClient):
    payload = {
        "founder": {
            "state": "Tamil Nadu",
            "gender": "female",
            "caste_category": "sc",
            "first_graduate": True,
            "date_of_birth": "1996-01-01",
        },
        "startup": {
            "entity_type": "private_limited",
            "stage": "mvp",
            "dpiit_recognized": True,
            "incorporation_age_years": 1,
            "annual_revenue": 500000,
        },
    }
    r = await client.post("/api/v1/schemes/eligibility", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["total_checked"] == 8
    ids = {s["id"] for s in body["eligible"]}
    assert {"sisfs", "tanseed", "needs"} <= ids
    # every ineligible scheme carries at least one reason
    for i in body["ineligible"]:
        assert len(i["reasons"]) >= 1


async def test_ineligible_reasons_present(client: AsyncClient):
    payload = {"founder": {"state": "Karnataka", "age": 50}, "startup": {"dpiit_recognized": False}}
    r = await client.post("/api/v1/schemes/eligibility", json=payload)
    body = r.json()
    by_id = {i["scheme"]["id"]: i for i in body["ineligible"]}
    assert any("DPIIT" in x for x in by_id["sisfs"]["reasons"])
