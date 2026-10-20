"""The novelty check: element, combination and context maps, statement and levers."""

from __future__ import annotations

import asyncio
import tempfile

import httpx
import pytest
from app.core.config import get_settings
from app.research import novelty

IDEA = "communication for physically challenged patients through brain waves for medication"
NURSE = "brain waves to send a nurse call for medication"
SCOPE = "the 654 startups on the Tamil Nadu Startup Map in Chennai, Coimbatore and Madurai"
LOCAL_NONE = {"local": {"status": "ok", "scope": SCOPE, "startups": []}}

# papers per query, keyed by the words that identify it
COUNTS = {
    "EEG": 760191,
    "nurse call system": 5200,
    "medication management": 73864,
}


def _count(q: str, india: bool) -> int:
    parts = [n for k, n in COUNTS.items() if k in q]
    if len(parts) == 1:
        return parts[0]
    if "EEG" in q and "medication management" in q and "nurse call system" not in q:
        return 52 if india else 1118
    if "EEG" in q and "nurse call system" in q:
        return 9 if india else 15  # a rare pair
    return 40 if india else 4000


@pytest.fixture(autouse=True)
def _settings(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "research_cache_dir", str(tmp_path / "cache"))
    monkeypatch.setattr(get_settings(), "openalex_api_key", "")


def _run(status=200, idea=IDEA, count=_count, fail=lambda q: False, **kw):
    seen: list = []
    get_settings().research_cache_dir = tempfile.mkdtemp()  # each run counts afresh

    def handle(req: httpx.Request) -> httpx.Response:
        params = dict(req.url.params)
        seen.append(params)
        if status != 200:
            return httpx.Response(status, text="Rate limit exceeded")
        if fail(params["search"]):
            return httpx.Response(503, text="Unavailable")
        india = "country_code:IN" in params.get("filter", "")
        return httpx.Response(200, json={"meta": {"count": count(params["search"], india)}})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:
            return await novelty.check(idea, client=c, **kw)

    return asyncio.run(go()), seen


def test_pairs_find_the_rare_combination():
    r, _ = _run(idea=NURSE)
    names = [e["element"] for e in r["elements"]]
    assert names == ["brain waves", "nurse call", "medication"]
    assert r["elements"][0]["query"] == '(EEG OR "brain-computer interface")'
    rare = [p for p in r["pairs"] if p["gap"]]
    assert [(p["a"], p["b"]) for p in rare] == [("brain waves", "nurse call")]
    assert r["statement"]["type"] == "combination"
    assert "Together, I found only 15" in r["statement"]["text"]
    assert r["levers"][0]["kind"] == "combine" and "15" in r["levers"][0]["because"]


def test_who_is_served_and_broader_restatements_are_not_parts():
    """1.2.1.4: 'physically challenged' and 'farmers' name who is served (re-target covers
    them); 'solar' beside 'solar inverters' only restates a part more broadly."""
    assert [p["element"] for p in novelty._parts(IDEA, None)] == ["brain waves", "medication"]
    banana = "banana chips from B-grade fruit bought from Thottiyam farmers"
    assert [p["element"] for p in novelty._parts(banana, None)] == ["banana"]
    solar = "board-level repair of solar inverters for farm and rooftop solar owners"
    assert [p["element"] for p in novelty._parts(solar, None)] == ["solar inverters"]
    vco = "virgin coconut oil and desiccated coconut unit"
    assert [p["element"] for p in novelty._parts(vco, None)] == ["virgin coconut oil"]


def test_a_large_pair_is_not_called_rare_just_for_a_small_share():
    r, _ = _run()
    brain_med = next(p for p in r["pairs"] if {p["a"], p["b"]} == {"brain waves", "medication"})
    assert brain_med["papers"] == 1118 and brain_med["share_pct"] < 2 and not brain_med["gap"]


def test_context_gap_uses_india_affiliated_papers_and_says_what_was_searched():
    r, seen = _run(scan=LOCAL_NONE)
    assert any("country_code:IN" in p.get("filter", "") for p in seen)
    c = r["context"]
    assert c["india_share_pct"] < 5 and c["tn_startups"] == 0 and c["gap"]
    assert r["statement"]["type"] == "context"
    assert f"none of {SCOPE} does it" in r["statement"]["text"]
    localise = next(lv for lv in r["levers"] if lv["kind"] == "localise")
    assert SCOPE in localise["because"] and "no Tamil Nadu startup" not in localise["because"]


def test_a_failed_local_lookup_is_no_context_gap():
    """R023: a lookup that failed, or a scan without its scope, says nothing about
    Tamil Nadu startups."""
    for scan in (None, {"local": {"status": "error", "startups": []}}, {"local": {"startups": []}}):
        r, _ = _run(scan=scan)
        assert r["context"]["tn_startups"] is None and not r["context"]["gap"]
        assert r["statement"]["type"] != "context"
        assert all(lv["kind"] != "localise" for lv in r["levers"])


def test_every_lever_names_its_reason():
    r, _ = _run(
        scan={"associated_domains": {"fields": [{"name": "Medicine"}]}, "trials": {"total": 23}}
    )
    assert r["levers"] and all(lv["because"] for lv in r["levers"])
    assert any(lv["kind"] == "regulatory route" for lv in r["levers"])


def test_private_and_budget_exhausted_are_unclear_not_novel():
    r, seen = _run(private=True)
    assert seen == [] and r["statement"]["type"] == "unclear" and r["levers"] == []
    r, _ = _run(status=429)
    assert r["statement"]["type"] == "unclear" and r["status"] == "budget_exhausted"


def test_the_founders_own_parts_are_searched_safely():
    r, seen = _run(elements=["brain waves to say yes or no", "KopraKing pager"])
    queries = " ".join(p["search"] for p in seen)
    assert "KopraKing" not in queries and "kopraking" not in queries.lower()


def test_crowded_needs_every_combination_counted():
    """R030: when the budget runs out on the pairs, or only one part can be searched,
    the idea is not called crowded and no business-model lever is offered."""
    r, _ = _run(fail=lambda q: "EEG" in q and "medication management" in q)
    assert r["pairs"] == [] and r["coverage"] == {"pairs_expected": 1, "pairs_counted": 0}
    assert r["statement"]["type"] == "unclear" and "every combination" in r["statement"]["text"]
    assert all(lv["kind"] != "business model" for lv in r["levers"])

    one, _ = _run(idea="banana chips for school children", count=lambda q, india: 800)
    assert [e["element"] for e in one["elements"]] == ["banana"]
    assert one["statement"]["type"] == "unclear" and "only one part" in one["statement"]["text"]
    assert all(lv["kind"] != "business model" for lv in one["levers"])


def test_crowded_and_active_are_told_apart():
    r, _ = _run()  # both parts above 5,000 papers and their pair counted
    assert r["statement"]["type"] == "crowded"
    assert any(lv["kind"] == "business model" for lv in r["levers"])
    active, _ = _run(count=lambda q, india: 40 if india else 2000)
    assert active["statement"]["type"] == "active"
    assert all(lv["kind"] != "business model" for lv in active["levers"])


def test_a_zero_on_one_name_is_not_searched_well():
    """1.2.1.5: 'dry-run' and 'dry run' are one part, and a single phrase with no paper
    at all is a name research does not use, not a gap."""
    idea = "a dry-run protection starter for farm pump motors"
    parts = novelty._parts(idea, None)
    assert [p["element"] for p in parts] == ["pump motors", "dry run"]
    assert [p["element"] for p in novelty._parts(idea.replace("dry-run", "dry run"), None)] == [
        "pump motors",
        "dry run",
    ]

    def count(q, india):
        return 0 if "dry running" in q else (20 if india else 581)

    r, _ = _run(idea=idea, count=count)
    labels = {e["element"]: e["label"] for e in r["elements"]}
    assert labels == {"pump motors": "active", "dry run": "not searched well"}
    assert "no papers" not in r["statement"]["text"] and r["pairs"] == []
    assert r["statement"]["type"] == "unclear"


def test_an_idea_with_no_known_part_says_why_it_is_unclear():
    """1.2.1.6: the medical-EMI idea has no lexicon term, so no part can be searched; the
    statement says that, rather than nothing."""
    r, seen = _run(idea="instalment plans for medical treatment offered at hospital billing desks")
    assert seen == [] and r["statement"]["type"] == "unclear"
    assert "none of its words are in the vocabulary" in r["statement"]["text"]
    assert "can't judge novelty yet" in r["statement"]["text"]
