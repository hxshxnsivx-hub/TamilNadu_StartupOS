"""The registered-startup journey: statuses, reasons, order and the domain's licences."""

from __future__ import annotations

import pytest
from app.journey.engine import journey, judge, library
from app.planner.packs import parse_rule
from httpx import AsyncClient

FOOD_COMPANY = {
    "entity": "pvt_ltd",
    "registered": False,
    "goods": True,
    "services": False,
    "turnover_lakh": 30,
    "sells_online": True,
    "innovative": True,
    "has_brand": True,
    "employees": 4,
    "exports": False,
}


def _by_id(j: dict) -> dict:
    return {s["id"]: s for s in j["steps"]}


def test_missing_facts_are_unknown_never_no():
    rule = parse_rule({"field": "registered", "op": "is_false"})
    assert judge(rule, {})[0] is None  # not "true because missing means False"
    j = _by_id(journey({}))
    assert j["udyam"]["status"] == "unknown"
    assert any(q["fact"] == "entity" for q in j["udyam"]["questions"])


def test_a_new_food_company_gets_the_right_steps_with_reasons():
    j = journey(FOOD_COMPANY, domain_id="banana_value_added")
    s = _by_id(j)
    assert s["incorporate"]["status"] == "required"
    assert s["incorporate"]["reason"] == "you chose a company or LLP; it is not registered yet"
    assert s["gst"]["status"] == "required"  # goods sold online
    assert s["dpiit"]["status"] == "required"  # registering now counts as 0 years
    assert s["esi"]["status"] == "not_needed" and "10 or more" in s["esi"]["reason"]
    assert s["lic:fssai"]["status"] == "required" and s["lic:fssai"]["link"]
    assert j["next"][0] == "incorporate"


def test_steps_come_after_their_prerequisites():
    order = [s["id"] for s in journey(FOOD_COMPANY)["steps"]]
    assert order.index("incorporate") < order.index("bank_account") < order.index("udyam")
    assert order.index("udyam") < order.index("startuptn")


def test_proprietorship_is_told_why_dpiit_does_not_apply():
    s = _by_id(journey({"entity": "proprietorship", "registered": True,
                        "years_since_incorporation": 2, "innovative": True,
                        "turnover_lakh": 10}))  # fmt: skip
    assert s["dpiit"]["status"] == "not_needed"
    assert "proprietorship does not qualify" in s["dpiit"]["reason"]


def test_small_service_business_gets_gst_as_recommended_not_required():
    s = _by_id(journey({"entity": "llp", "registered": True, "services": True,
                        "goods": False, "turnover_lakh": 12}))  # fmt: skip
    assert s["gst"]["status"] == "recommended" and "optional" in s["gst"]["reason"]


def test_done_steps_unblock_the_next_ones():
    j = journey({**FOOD_COMPANY}, done=["incorporate", "bank_account"])
    s = _by_id(j)
    assert s["incorporate"]["status"] == "done"
    assert s["udyam"]["waiting_on"] == [] and "udyam" in j["next"]


def test_skipped_prerequisites_do_not_block():
    s = _by_id(journey({"entity": "proprietorship", "registered": True}))
    assert "incorporate" not in s["bank_account"]["depends_on"]  # it does not apply


def test_every_step_has_a_link_and_a_known_phase():
    phases = library()["_meta"]["phases"]
    for raw in library()["steps"]:
        assert raw["link"].startswith("https://") and raw["phase"] in phases


@pytest.mark.parametrize("domain,status", [("banana_value_added", 200), ("spaceships", 404)])
async def test_journey_endpoint(client: AsyncClient, domain, status):
    r = await client.post(
        "/api/v1/journey", json={"facts": {"entity": "none"}, "domain_id": domain}
    )
    assert r.status_code == status
    if status == 200:
        assert r.json()["steps"][0]["id"] == "choose_entity"
        assert r.json()["steps"][0]["status"] == "required"
