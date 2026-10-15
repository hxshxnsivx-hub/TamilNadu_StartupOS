"""Unit tests for the startup ecosystem: sectors, hotspot zones, investor matching."""

from __future__ import annotations

from collections import Counter

from app.ecosystem.index import build
from app.ecosystem.match import Founder, judge, match
from app.ecosystem.taxonomy import sector_of_nic, sectors_in
from app.ecosystem.zones import PinActivity, build_district, nearest_zone


def test_sector_vocabulary():
    assert sector_of_nic("72200") == "saas"
    assert sector_of_nic("24230") == "biotech_pharma"  # class overrides division
    assert sector_of_nic("NA") is None
    assert sectors_in("Seed fund for EdTech and AI-first SaaS") == ["edtech", "saas", "deeptech"]
    assert sectors_in("coworking workspace") == []  # "space" inside a word is not space tech
    assert "fintech" not in sectors_in("Private credit and growth equity")


Point = tuple[float, float]


def _grid(cluster: list[Point], quiet: list[Point]) -> list[PinActivity]:
    pins = []
    for i, (lat, lon) in enumerate(cluster):
        pins.append(
            PinActivity(
                f"6000{i:02d}",
                lat,
                lon,
                "chennai",
                f"Busy{i}",
                {"companies": 200, "branches": 20},
                Counter({"saas": 150, "textiles": 10}),
            )
        )
    for i, (lat, lon) in enumerate(quiet):
        pins.append(
            PinActivity(
                f"6001{i:02d}",
                lat,
                lon,
                "chennai",
                f"Quiet{i}",
                {"companies": 2, "branches": 1},
                Counter({"textiles": 5}),
            )
        )
    return pins


def _two_clusters() -> list[PinActivity]:
    # Two busy clusters ~15 km apart, ringed and separated by quiet pins (~1.1 km spacing).
    a = [(13.00 + 0.01 * i, 80.20 + 0.01 * j) for i in range(2) for j in range(2)]
    b = [(13.00 + 0.01 * i, 80.34 + 0.01 * j) for i in range(2) for j in range(2)]
    quiet = [(12.97 + 0.01 * i, 80.17 + 0.01 * j) for i in range(8) for j in range(22)]
    quiet = [q for q in quiet if q not in a and q not in b]
    return _grid(a + b, quiet)


def test_hotspots_split_into_one_zone_per_cluster():
    dz = build_district("chennai", _two_clusters())
    assert len(dz.zones) == 2
    west, east = sorted(dz.zones, key=lambda z: z.lon)
    for z in dz.zones:
        assert z.peak_z >= 1.645
        assert z.peak_pin.startswith("6000")  # peaks on a busy pin
    # Every busy pin is in a zone, and each cluster's pins in its own zone. (Quiet pins
    # touching a cluster may join it: Gi* scores a pin with its neighbours.)
    busy = {p.pin: p for p in dz.pins.values() if p.pin.startswith("6000")}
    for pin, p in busy.items():
        assert dz.zone_of[pin] == (west.id if p.lon < 80.3 else east.id)
    # Each cluster's software firms are over-represented against the district.
    assert dz.zones[0].specialisations[0][0] == "saas"


def test_pin_outside_hotspots_gets_nearest_zone_and_distance():
    dz = build_district("chennai", _two_clusters())
    inside = dz.zones[0].pins[0]
    assert nearest_zone(dz, inside) == (dz.zones[0], 0.0)
    z, km = nearest_zone(dz, "600100")
    assert km > 0
    assert nearest_zone(dz, "999999") is None


INVESTORS = {
    "edtech_angel": {
        "slug": "edtech_angel",
        "name": "EdTech Angel Fund",
        "city": "Chennai",
        "serves_founders": True,
        "instrument": "equity",
        "stages": ["seed", "pre_series_a"],
        "sectors": ["edtech", "healthtech"],
        "generalist": False,
        "ticket_lakh": [100.0, 300.0],
    },
    "any_angels": {
        "slug": "any_angels",
        "name": "Any Angels",
        "city": "Madurai",
        "serves_founders": True,
        "instrument": "equity",
        "stages": ["seed"],
        "sectors": [],
        "generalist": True,
        "ticket_lakh": None,
    },
    "lender": {
        "slug": "lender",
        "name": "Lender",
        "city": "Chennai",
        "serves_founders": True,
        "instrument": "debt",
        "stages": [],
        "sectors": [],
        "generalist": True,
        "ticket_lakh": None,
    },
    "growth_pe": {
        "slug": "growth_pe",
        "name": "Growth PE",
        "city": "Chennai",
        "serves_founders": True,
        "instrument": "equity",
        "stages": ["growth"],
        "sectors": ["consumer"],
        "generalist": False,
        "ticket_lakh": None,
    },
    "realty": {
        "slug": "realty",
        "name": "Realty Fund",
        "serves_founders": False,
        "not_for_founders_reason": "Real-estate fund: does not invest in startups",
    },
}
SEED_EDTECH = Founder(sectors=["edtech"], stage="seed", district="chennai", ask_lakh=150)


def test_investor_refusals_carry_reasons():
    refused = judge(INVESTORS["realty"], SEED_EDTECH, {})
    assert refused.reasons == ["Real-estate fund: does not invest in startups"]
    r = judge(INVESTORS["growth_pe"], SEED_EDTECH, {})
    assert "Invests at growth — not seed" in r.reasons
    assert "Invests in Consumer, retail & D2C" in r.reasons
    equity_only = Founder(sectors=["edtech"], stage="seed", district="chennai", instrument="equity")
    assert judge(INVESTORS["lender"], equity_only, {}).reasons == [
        "Lends (debt), you asked for equity"
    ]
    big = Founder(sectors=["edtech"], stage="seed", district="chennai", ask_lakh=2000)
    assert judge(INVESTORS["edtech_angel"], big, {}).reasons == [
        "Writes ₹100–300L cheques; you need ₹2000L"
    ]


def test_thesis_match_outranks_generalist_and_unknowns_are_left_out():
    focused = judge(INVESTORS["edtech_angel"], SEED_EDTECH, {})
    general = judge(INVESTORS["any_angels"], SEED_EDTECH, {})
    assert focused.fit > general.fit
    assert focused.signals["sector"] == 1.0 and general.signals["sector"] == 0.6
    assert "ticket" not in general.signals  # no stated cheque size: not scored, not guessed
    assert general.signals["nearness"] == 0.7  # Madurai investor, Chennai founder


def test_site_with_pitch_route_counts_as_reachable():
    signals = {
        "any_angels": {"status": "ok", "pitch_url": "https://example.org/apply", "evidence": []}
    }
    m = judge(INVESTORS["any_angels"], SEED_EDTECH, signals)
    assert m.signals["reachable"] == 1.0
    assert m.reachability["pitch_url"] == "https://example.org/apply"
    assert judge(INVESTORS["any_angels"], SEED_EDTECH, {}).signals["reachable"] == 0.3


def test_match_puts_founder_in_zone_and_finds_peers_and_companies():
    raw = {
        "_meta": {"districts": ["chennai"]},
        "pins": {
            "600004": {"lat": 13.03, "lon": 80.26, "district": "chennai", "name": "Mylapore"},
            "600020": {"lat": 13.00, "lon": 80.25, "district": "chennai", "name": "Adyar"},
        },
        "companies": [
            {
                "cin": f"U{i}",
                "name": f"Edu {i}",
                "sector": "edtech",
                "pin": "600004",
                "district": "chennai",
                "paidup_lakh": i,
                "year": 2018,
            }
            for i in range(12)
        ],
        "startups": [
            {
                "slug": "learnco",
                "name": "LearnCo",
                "sectors": ["edtech"],
                "district": "chennai",
                "pin": "600004",
                "lat": 13.03,
                "lon": 80.26,
                "careers_url": "https://l.co/jobs",
                "source_url": "x",
            }
        ],
        "investors": list(INVESTORS.values()),
    }
    eco = build(raw, Counter({"600004": 30, "600020": 2}))
    f = Founder(sectors=["edtech"], stage="seed", district="chennai", pin="600004", ask_lakh=150)
    r = match(eco, f)
    assert r.investors[0].investor["slug"] == "edtech_angel"
    assert {x.investor["slug"] for x in r.refused} == {"realty", "growth_pe"}
    assert r.peers[0]["name"] == "LearnCo" and r.peers[0]["hiring"]
    assert r.company_counts["district_same_sector"] == 12


# --- Incubators -----------------------------------------------------------------

from app.ecosystem import incubators as incmod  # noqa: E402
from app.ecosystem.incubators import judge_incubator, programme_fit  # noqa: E402


def _inc(**kw):
    base = {
        "id": "x",
        "name": "Test Incubator",
        "host": "Test College",
        "district": "chennai",
        "area": "Guindy",
        "pin": "600025",
        "sectors": ["healthtech"],
        "stages": ["pre_seed", "seed"],
        "programmes": ["BioNEST"],
        "notes": "",
        "source_url": "x",
        "confidence": "official",
    }
    base.update(kw)
    return base


PINS = {"600025": (13.0108, 80.2354), "600020": (13.0012, 80.2565)}


def _founder(**kw):
    base = {"sectors": ["healthtech"], "stage": "seed", "district": "chennai", "pin": "600020"}
    base.update(kw)
    return Founder(**base)


def test_incubator_refusals_carry_reasons():
    late = judge_incubator(_inc(), _founder(stage="series_a"), PINS)
    assert late.reasons == ["Incubators take idea-to-MVP startups; look at investors at your stage"]
    off = judge_incubator(_inc(), _founder(sectors=["fintech"]), PINS)
    assert off.reasons == ["Focuses on Health & medical"]
    only_idea = judge_incubator(_inc(stages=["pre_seed"]), _founder(), PINS)
    assert only_idea.reasons == ["Takes idea and prototype startups, not MVP"]
    elsewhere = judge_incubator(_inc(district="madurai"), _founder(), PINS)
    assert elsewhere.reasons[0] == "Serves Madurai, not Chennai"


def test_general_incubator_takes_any_sector_at_lower_weight():
    focused = judge_incubator(_inc(), _founder(), PINS)
    general = judge_incubator(_inc(sectors=["general"]), _founder(sectors=["fintech"]), PINS)
    assert focused.signals["sector"] == 1.0 and general.signals["sector"] == 0.6
    assert focused.fit > general.fit


def test_travel_is_estimated_and_unknown_campus_scores_half():
    m = judge_incubator(_inc(), _founder(), PINS)
    assert m.travel["basis"] == "estimate" and 0 < m.travel["minutes"] < 15
    assert m.signals["nearness"] > 0.8
    unknown = judge_incubator(_inc(pin=""), _founder(), PINS)
    assert unknown.travel is None and unknown.signals["nearness"] == 0.5
    neighbour = judge_incubator(
        _inc(district="tiruppur", pin=""), _founder(district="coimbatore", pin=None), PINS
    )
    assert neighbour.signals["nearness"] == 0.5


def test_programmes_say_whether_money_reaches_this_founder(monkeypatch):
    monkeypatch.setattr(incmod, "scheme_status", lambda: {"sisfs": "active"})
    assert programme_fit("SISFS", _founder(dpiit=False))["applies"] == "no"
    assert programme_fit("SISFS", _founder(dpiit=True, company_age_years=3))["reason"] == (
        "Company must be under 2 years old"
    )
    assert programme_fit("SISFS", _founder())["applies"] == "check"
    assert programme_fit("SISFS", _founder(dpiit=True, company_age_years=1))["applies"] == "yes"
    monkeypatch.setattr(incmod, "scheme_status", lambda: {"sisfs": "closed"})
    closed = programme_fit("SISFS", _founder(dpiit=True, company_age_years=1))
    assert closed["applies"] == "closed" and closed["reason"].endswith("scheme closed now")
    assert programme_fit("BioNEST", _founder())["applies"] == "yes"
    assert programme_fit("BioNEST", _founder(sectors=["saas"]))["applies"] == "no"
    assert programme_fit("NABARD", _founder(sectors=["agritech"]))["applies"] == "yes"


def test_money_signal_follows_programmes():
    paying = judge_incubator(_inc(), _founder(), PINS)
    support = judge_incubator(_inc(programmes=["AIC"]), _founder(), PINS)
    assert paying.signals["money"] == 1.0 and support.signals["money"] == 0.4


# --- Incubator intake -----------------------------------------------------------

import datetime as dt  # noqa: E402

from app.ecosystem import intake as intakemod  # noqa: E402
from app.ecosystem.intake import classify_intake, current_intake, parse_date  # noqa: E402

TODAY = dt.date(2026, 10, 5)


def _cls(text, apply_url=None):
    return classify_intake([("https://inc.example/", text)], apply_url, TODAY)


def test_dates_in_indian_and_written_formats():
    assert parse_date("15 October 2026") == dt.date(2026, 10, 15)
    assert parse_date("15th Oct, 2026") == dt.date(2026, 10, 15)
    assert parse_date("October 15, 2026") == dt.date(2026, 10, 15)
    assert parse_date("15-10-2026") == dt.date(2026, 10, 15)  # day first
    assert parse_date("31/02/2026") is None


def test_intake_status_from_page_words():
    upcoming = _cls("Cohort 7. Last date: 20 October 2026.")
    assert upcoming["status"] == "open" and upcoming["deadline"] == "2026-10-20"
    assert _cls("Cohort 6. Last date: 20 August 2026.")["status"] == "closed"
    assert _cls("Applications are closed for this cohort.")["status"] == "closed"
    assert _cls("Applications open for the healthcare programme")["status"] == "open"
    assert _cls("Apply now and take your idea further")["status"] == "rolling"
    assert _cls("About us", apply_url="https://inc.example/apply")["status"] == "apply_page"
    assert _cls("About us")["status"] == "unknown"
    # A future deadline outweighs a closed notice for an older call on the same page.
    both = _cls("Cohort 5 applications closed. Cohort 6 deadline 1 Nov 2026.")
    assert both["status"] == "open"


def test_stale_or_lapsed_checks_are_not_trusted(monkeypatch):
    rec = {"checked": "2026-09-01", "status": "open", "deadline": None, "evidence": []}
    monkeypatch.setattr(intakemod, "load_intake", lambda: {"x": rec})
    assert current_intake("x", TODAY)["status"] == "stale"
    lapsed = {"checked": "2026-10-01", "status": "open", "deadline": "2026-10-03", "evidence": []}
    monkeypatch.setattr(intakemod, "load_intake", lambda: {"x": lapsed})
    assert current_intake("x", TODAY)["status"] == "closed"
    assert current_intake("missing", TODAY) is None


def test_intake_feeds_the_incubator_ranking(monkeypatch):
    monkeypatch.setattr(incmod, "current_intake", lambda _id: {"status": "open", "checked": "x"})
    open_now = judge_incubator(_inc(), _founder(), PINS)
    monkeypatch.setattr(incmod, "current_intake", lambda _id: {"status": "closed", "checked": "x"})
    closed = judge_incubator(_inc(), _founder(), PINS)
    monkeypatch.setattr(incmod, "current_intake", lambda _id: {"status": "stale", "checked": "x"})
    stale = judge_incubator(_inc(), _founder(), PINS)
    assert open_now.signals["intake"] == 1.0 and "Taking applications now" in open_now.why
    assert closed.fit < open_now.fit
    assert "intake" not in stale.signals  # old checks are left out, not counted as closed
