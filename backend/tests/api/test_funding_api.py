"""API test for the funding readiness endpoint (stateless, no DB)."""

from __future__ import annotations

import pytest_asyncio
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_readiness_endpoint(client: AsyncClient):
    r = await client.post(
        "/api/v1/funding/readiness",
        json={"profile": {"is_registered": True, "stage": "mvp", "team_size": 2}},
    )
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["overall"] <= 100
    assert body["band"] in {"Not Ready", "Developing", "Ready", "Highly Ready"}
    assert set(body["dimensions"]) == {"team", "product", "traction", "financial", "pitch", "legal"}
    # weak dimensions produce ranked recommendations
    assert len(body["gaps"]) >= 1
    assert body["gaps"][0]["impact"] in {"High", "Medium", "Low"}


async def test_pipeline_advance_endpoint(client: AsyncClient):
    r = await client.post(
        "/api/v1/funding/pipeline/advance",
        json={
            "entry": {"investor_id": "angel_ravi", "stage": "initial_contact", "amount": 2000000},
            "to_stage": "pitch_scheduled",
            "at": "2026-03-01",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["entry"]["stage"] == "pitch_scheduled"
    assert [h["stage"] for h in body["entry"]["history"]] == [
        "initial_contact",
        "pitch_scheduled",
    ]
    assert "pitch_delivered" in body["next_stages"]


async def test_pipeline_advance_rejects_stage_skip(client: AsyncClient):
    r = await client.post(
        "/api/v1/funding/pipeline/advance",
        json={
            "entry": {"investor_id": "angel_ravi", "stage": "initial_contact"},
            "to_stage": "term_sheet",
        },
    )
    assert r.status_code == 422
    assert r.json()["error_code"] == "INVALID_PIPELINE_TRANSITION"


async def test_pipeline_board_endpoint(client: AsyncClient):
    r = await client.post(
        "/api/v1/funding/pipeline/board",
        json={
            "entries": [
                {"investor_id": "a", "stage": "negotiation", "amount": 1000000},
                {"investor_id": "b", "stage": "closed_won", "amount": 3000000},
                {"investor_id": "c", "stage": "closed_lost", "amount": 500000},
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stages"][0] == "initial_contact"
    assert len(body["columns"]) == len(body["stages"])
    m = body["metrics"]
    assert m["total"] == 3 and m["won"] == 1 and m["lost"] == 1
    assert m["win_rate"] == 50
    # only the open deal counts toward pipeline value, discounted by stage
    assert m["pipeline_value"] == 1000000
    assert m["weighted_value"] == 800000
