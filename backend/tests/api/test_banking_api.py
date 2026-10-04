"""API tests for the bank loan routing endpoints (stateless, no DB)."""

from __future__ import annotations

from httpx import AsyncClient


async def test_branches_near_pin(client: AsyncClient):
    r = await client.get("/api/v1/banking/branches", params={"pin": "641201", "radius_km": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["located"] is True
    assert body["count"] > 20
    nearest = body["branches"][0]
    assert nearest["km"] == 0
    assert nearest["pin"] == "641201"
    assert body["by_type"]["public"] > 0
    # Coimbatore has precomputed road times; the list is ordered by them.
    timed = [b for b in body["branches"] if b["travel_basis"] == "road_network"]
    assert len(timed) == body["count"]
    minutes = [b["travel_min"] for b in body["branches"]]
    assert minutes == sorted(minutes)
    assert all(b["road_km"] >= b["km"] - 0.6 for b in timed)


async def test_branches_rejects_bad_pin(client: AsyncClient):
    r = await client.get("/api/v1/banking/branches", params={"pin": "12345"})
    assert r.status_code == 422


async def test_match_returns_rail_loans_guarantees_and_reasons(client: AsyncClient):
    r = await client.post(
        "/api/v1/banking/match",
        json={
            "amount_lakh": 40,
            "purpose": "wc",
            "years_in_business": 2,
            "gst_registered": True,
            "gst_months": 18,
            "women_owned": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["rail"]["primary"] == "online"
    ids = {s["id"] for s in body["loans"]}
    assert "canara_mv" in ids and "bob_ms" in ids
    assert {g["id"] for g in body["guarantees"]} >= {"cgtmse"}
    assert all(x["reasons"] for x in body["rejected"])


async def test_allocate_for_pin(client: AsyncClient):
    r = await client.post(
        "/api/v1/banking/allocate",
        json={
            "need": {"amount_lakh": 15, "purpose": "tl", "qualifies_for_subsidy": True},
            "pin": "641201",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["pin_located"] is True
    assert body["rail"]["primary"] == "branch_scheme"
    assert body["rail"]["collateral_route"] == "none_by_rbi_rule"
    assert 1 <= len(body["options"]) <= 5
    assert body["options"][0]["branch"] is not None
    assert body["signals_missing"] == ["track_record", "speed"]
