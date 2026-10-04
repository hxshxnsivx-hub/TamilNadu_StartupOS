"""API tests for the startup-ecosystem endpoints, on the built pilot index."""

from __future__ import annotations

from httpx import AsyncClient


async def test_zones_split_each_district(client: AsyncClient):
    for district in ("chennai", "coimbatore", "madurai"):
        r = await client.get("/api/v1/ecosystem/zones", params={"district": district})
        assert r.status_code == 200
        body = r.json()
        assert len(body["zones"]) >= 2, district
        assert body["hot_pins"] < body["pins_total"]
        assert all(z["peak_z"] >= 1.645 for z in body["zones"])
        assert "Gi*" in body["method"]


async def test_zones_reject_unknown_district(client: AsyncClient):
    r = await client.get("/api/v1/ecosystem/zones", params={"district": "salem"})
    assert r.status_code == 422


async def test_investor_list_hides_non_startup_funds_by_default(client: AsyncClient):
    founders = (await client.get("/api/v1/ecosystem/investors")).json()
    everyone = (await client.get("/api/v1/ecosystem/investors?founders_only=false")).json()
    assert all(i["serves_founders"] for i in founders)
    assert len(everyone) > len(founders)


async def test_edtech_founder_gets_thesis_investor_first_and_reasons_for_the_rest(
    client: AsyncClient,
):
    r = await client.post(
        "/api/v1/ecosystem/match",
        json={
            "sectors": ["edtech"],
            "stage": "seed",
            "district": "chennai",
            "pin": "600004",
            "ask_lakh": 150,
        },
    )
    assert r.status_code == 200
    body = r.json()
    top = body["investors"][0]
    assert "edtech" in top["investor"]["sectors"]
    assert top["signals"]["sector"] == 1.0
    assert all(x["reasons"] for x in body["refused"])
    assert body["zone"]["zone"]["district"] == "chennai"
    assert body["company_counts"]["district_same_sector"] > 0
    assert {p["id"] for p in body["platforms"]} >= {"tanfund", "investor_connect"}


async def test_match_rejects_unknown_sector(client: AsyncClient):
    r = await client.post(
        "/api/v1/ecosystem/match",
        json={"sectors": ["crypto"], "stage": "seed", "district": "madurai"},
    )
    assert r.status_code == 422


async def test_incubators_listed_by_district_and_sector(client: AsyncClient):
    r = await client.get("/api/v1/ecosystem/incubators", params={"district": "madurai"})
    assert r.status_code == 200
    names = {i["name"] for i in r.json()}
    assert any("MABIF" in n for n in names) and any("TCE" in n for n in names)
    agri = await client.get("/api/v1/ecosystem/incubators", params={"sector": "agritech"})
    assert all("agritech" in i["sectors"] or "general" in i["sectors"] for i in agri.json())
    bad = await client.get("/api/v1/ecosystem/incubators", params={"sector": "crypto"})
    assert bad.status_code == 422


async def test_match_includes_incubators_with_programmes(client: AsyncClient):
    r = await client.post(
        "/api/v1/ecosystem/match",
        json={
            "sectors": ["healthtech"],
            "stage": "seed",
            "district": "chennai",
            "pin": "600020",
            "dpiit": True,
            "company_age_years": 1,
        },
    )
    assert r.status_code == 200
    body = r.json()
    top = body["incubators"][0]
    assert "healthtech" in top["incubator"]["sectors"]
    assert any(p["name"] == "BioNEST" and p["applies"] == "yes" for p in top["programmes"])
    assert top["travel"]["basis"] == "estimate"
    assert all(x["reasons"] for x in body["incubators_refused"])
    late = await client.post(
        "/api/v1/ecosystem/match",
        json={"sectors": ["saas"], "stage": "series_a", "district": "chennai"},
    )
    assert late.json()["incubators"] == []
