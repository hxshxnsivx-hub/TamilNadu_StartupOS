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
    assert cov["patents"]["status"] == "no_key" and "EPO_OPS_KEY" in cov["patents"]["note"]
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
    assert {f["name"] for f in r["associated_domains"]["fields"]} == set(fields_from_terms(BCI))
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
    remote = [c for c in r["coverage"] if c["source"] != "local startups"]
    assert {c["status"] for c in remote} <= {"private", "skipped"}
    assert r["local"]["status"] == "ok"  # Vanigam's own data is still used


def test_nothing_safe_to_send_is_reported_not_searched():
    calls: list = []
    r = _run("KopraKing by Ravi from Pollachi", calls)
    cov = {c["source"]: c for c in r["coverage"]}
    assert cov["papers"]["status"] == "skipped" and "safe" in cov["papers"]["note"]
    assert not any("kopraking" in c.lower() for c in calls)


# ---- 1.2.1: relevance faults from the quality set ------------------------------------

BANANA = (
    "I want to start a banana chips and banana flour unit in Tiruchirappalli using B-grade"
    " fruit from Thottiyam farmers"
)
YARN = (
    "a yarn price marketplace app where small knitting units in Tiruppur buy from spinning"
    " mills on credit"
)
EMI = "instalment plans for medical treatment offered at hospital billing desks in Chennai"


def _engineering_handler(calls: list):
    """Papers on banana chips whose topics also touch Engineering and Medicine."""
    works = [
        _work("Banana chips frying", "Agricultural and Biological Sciences", "Food", "Frying"),
        _work("Dryer design", "Engineering", "Mechanical Engineering", "Drying equipment"),
        _work("Banana flour and gut health", "Medicine", "Nutrition", "Dietary fibre"),
    ]

    def handle(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        if req.url.host == "api.openalex.org":
            return httpx.Response(200, json={"meta": {"count": 90}, "results": works})
        if req.url.host == "api.github.com":
            return httpx.Response(200, json={"total_count": 0, "items": []})
        return httpx.Response(404)

    return handle


def _scan_with(text, handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def go():
        try:
            return await scan(text, client=client)
        finally:
            await client.aclose()

    return asyncio.run(go())


def test_discussion_points_come_from_the_matched_domain():
    """1.2.1.1: a banana-chips unit hears about its buyers and licences, not about
    sensors and hardware, though its papers touch Engineering."""
    r = _scan_with(BANANA, _engineering_handler([]))
    assert r["matched_domain"] == "banana_value_added"
    fields = [d["field"] for d in r["discuss"]]
    assert fields[0] == "Banana value-added products"
    assert "FSSAI registration or licence" in " ".join(r["discuss"][0]["questions"])
    assert "Engineering" not in fields and "Medicine" not in fields
    assert "Agricultural and Biological Sciences" in fields


def test_the_clinical_gate_covers_categories_too():
    """R035: papers that touch Medicine do not make a food idea a health product."""
    r = _scan_with(BANANA, _engineering_handler([]))
    assert "health_bio" not in r["vanigam_categories"]
    assert "agriculture" in r["vanigam_categories"]
    health = _run(BCI, [])
    assert "health_bio" in health["vanigam_categories"]  # a health idea keeps it


def test_closest_paper_needs_real_overlap_with_the_query():
    """1.2.1.2: the search's first hit is named only when its title is close."""
    from app.research.scan import closest_paper

    query = "smallholder agriculture banana chips flour"
    off = {"title": "Solomon Islands Smallholder Agriculture Study", "year": 2006}
    on = {"title": "Ready-to-eat banana porridge flour", "year": 2024}
    assert closest_paper([off], query, BANANA) is None
    assert closest_paper([off, on], query, BANANA) is on
    assert closest_paper([], query, BANANA) is None
    r = _scan_with(BANANA, _engineering_handler([]))
    assert r["papers"]["closest"]["title"] == "Banana chips frying"


def test_local_startups_must_fit_the_sector_and_name_the_product():
    """1.2.1.3: fintech lenders are not yarn marketplaces, nor eye hospitals EMI lenders."""
    from app.research.scan import _local, matched_domain

    yarn = _local(YARN, matched_domain(YARN))
    names = " ".join(s["name"] for s in yarn["startups"])
    assert "BankBazaar" not in names and "Kaleidofin" not in names and "Yubi" not in names
    assert "textiles" in yarn["sectors"] and "fintech" not in yarn["sectors"]
    emi = _local(EMI, matched_domain(EMI))
    assert not any("Agarwal" in s["name"] or "Wabag" in s["name"] for s in emi["startups"])
    assert emi["sectors"] == ["fintech"]


def test_short_product_words_match_local_startups():
    """Three-letter anchors ('oil', 'tea', 'eeg') count in startup descriptions too."""
    from app.research.scan import _local, matched_domain

    vco = "virgin coconut oil and desiccated coconut unit in Pollachi buying nuts from farmers"
    found = _local(vco, matched_domain(vco))
    assert "Anaimalais Coco" in [s["name"] for s in found["startups"]]


def test_function_words_are_never_product_anchors():
    """'cannot speak' becomes 'augmentative and alternative communication'; 'and' must
    not match nearly every startup description."""
    from app.research.scan import _anchors, _local, matched_domain
    from app.research.terms import LEXICON

    for text in (
        "communication aid for patients who cannot speak, using a tablet and sensors",
        "app for children who cannot speak to learn with parents and teachers",
    ):
        assert "and" not in _anchors(text)
        found = _local(text, matched_domain(text))
        assert found["startups"] == [], [s["name"] for s in found["startups"]]
    short = {w for phrase in LEXICON for w in _anchors(phrase) if len(w) == 3}
    assert short <= {"dry", "eeg", "eye", "ion", "oil", "tea"}, short


def test_local_lookup_reports_its_scope():
    """R023: what was searched is stated, in the result and in coverage."""
    from app.research import scan as scan_mod

    ok = scan_mod._local(BANANA, scan_mod.matched_domain(BANANA))
    assert ok["status"] == "ok" and ok["searched"] > 0
    assert ok["scope"].startswith(f"the {ok['searched']:,} startups on the Tamil Nadu Startup Map")
    assert "Chennai" in ok["scope"]
    r = _scan_with(BANANA, _engineering_handler([]))
    row = next(c for c in r["coverage"] if c["source"] == "local startups")
    assert row["status"] == "ok" and row["note"] == f"Only {ok['scope']}"


def test_a_broken_local_lookup_is_reported_as_an_error(monkeypatch):
    from app.ecosystem import index
    from app.research import scan as scan_mod

    def boom():
        raise OSError("disk")

    monkeypatch.setattr(index, "get_ecosystem", boom)
    out = scan_mod._local(BANANA)
    assert out["status"] == "error" and out["startups"] == [] and "scope" not in out


def test_one_unreachable_source_does_not_fail_the_scan():
    """R045: a timeout on GitHub leaves papers and the rest standing."""
    calls: list = []
    good = _handler(calls)

    def handle(req: httpx.Request) -> httpx.Response:
        if req.url.host == "api.github.com":
            raise httpx.ReadTimeout("slow", request=req)
        return good(req)

    r = _scan_with(BCI, handle)
    cov = {c["source"]: c for c in r["coverage"]}
    assert cov["projects"]["status"] == "error" and "reached" in cov["projects"]["note"]
    assert cov["papers"]["status"] == "ok" and r["papers"]["total"] == 12000


def test_a_network_error_is_not_cached(tmp_path):
    from app.research import sources

    cache = sources.Cache(tmp_path / "c", 7)
    attempts: list = []

    def handle(req: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx.ConnectError("refused", request=req)
        return httpx.Response(200, json={"meta": {"count": 5}})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:
            first = await sources.paper_count(c, "banana", cache)
            second = await sources.paper_count(c, "banana", cache)
        return first, second

    first, second = asyncio.run(go())
    assert first.status == "error" and second.status == "ok" and second.total == 5


def test_registry_filler_takes_no_query_slot():
    """R093: 'small', 'local', 'village', 'building' are prose, not search terms."""
    from app.research.terms import filler

    common = filler()
    assert {"small", "local", "building", "village"} <= common
    assert not {"banana", "yarn", "coconut", "solar", "farmers"} & common
    q = build_queries("I want to start a small business making banana chips for local shops")
    assert q["papers"] == "banana chips"
    assert "village" not in build_queries("solar dryer for copra farmers in my village")["papers"]
    assert "building" not in build_queries("I am building an app for dried fish")["papers"]


def test_hyphen_and_space_find_the_same_lexicon_entry():
    """1.2.1.5: 'dry-run' and 'dry run', 't-shirt' and 't shirt' are one entry."""
    for text in ("a dry-run starter", "a dry run starter"):
        assert "pump dry running protection" in build_queries(text)["papers"]
    for text in ("printed t-shirt brand", "printed t shirt brand"):
        assert build_queries(text)["papers"].startswith("knitted apparel")
