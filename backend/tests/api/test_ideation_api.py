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


async def test_domains_list_the_tea_pack(client: AsyncClient):
    r = await client.get("/api/v1/ideation/domains")
    assert r.status_code == 200
    tea = next(d for d in r.json() if d["id"] == "tea_infusions")
    assert "Mint hibiscus infusion" in tea["starting_variants"]
    assert any(q["slot"] == "production_mode" for q in tea["questions"])


async def test_plan_returns_variants_costs_and_a_specific_roadmap(client: AsyncClient):
    r = await client.post(
        "/api/v1/ideation/plan",
        json={
            "text": "I want to start a tea brand",
            "slots": {"district": "Coimbatore", "stage": "idea", "funding_route": "debt"},
            "variants": ["mint lemon", "mint hibiscus"],
            "format": "loose_leaf",
            "production_mode": "co_packer",
            "channels": ["online"],
            "monthly_packs": 800,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["domain"]["id"] == "tea_infusions"
    assert {v["kind"] for v in body["variants"]} == {"tea", "herbal infusion"}
    assert body["costs"]["rows"] and body["costs"]["example_prices_used"]
    titles = [m["title"] for m in body["roadmap"]["milestones"]]
    assert "Contract a co-packer and run a pilot batch" in titles
    assert 5 <= len(titles) <= 15
    assert body["roadmap"]["milestones"][0]["from"] in ("common", "tea_infusions")


async def test_plan_rejects_unknown_domain(client: AsyncClient):
    r = await client.post("/api/v1/ideation/plan", json={"domain": "spaceships"})
    assert r.status_code == 422


async def test_categories_registry_and_hybrids(client: AsyncClient):
    cats = (await client.get("/api/v1/ideation/categories")).json()
    assert len(cats) == 12 and all(c["domains"] >= 10 for c in cats)
    reg = (await client.get("/api/v1/ideation/registry", params={"district": "madurai"})).json()
    assert reg[0]["district_fit"]["madurai"] == 3
    card = (await client.get("/api/v1/ideation/registry/jasmine_postharvest")).json()
    assert card["schemes"] and card["regulatory_items"]
    hyb = (
        await client.get("/api/v1/ideation/hybrids", params={"domain": "knitwear_small_batch"})
    ).json()
    assert hyb and all(h["anchor"]["id"] == "knitwear_small_batch" for h in hyb)
    assert (await client.get("/api/v1/ideation/registry/nothing")).status_code == 404
    bad = await client.get("/api/v1/ideation/registry", params={"district": "salem"})
    assert bad.status_code == 422


async def test_plan_accepts_a_registry_domain(client: AsyncClient):
    r = await client.post(
        "/api/v1/ideation/plan",
        json={"domain": "phc_diagnostics", "slots": {"stage": "idea", "district": "Chennai"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["domain_card"]["id"] == "phc_diagnostics"
    assert body["risks_by_phase"]["MVP"]
    assert all("risks" in m for m in body["roadmap"]["milestones"])


async def test_scan_endpoint_validates_and_returns_the_report(client: AsyncClient, monkeypatch):
    from app.routers import ideation

    async def fake_scan(text, *, elements=None, queries=None):
        return {"idea": text, "elements": elements, "queries": queries, "coverage": []}

    monkeypatch.setattr(ideation, "scan", fake_scan)
    r = await client.post(
        "/api/v1/ideation/scan",
        json={"text": "EEG communication for paralysed patients", "elements": ["EEG yes/no"]},
    )
    assert r.status_code == 200 and r.json()["elements"] == ["EEG yes/no"]
    assert (await client.post("/api/v1/ideation/scan", json={"text": "short"})).status_code == 422


async def test_agent_session_lifecycle(client: AsyncClient, monkeypatch):
    from app.agents import store
    from app.core.config import get_settings
    from app.research import scan as research

    real_scan = research.scan

    async def private_scan(text, *, elements=None, queries=None, client=None, private=False):
        return await real_scan(text, client=client, private=True)  # no network in tests

    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")
    monkeypatch.setattr(research, "scan", private_scan)
    store.set_store(store.MemoryStore())
    try:
        r = await client.post("/api/v1/ideation/agent/sessions", json={"name": "Kavya"})
        assert r.status_code == 200 and "Kavya" in r.json()["reply"]
        sid = r.json()["session_id"]
        base = f"/api/v1/ideation/agent/sessions/{sid}"

        r = await client.post(f"{base}/turns", json={"text": "a nurse alert device"})
        assert r.status_code == 200 and r.json()["action"]["kind"] == "ask"
        asked = r.json()["action"]["question"]

        # resumes at the same question, from the saved session
        snap = (await client.get(base)).json()
        assert snap["last_question"] == asked and snap["transcript"]

        # streamed turn: ack first, done last, sentences between
        async with client.stream("POST", f"{base}/turns/stream", json={"text": "Chennai"}) as s:
            body = "".join([c async for c in s.aiter_text()])
        kinds = [ln[7:] for ln in body.splitlines() if ln.startswith("event: ")]
        assert kinds[0] == "ack" and kinds[-1] == "done" and "sentence" in kinds
        assert (await client.get(base)).json()["known"]["district"] == "chennai"

        assert (await client.delete(base)).status_code == 204
        assert (await client.get(base)).status_code == 404
        bad = await client.post("/api/v1/ideation/agent/sessions/nope/turns", json={"text": "x"})
        assert bad.status_code == 422
    finally:
        store.set_store(None)
