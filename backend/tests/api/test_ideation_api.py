"""API tests for the stateless ideation/route/completeness endpoints (no DB)."""

from __future__ import annotations

import pytest_asyncio
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_route_endpoint(client: AsyncClient):
    r = await client.post(
        "/api/v1/orchestrator/route", json={"message": "which scheme am I eligible for?"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["swarm"] == "scheme"
    assert body["action"] == "route"


async def test_roadmap_endpoint(client: AsyncClient):
    r = await client.post(
        "/api/v1/ideation/roadmap",
        json={"text": "An affordable agri IoT device to help farmers with irrigation."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["idea"]["domain"] == "agritech"
    assert 5 <= len(body["milestones"]) <= 15
    assert body["critical_path"][0] == "m1"
    # critical milestones match the critical path
    crit = [m["id"] for m in body["milestones"] if m["critical"]]
    assert crit == body["critical_path"]
    assert 0 <= body["feasibility_score"] <= 100


async def test_roadmap_validation_error(client: AsyncClient):
    r = await client.post("/api/v1/ideation/roadmap", json={"text": "x"})  # too short
    assert r.status_code == 422
    assert r.json()["error_code"] == "VALIDATION_FAILED"


async def test_completeness_endpoint(client: AsyncClient):
    payload = {
        "founder": {
            "name": "Selvi",
            "email": "s@e.com",
            "phone": "+919876543210",
            "date_of_birth": "1988-01-01",
            "gender": "female",
            "state": "Tamil Nadu",
            "district": "Erode",
            "city": "Erode",
        }
    }
    r = await client.post("/api/v1/profiles/completeness", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 40
    assert body["tier"] == "basic"
