"""The front door's two answers reach the conversation and the journey (tasks
1.1.5.1 plumbing, 1.1.6; R121): one vocabulary, one mapping, typed at the API."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from app.agents import ideation as agent
from app.agents import store
from app.core.stages import Stage
from app.elicitation import engine
from app.elicitation.entry import CONVERSATION_MODE, REGISTRATION, journey_facts
from app.elicitation.session import Source
from app.elicitation.slots import Band, EntryMode
from app.journey.engine import journey
from app.models.enums import EntryMode as Door
from app.models.enums import RegSubtype
from httpx import AsyncClient

JOURNEY_STORE = Path(__file__).resolve().parents[3] / "frontend" / "src" / "journeyStore.ts"
URL = "/api/v1/ideation/agent/sessions"


def _union(name: str) -> set[str]:
    src = JOURNEY_STORE.read_text(encoding="utf8")
    body = re.search(rf"export type {name} =([^;]+);", src)
    assert body, name
    return set(re.findall(r'"([a-z_]+)"', body.group(1)))


@pytest.mark.skipif(not JOURNEY_STORE.exists(), reason="frontend not checked out")
def test_backend_values_match_what_the_browser_stores():
    """R121: the browser stores 'registered_with_product'; the backend once said
    'registered_product', so the subtype would have been refused or lost."""
    assert _union("RegSubtype") == {r.value for r in RegSubtype}
    assert _union("EntryMode") == {d.value for d in Door}


def test_every_value_has_one_reading():
    assert set(REGISTRATION) == set(RegSubtype)
    assert set(CONVERSATION_MODE) == set(Door)
    assert CONVERSATION_MODE[Door.IDEA] is EntryMode.IDEA
    assert CONVERSATION_MODE[Door.DOMAIN_ONLY] is EntryMode.EXPERIENCE
    assert CONVERSATION_MODE[Door.INTENT_ONLY] is EntryMode.EXPERIENCE


def test_journey_facts_follow_the_subtype():
    assert journey_facts(None) == {}
    assert journey_facts(RegSubtype.UNREGISTERED) == {"registered": False, "entity": "none"}
    assert journey_facts(RegSubtype.IDEA_WORKER_NO_COMPANY) == {
        "registered": False,
        "entity": "none",
    }
    # registered, but the subtype does not say which structure: entity is still asked
    assert journey_facts(RegSubtype.REGISTERED_WITH_PRODUCT) == {"registered": True}
    assert journey_facts(RegSubtype.REGISTERED_NO_PRODUCT) == {"registered": True}


def test_the_journey_does_not_ask_what_the_subtype_says():
    asked = {q["fact"] for q in journey({})["questions"]}
    assert {"entity", "registered"} & asked  # without it, they are asked
    j = journey({}, reg_subtype="unregistered")
    asked = {q["fact"] for q in j["questions"]}
    assert not {"entity", "registered"} & asked
    # a fact the founder gave outranks the subtype's reading
    s = {r["id"]: r for r in journey({"entity": "pvt_ltd"}, reg_subtype="unregistered")["steps"]}
    assert s["incorporate"]["status"] == "required"


def test_a_registered_product_puts_a_stage_floor_said_back_as_assumed():
    s = engine.start("u", stage_floor=Stage.MVP)
    sv = s.slots["stage"]
    assert sv.value == "mvp" and sv.source is Source.DEFAULT
    assert s.band("stage") is Band.CONFIRM  # not asked, confirmed at the restatement
    assert "stage" in s.filled


def test_the_floor_never_lowers_a_profile_stage():
    s = engine.start("u", profile={"stage": "revenue"}, stage_floor=Stage.MVP)
    assert s.slots["stage"].value == "revenue"
    assert s.slots["stage"].source is Source.PROFILE


def test_a_profile_stage_below_the_floor_is_confirmed_not_trusted():
    """The profile says 'idea' and the front door says a product sells: the two
    disagree, so the floor is said back for the founder to confirm."""
    s = engine.start("u", profile={"stage": "idea"}, stage_floor=Stage.MVP)
    assert s.slots["stage"].value == "mvp"
    assert s.band("stage") is Band.CONFIRM


def test_the_greeting_follows_the_subtype_and_survives_a_reload():
    s, greeting = agent.new_session(
        "Kavya", reg_subtype=RegSubtype.REGISTERED_WITH_PRODUCT, entry_mode=Door.IDEA
    )
    opening = REGISTRATION[RegSubtype.REGISTERED_WITH_PRODUCT].opening
    assert opening in greeting and agent.OPENING_QUESTION not in greeting
    assert s.pending["question"] == opening
    back = agent.AgentSession.from_dict(s.to_dict())
    assert back.reg_subtype == "registered_with_product" and back.entry_mode == "idea"
    # an old document with no pending record rebuilds the subtype's opening
    d = s.to_dict()
    del d["pending"]
    assert agent.AgentSession.from_dict(d).pending["question"] == opening
    _, plain = agent.new_session("Kavya")
    assert agent.OPENING_QUESTION in plain


def test_the_model_hears_the_registration():
    s, _ = agent.new_session("K", reg_subtype=RegSubtype.REGISTERED_NO_PRODUCT)
    assert REGISTRATION[RegSubtype.REGISTERED_NO_PRODUCT].said in agent._known(s)


def test_entry_mode_is_kept_and_picks_the_conversation():
    """1.1.5.1: a domain_only founder runs the experience conversation
    (tests/unit/test_experience.py covers it)."""
    s, _ = agent.new_session("K", entry_mode=Door.DOMAIN_ONLY)
    assert s.entry_mode == "domain_only"
    assert s.elicitation.mode is EntryMode.EXPERIENCE


async def test_api_takes_typed_subtype_and_mode_and_refuses_others(client: AsyncClient):
    store.set_store(store.MemoryStore())
    try:
        for bad in (
            {"reg_subtype": "registered_product"},  # the old backend spelling
            {"reg_subtype": "2A"},
            {"entry_mode": "experience"},  # the conversation's word, not the door's
            {"entry_mode": None, "facts": {"registered": True}},  # no free-form facts
        ):
            assert (await client.post(URL, json=bad)).status_code == 422, bad
        r = await client.post(
            URL,
            json={"name": "Kavya", "reg_subtype": "registered_with_product", "entry_mode": "idea"},
        )
        assert r.status_code == 200
        body = r.json()
        assert REGISTRATION[RegSubtype.REGISTERED_WITH_PRODUCT].opening in body["reply"]
        snap = (await client.get(f"{URL}/{body['session_id']}")).json()
        assert snap["reg_subtype"] == "registered_with_product"
        assert snap["entry_mode"] == "idea"
        assert snap["known"]["stage"] == "mvp"
    finally:
        store.set_store(None)


async def test_a_registered_founder_with_a_product_is_never_asked_the_stage(
    client: AsyncClient, monkeypatch
):
    """1.1.6: the subtype lived only in the browser, so the stage was asked again."""
    from app.core.config import get_settings
    from app.research import novelty
    from app.research import scan as research

    real_scan, real_novelty = research.scan, novelty.check

    async def private_scan(text, *, elements=None, queries=None, client=None, private=False):
        return await real_scan(text, client=client, private=True)

    async def private_novelty(idea, **kw):
        return await real_novelty(idea, **{**kw, "private": True})

    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")
    monkeypatch.setattr(research, "scan", private_scan)
    monkeypatch.setattr(novelty, "check", private_novelty)
    store.set_store(store.MemoryStore())
    try:
        r = await client.post(URL, json={"reg_subtype": "registered_with_product"})
        base = f"{URL}/{r.json()['session_id']}"
        asked: list[str] = []
        text = "We make naturally dyed cotton sarees and sell them to buyers in other states"
        for _ in range(8):
            act = (await client.post(f"{base}/turns", json={"text": text})).json()["action"]
            if act["kind"] != "ask":
                break
            asked.append(act["slot"])
            text = "yes"
        assert asked, "the conversation asked nothing, so the test proved nothing"
        assert "stage" not in asked
    finally:
        store.set_store(None)


async def test_journey_endpoint_takes_the_subtype(client: AsyncClient):
    r = await client.post("/api/v1/journey", json={"reg_subtype": "unregistered"})
    assert r.status_code == 200
    assert not {"entity", "registered"} & {q["fact"] for q in r.json()["questions"]}
    r = await client.post("/api/v1/journey", json={"reg_subtype": "registered_product"})
    assert r.status_code == 422
