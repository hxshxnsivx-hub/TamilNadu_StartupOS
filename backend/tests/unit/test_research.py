"""Unit tests for the prior-art scan, with a mock transport (no network)."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from app.core.config import get_settings
from app.research.scan import _label, associated_domains, scan
from app.research.terms import build_queries, fields_from_terms, is_health

BCI = (
    "developing a project for communication with physically challenged patients through the"
    " brain waves for change in medication"
)


def _work(title, field, subfield, topic, score=0.9, year=2023, cited=10):
    return {
        "id": f"https://openalex.org/{title}",
        "display_name": title,
        "publication_year": year,
        "cited_by_count": cited,
        "doi": None,
        "primary_location": {"source": {"display_name": "A Journal"}},
        "topics": [
            {
                "display_name": topic,
                "score": score,
                "subfield": {"display_name": subfield},
                "field": {"display_name": field},
                "domain": {"display_name": "Health Sciences"},
            }
        ],
    }


WORKS = [
    _work(
        "EEG speller", "Neuroscience", "Cognitive Neuroscience", "EEG and Brain-Computer Interfaces"
    ),
    _work(
        "P300 BCI", "Neuroscience", "Cognitive Neuroscience", "EEG and Brain-Computer Interfaces"
    ),
    _work("AAC for ALS", "Health Professions", "Speech and Hearing", "Augmentative communication"),
    _work("Deep EEG", "Computer Science", "Artificial Intelligence", "EEG classification", 0.5),
]


def _handler(calls: list, openalex_status: int = 200):
    def handle(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        host, params = req.url.host, dict(req.url.params)
        if host == "api.openalex.org":
            if openalex_status != 200:
                return httpx.Response(openalex_status, text="Rate limit exceeded")
            if "group_by" in params:
                return httpx.Response(
                    200,
                    json={"group_by": [{"key": "2022", "count": 40}, {"key": "2023", "count": 55}]},
                )
            q = params.get("search", "")
            total = 12000 if "medication" in q else 420
            return httpx.Response(200, json={"meta": {"count": total}, "results": WORKS})
        if host == "clinicaltrials.gov":
            study = {
                "protocolSection": {
                    "identificationModule": {
                        "nctId": "NCT00000001",
                        "briefTitle": "BCI speech trial",
                    },
                    "statusModule": {
                        "overallStatus": "RECRUITING",
                        "startDateStruct": {"date": "2023-10"},
                    },
                    "designModule": {"phases": ["NA"]},
                    "sponsorCollaboratorsModule": {"leadSponsor": {"name": "A Hospital"}},
                }
            }
            return httpx.Response(200, json={"totalCount": 23, "studies": [study]})
        if host == "api.github.com":
            repo = {
                "full_name": "lab/eeg-bci",
                "description": "Low-cost EEG BCI",
                "stargazers_count": 169,
                "pushed_at": "2025-01-01",
                "license": {"spdx_id": "MIT"},
                "html_url": "https://github.com/lab/eeg-bci",
            }
            return httpx.Response(200, json={"total_count": 702, "items": [repo]})
        return httpx.Response(404)

    return handle


@pytest.fixture(autouse=True)
def _settings(monkeypatch, tmp_path):
    s = get_settings()
    monkeypatch.setattr(s, "research_cache_dir", str(tmp_path / "cache"))
    monkeypatch.setattr(s, "patentsview_api_key", "")
    monkeypatch.setattr(s, "openalex_api_key", "")
    monkeypatch.setattr(s, "github_token", "")


def _run(text, calls, status=200, **kw):
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler(calls, status)))

    async def go():
        try:
            return await scan(text, client=client, **kw)
        finally:
            await client.aclose()

    return asyncio.run(go())


def test_everyday_words_become_precise_queries():
    q = build_queries(BCI)
    assert q["projects"] == "EEG brain-computer interface"
    assert q["papers"].startswith("EEG brain-computer interface medication management")
    el = build_queries("EEG signals to communicate yes or no for locked-in patients")
    assert "locked-in syndrome" in el["papers"] and "EEG" in el["papers"]
    assert is_health(BCI) and not is_health("solar dryer for coconut")


def test_domains_come_from_topic_evidence():
    d = associated_domains(WORKS_AS_PARSED())
    names = [f["name"] for f in d["fields"]]
    assert names[0] == "Neuroscience"  # two papers, highest weight
    assert set(names) == {"Neuroscience", "Health Professions", "Computer Science"}
    assert sum(f["share_pct"] for f in d["fields"]) in (99, 100, 101)


def WORKS_AS_PARSED():
    from app.research.sources import _work

    return [_work(w) for w in WORKS]


def test_scan_reports_every_source_honestly():
    calls: list = []
    r = _run(BCI, calls)
    cov = {c["source"]: c for c in r["coverage"]}
    assert cov["papers"]["status"] == "ok" and r["papers"]["total"] == 12000
    assert cov["trials"]["status"] == "ok" and r["trials"]["items"][0]["id"] == "NCT00000001"
    assert cov["projects"]["status"] == "ok" and r["projects"]["total"] == 702
    assert cov["patents"]["status"] == "no_key" and "PATENTSVIEW_API_KEY" in cov["patents"]["note"]
    assert r["associated_domains"]["basis"] == "papers"
    assert "health_bio" in r["vanigam_categories"] and "ai_ml" in r["vanigam_categories"]
    assert any(d["field"] == "Neuroscience" for d in r["discuss"])
    assert r["papers"]["by_year"] == {2022: 40, 2023: 55}


def test_non_health_ideas_skip_trials():
    r = _run("solar dryer for coconut copra in Pollachi", [])
    cov = {c["source"]: c for c in r["coverage"]}
    assert cov["trials"]["status"] == "skipped"


def test_spent_budget_is_reported_and_domains_fall_back_to_terms():
    r = _run(BCI, [], status=429)
    cov = {c["source"]: c for c in r["coverage"]}
    assert cov["papers"]["status"] == "budget_exhausted"
    assert r["associated_domains"]["basis"].startswith("terms")
    assert [f["name"] for f in r["associated_domains"]["fields"]] == fields_from_terms(BCI)
    assert r["elements"] == []


def test_elements_are_labelled_from_paper_evidence():
    r = _run(BCI, [], elements=["EEG yes/no for locked-in patients", "medication change request"])
    labels = {e["element"]: e["label"] for e in r["elements"]}
    assert labels["EEG yes/no for locked-in patients"] == "active"  # 420 papers
    assert labels["medication change request"] == "crowded"  # 12,000 papers
    assert _label(None, 900) == "not enough evidence (papers not searched)"
    assert _label(0, 0) == "nothing found"


def test_results_are_cached():
    calls: list = []
    _run(BCI, calls)
    first = len(calls)
    _run(BCI, calls)
    assert len(calls) == first  # second scan served from the cache


def test_agent_supplied_queries_replace_the_lexicon():
    calls: list = []
    _run(BCI, calls, queries={"projects": "P300 speller"})
    assert any("P300+speller" in c or "P300%20speller" in c for c in calls)


def test_scan_output_is_json_serialisable():
    json.dumps(_run(BCI, []))


def test_founder_words_never_leave_in_queries():
    """Names, brands and places stay on the platform; only public vocabulary goes out."""
    text = "solar dryer for coconut copra in Pollachi called KopraKing by Ravi"
    sent = " ".join(build_queries(text)[k] for k in ("papers", "trials", "projects", "patents"))
    for private_word in ("kopraking", "ravi", "pollachi"):
        assert private_word not in sent.lower()
    assert "photovoltaic" in sent


def test_model_written_queries_are_cleaned():
    from app.research.terms import scrub

    assert scrub("P300 speller nurse call KopraKing Chennai 2024", "KopraKing in Chennai") == (
        "P300 speller nurse call"
    )


def test_private_scan_calls_no_external_source():
    calls: list = []
    r = _run(BCI, calls, private=True)
    assert calls == []
    assert {c["status"] for c in r["coverage"]} <= {"private", "skipped"}


def test_nothing_safe_to_send_is_reported_not_searched():
    calls: list = []
    r = _run("KopraKing by Ravi from Pollachi", calls)
    cov = {c["source"]: c for c in r["coverage"]}
    assert cov["papers"]["status"] == "skipped" and "safe" in cov["papers"]["note"]
    assert not any("kopraking" in c.lower() for c in calls)
