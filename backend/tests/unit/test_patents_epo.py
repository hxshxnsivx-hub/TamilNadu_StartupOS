"""EPO Open Patent Services: worldwide patents and the Indian filings among them."""

from __future__ import annotations

import asyncio
from urllib.parse import parse_qs

import httpx
import pytest
from app.agents.ideation import _fallback_reply
from app.core.config import get_settings
from app.research import sources


def _doc(country: str, number: str, title: str, applicant: str, date: str = "20210304") -> dict:
    """One exchange-document as OPS writes it in JSON."""
    return {
        "exchange-document": {
            "@country": country,
            "@doc-number": number,
            "@kind": "A1",
            "bibliographic-data": {
                "invention-title": [
                    {"@lang": "fr", "$": "Titre"},
                    {"@lang": "en", "$": title},
                ],
                "publication-reference": {
                    "document-id": [
                        {"@document-id-type": "docdb", "date": {"$": date}},
                    ]
                },
                "parties": {
                    "applicants": {
                        "applicant": [
                            {"@data-format": "docdb", "applicant-name": {"name": {"$": "UPPER"}}},
                            {
                                "@data-format": "original",
                                "applicant-name": {"name": {"$": applicant}},
                            },
                        ]
                    }
                },
            },
        }
    }


def _answer(total: int, docs: list[dict]) -> dict:
    return {
        "ops:world-patent-data": {
            "ops:biblio-search": {
                "@total-result-count": str(total),
                # one document comes as an object, several as a list
                "ops:search-result": {"exchange-documents": docs[0] if len(docs) == 1 else docs},
            }
        }
    }


@pytest.fixture
def epo(monkeypatch):
    st = get_settings()
    monkeypatch.setattr(st, "epo_ops_key", "k")
    monkeypatch.setattr(st, "epo_ops_secret", "s")
    monkeypatch.setattr(sources, "_epo_token", None)
    seen: list[httpx.Request] = []

    def handle(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if req.url.path.endswith("/accesstoken"):
            assert req.headers["authorization"].startswith("Basic ")
            return httpx.Response(200, json={"access_token": "tok", "expires_in": "1199"})
        assert req.headers["authorization"] == "Bearer tok"
        q = parse_qs(req.url.query.decode())["q"][0]
        if "pn=IN" in q:
            if "nothing" in q:
                return httpx.Response(404, text="<fault>SERVER.EntityNotFound</fault>")
            return httpx.Response(
                200, json=_answer(1, [_doc("IN", "202141001", "Pump dry run guard", "Ravi Motors")])
            )
        return httpx.Response(
            200,
            json=_answer(
                57,
                [
                    _doc("US", "2021123", "Dry run protection for pumps", "Acme Pumps Inc"),
                    _doc("IN", "202141001", "Pump dry run guard", "Ravi Motors"),
                ],
            ),
        )

    return seen, httpx.MockTransport(handle)


def _search(transport, query: str):
    async def go():
        async with httpx.AsyncClient(transport=transport) as c:
            return await sources.patents(c, query)

    return asyncio.run(go())


def test_worldwide_patents_and_the_indian_filings(epo):
    seen, transport = epo
    r = _search(transport, "pump dry run motor protection")
    assert r.status == "ok" and r.total == 57
    first = r.items[0]
    assert first["title"] == "Dry run protection for pumps"  # the English title, not the French
    assert first["id"] == "US2021123A1" and first["date"] == "2021-03-04"
    assert first["assignees"] == ["Acme Pumps Inc"]  # not the same name again in capitals
    assert "espacenet" in first["url"]
    assert r.extra["india"]["total"] == 1 and r.extra["india"]["items"][0]["country"] == "IN"
    queries = [parse_qs(q.url.query.decode())["q"][0] for q in seen if "search" in q.url.path]
    assert queries == ['ta all "pump dry run"', 'ta all "pump dry run" and pn=IN']
    assert "Indian filings included" in r.note


def test_no_indian_hits_is_none_found_not_an_error(epo):
    _, transport = epo
    r = _search(transport, "nothing matches here")
    assert r.status == "ok" and r.extra["india"] == {"total": 0, "items": []}


def test_the_token_is_reused_and_a_bad_key_is_reported(epo, monkeypatch):
    seen, transport = epo
    _search(transport, "pump dry run")
    _search(transport, "solar cold box")
    assert sum(1 for q in seen if q.url.path.endswith("/accesstoken")) == 1

    monkeypatch.setattr(sources, "_epo_token", None)
    refused = httpx.MockTransport(lambda req: httpx.Response(401, json={"error": "invalid_client"}))
    r = _search(refused, "pump dry run")
    assert r.status == "error" and "EPO_OPS_KEY" in r.note


def test_without_keys_patents_are_not_searched():
    r = _search(httpx.MockTransport(lambda req: httpx.Response(500)), "pump dry run")
    assert r.status == "no_key" and "EPO_OPS_KEY" in r.note


def test_the_mentor_says_how_many_were_filed_in_india():
    from tests.unit.test_ideation_agent import SCAN

    scan = {**SCAN, "patents": {"total": 57, "items": [], "india": {"total": 3, "items": []}}}
    assert "57 related patents came up, 3 of them filed in India." in _fallback_reply(scan, None)
    scan["patents"]["india"]["total"] = 0
    assert "none of them filed in India" in _fallback_reply(scan, None)
    scan["patents"]["india"] = None  # a source that cannot tell says nothing about India
    assert "57 related patents came up." in _fallback_reply(scan, None)
