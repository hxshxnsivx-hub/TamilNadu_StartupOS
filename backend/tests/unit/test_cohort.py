"""Cohorts: reference (similar TN startups and companies) and programme (aggregates)."""

from __future__ import annotations

import asyncio

from app.agents import ideation as agent
from app.agents.store import MemoryStore, set_store
from app.cohort.programme import MIN_GROUP, SMALL, programme_cohort
from app.cohort.reference import reference_cohort, similar_startups
from httpx import AsyncClient

EV = "electric vehicle charging stations for apartments"


def test_reference_finds_similar_startups_with_the_founders_words():
    rows = similar_startups(EV, "mobility", limit=5)
    assert rows and all(len(r["shared_words"]) >= 1 for r in rows)
    assert "charging" in rows[0]["shared_words"]  # the founder's word, not a stem
    assert all(r["source"].startswith("https://tamilnadustartupmap.com") for r in rows)


def test_reference_names_the_district_gap_and_the_sector():
    r = reference_cohort(EV, "mobility", "madurai")
    text = " ".join(r["observations"])
    assert "None of them is in Madurai" in text
    assert r["sector_companies"]["total"] > 0 and "registered companies in mobility" in text
    assert "not proof" in r["coverage"]


def test_reference_says_when_nothing_is_found():
    r = reference_cohort("zzqx frobnicate quuxly widgets for nobody", None, None)
    assert r["similar_startups"] == []
    assert r["observations"] == ["No similar startup found on the Tamil Nadu Startup Map."]


def _session(consent: bool, district: str, sector: str = "agri"):
    s, _ = agent.new_session("Founder", share_with_programme=consent)
    s.elicitation.put("district", district, 0.9, _src())
    s.elicitation.put("sector", sector, 0.9, _src())
    return s


def _src():
    from app.elicitation.session import Source

    return Source.ANSWER


def test_programme_shows_nothing_below_five_sharing_founders():
    sessions = [_session(True, "madurai") for _ in range(MIN_GROUP - 1)]
    sessions += [_session(False, "madurai") for _ in range(10)]
    r = programme_cohort(sessions)
    assert r["shown"] is False and r["founders_sharing"] == MIN_GROUP - 1
    assert "where_they_are" not in r


def test_programme_aggregates_fold_small_groups_and_hold_no_text():
    sessions = [_session(True, "madurai") for _ in range(6)]
    sessions += [_session(True, "chennai") for _ in range(2)]
    sessions += [_session(False, "coimbatore") for _ in range(9)]  # not shared: not counted
    r = programme_cohort(sessions)
    assert r["shown"] and r["founders_sharing"] == 8
    assert r["where_they_are"]["district"] == {"madurai": 6, SMALL: 2}
    assert "coimbatore" not in str(r)
    assert "Founder" not in str(r)  # no names
    assert r["not_worked_out_yet"]  # what they have not answered yet, as counts


async def test_cohort_endpoints(client: AsyncClient):
    r = await client.post(
        "/api/v1/cohort/reference", json={"idea": EV, "sector": "mobility", "district": "madurai"}
    )
    assert r.status_code == 200 and r.json()["similar_startups"]

    store = MemoryStore()
    set_store(store)
    try:
        ids = []
        for _ in range(5):
            s = _session(True, "madurai")
            await store.create(s)
            ids.append(s.id)
        r = await client.post("/api/v1/cohort/programme", json={"session_ids": ids + ["missing"]})
        body = r.json()
        assert body["shown"] and body["sessions_found"] == 5
        assert body["where_they_are"]["district"] == {"madurai": 5}
    finally:
        set_store(None)


def test_consent_survives_saving():
    store = MemoryStore()
    s = _session(True, "chennai")
    asyncio.run(store.create(s))
    assert asyncio.run(store.get(s.id)).cohort_consent is True
