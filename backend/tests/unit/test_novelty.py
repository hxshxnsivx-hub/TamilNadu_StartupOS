"""The novelty check: element, combination and context maps, statement and levers."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from app.core.config import get_settings
from app.research import novelty

IDEA = "communication for physically challenged patients through brain waves for medication"

# papers per query, keyed by the words that identify it
COUNTS = {
    "EEG": 760191,
    "motor disability": 52000,
    "medication management": 73864,
}


def _count(q: str, india: bool) -> int:
    parts = [n for k, n in COUNTS.items() if k in q]
    if len(parts) == 1:
        return parts[0]
    if "EEG" in q and "medication management" in q and "motor disability" not in q:
        return 52 if india else 1118
    if "EEG" in q and "motor disability" in q:
        return 9 if india else 15  # a rare pair
    return 40 if india else 4000


@pytest.fixture(autouse=True)
def _settings(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "research_cache_dir", str(tmp_path / "cache"))
    monkeypatch.setattr(get_settings(), "openalex_api_key", "")


def _run(status=200, **kw):
    seen: list = []

    def handle(req: httpx.Request) -> httpx.Response:
        params = dict(req.url.params)
        seen.append(params)
        if status != 200:
            return httpx.Response(status, text="Rate limit exceeded")
        india = "country_code:IN" in params.get("filter", "")
        return httpx.Response(200, json={"meta": {"count": _count(params["search"], india)}})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:
            return await novelty.check(IDEA, client=c, **kw)

    return asyncio.run(go()), seen


def test_parts_come_from_the_lexicon_and_pairs_find_the_rare_combination():
    r, seen = _run()
    names = [e["element"] for e in r["elements"]]
    assert names == ["physically challenged", "brain waves", "medication"]
    assert r["elements"][1]["query"] == '(EEG OR "brain-computer interface")'
    rare = [p for p in r["pairs"] if p["gap"]]
    assert [(p["a"], p["b"]) for p in rare] == [("physically challenged", "brain waves")]
    assert r["statement"]["type"] == "combination"
    assert "Together, I found only 15" in r["statement"]["text"]
    assert r["levers"][0]["kind"] == "combine" and "15" in r["levers"][0]["because"]


def test_a_large_pair_is_not_called_rare_just_for_a_small_share():
    r, _ = _run()
    brain_med = next(p for p in r["pairs"] if {p["a"], p["b"]} == {"brain waves", "medication"})
    assert brain_med["papers"] == 1118 and brain_med["share_pct"] < 2 and not brain_med["gap"]


def test_context_gap_uses_india_affiliated_papers():
    r, seen = _run()
    assert any("country_code:IN" in p.get("filter", "") for p in seen)
    c = r["context"]
    assert c["india_share_pct"] < 5 and c["tn_startups"] == 0 and c["gap"]
    assert any(lv["kind"] == "localise" for lv in r["levers"])


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
