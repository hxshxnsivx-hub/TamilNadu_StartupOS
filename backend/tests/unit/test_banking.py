"""Unit tests for bank loan routing: matching, rails and branch allocation."""

from __future__ import annotations

from app.banking.allocate import allocate
from app.banking.branches import BranchIndex, haversine_km
from app.banking.catalogue import load_schemes
from app.banking.matcher import check, match
from app.banking.models import LoanNeed
from app.banking.router import decide

SCHEMES = {s.id: s for s in load_schemes()}


def _need(**kw) -> LoanNeed:
    base = {"amount_lakh": 15, "purpose": "tl"}
    base.update(kw)
    return LoanNeed(**base)


def _index() -> BranchIndex:
    # Pin A at the origin; pin B about 5.5 km north.
    pins = {"641201": [10.9174, 77.0378], "641050": [10.9670, 77.0378]}
    rows = [
        ("SBIN0000001", "State Bank of India", "SBIN", "public", "641201"),
        ("CNRB0000002", "Canara Bank", "CNRB", "public", "641050"),
        ("HDFC0000003", "HDFC Bank", "HDFC", "private", "641050"),
    ]
    branches = [
        {
            "ifsc": i,
            "bank": b,
            "bank_code": c,
            "type": t,
            "branch": "X",
            "address": "",
            "district": "coimbatore",
            "pin": p,
        }
        for i, b, c, t, p in rows
    ]
    return BranchIndex(pins, branches)


def test_catalogue_loads_all_schemes():
    assert len(SCHEMES) == 48
    assert SCHEMES["cgss"].is_guarantee


def test_every_refusal_has_a_reason():
    res = match(_need(amount_lakh=40, purpose="wc"))
    assert res.rejected
    assert all(m.reasons for m in res.rejected)


def test_women_only_scheme_explains_refusal():
    m = check(SCHEMES["canara_mv"], _need(amount_lakh=40))
    assert not m.eligible
    assert "Only for women-owned businesses (51%+)" in m.reasons
    assert check(SCHEMES["canara_mv"], _need(amount_lakh=40, women_owned=True)).eligible


def test_amount_and_closed_scheme_reasons():
    assert (
        "Maximum is ₹1L"
        in check(SCHEMES["sbi_sahaj"], _need(purpose="wc", gst_registered=True)).reasons
    )
    assert "Not open now" in check(SCHEMES["standup"], _need()).reasons


def test_property_only_scheme_needs_collateral():
    m = check(SCHEMES["cub_ebl"], _need(amount_lakh=30, years_in_business=2))
    assert "Needs property or other security" in m.reasons


def test_guarantees_are_returned_separately():
    res = match(_need())
    ids = {m.scheme.id for m in res.guarantees}
    assert {"cgtmse", "mcgs"} <= ids
    assert not ids & {m.scheme.id for m in res.loans}


def test_subsidy_comes_first():
    d = decide(_need(qualifies_for_subsidy=True, gst_registered=True, gst_months=12))
    assert d.primary == "branch_scheme"
    assert d.also == ["online"]


def test_records_without_subsidy_go_online():
    assert decide(_need(gst_registered=True, gst_months=12)).primary == "online"
    assert decide(_need()).primary == "branch_scheme"


def test_collateral_route_follows_rbi_limit_and_guarantees():
    assert decide(_need(amount_lakh=20)).collateral_route == "none_by_rbi_rule"
    d = decide(_need(amount_lakh=50, dpiit=True))
    assert d.guarantee_options == ["CGTMSE", "CGSS", "MCGS-MSME", "TNCGS"]


def test_urgent_need_adds_fast_rail():
    assert "fast_priced" in decide(_need(needs_within_week=True)).also


def test_haversine():
    assert haversine_km((10.9174, 77.0378), (10.9174, 77.0378)) == 0
    assert 5.4 < haversine_km((10.9174, 77.0378), (10.9670, 77.0378)) < 5.6


def test_nearby_sorts_and_filters_by_radius():
    idx = _index()
    near = idx.nearby("641201", 10)
    assert [b.bank for b, _ in near][0] == "State Bank of India"
    assert near[0][1] == 0
    assert len(idx.nearby("641201", 3)) == 1
    assert idx.nearby("999999") == []


def test_branch_located_by_neighbourhood_uses_its_own_position():
    pins = {"641201": [10.9174, 77.0378]}
    rows = [
        {
            "ifsc": "KVBL0000009",
            "bank": "Karur Vysya Bank",
            "bank_code": "KVBL",
            "type": "private_tn",
            "branch": "PODANUR",
            "address": "no pin in address",
            "district": "coimbatore",
            "pin": "",
            "lat": 10.9174,
            "lon": 77.0832,  # about 5 km east
            "located_by": "locality",
        },
        {
            "ifsc": "KVBL0000010",
            "bank": "Karur Vysya Bank",
            "bank_code": "KVBL",
            "type": "private_tn",
            "branch": "UNLOCATED",
            "address": "",
            "district": "coimbatore",
            "pin": "",
        },
    ]
    near = BranchIndex(pins, rows).nearby("641201", 10)
    assert len(near) == 1  # no pin and no coordinates: cannot be placed, so left out
    b, km = near[0]
    assert b.located_by == "locality"
    assert 4.8 < km < 5.2


def test_allocation_ranks_and_is_honest_about_signals():
    a = allocate(_need(), "641201", index=_index())
    assert a.pin_located
    assert a.options
    assert all(0 <= o.score <= 100 for o in a.options)
    assert a.signals_missing == ["track_record", "speed"]
    top = a.options[0]
    # a government scheme loan at the branch inside the pin ranks first
    assert top.scheme.category == "gov"
    assert top.branch is not None and top.branch.bank == "State Bank of India"
    assert top.km == 0


def test_bank_specific_scheme_uses_that_banks_branch():
    a = allocate(_need(amount_lakh=40, women_owned=True), "641201", limit=20, index=_index())
    canara = [o for o in a.options if o.scheme.id == "canara_mv"]
    assert canara and canara[0].branch.bank == "Canara Bank"


def test_unknown_pin_still_returns_schemes_without_branches():
    a = allocate(_need(), "999999", index=_index())
    assert not a.pin_located
    assert a.options and all(o.branch is None for o in a.options)


def test_travel_uses_road_network_when_precomputed_else_estimates():
    pins = {"641201": [10.9174, 77.0378], "641050": [10.9670, 77.0378]}
    rows = [
        {
            "ifsc": i,
            "bank": bank,
            "bank_code": i[:4],
            "type": "public",
            "branch": "X",
            "address": "",
            "district": "coimbatore",
            "pin": "641050",
        }
        for i, bank in (("CNRB0000002", "Canara Bank"), ("IOBA0000004", "Indian Overseas Bank"))
    ]
    # Canara is 5.5 km away in a straight line but 25 minutes by road; IOB has no
    # precomputed road time and is estimated (5.5 × 1.34 km at 34 km/h ≈ 13 min).
    idx = BranchIndex(pins, rows, {"641201": {"CNRB0000002": [25.0, 9.1]}})
    near = idx.nearby("641201", 10)
    assert [b.ifsc for b, _ in near] == ["IOBA0000004", "CNRB0000002"]
    road = idx.travel("641201", near[1][0], near[1][1])
    assert (road.minutes, road.road_km, road.basis) == (25.0, 9.1, "road_network")
    est = idx.travel("641201", near[0][0], near[0][1])
    assert est.basis == "estimate" and 12 < est.minutes < 14


def test_allocation_nearness_uses_road_minutes():
    idx = _index()
    idx.travel_table = {"641201": {"SBIN0000001": [2.0, 0.6]}}
    top = allocate(_need(), "641201", index=idx).options[0]
    assert top.travel.basis == "road_network"
    assert top.signals["nearness"] == 1 - 2.0 / 40
