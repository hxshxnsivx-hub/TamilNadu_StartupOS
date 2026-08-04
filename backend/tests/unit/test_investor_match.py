"""Unit tests for investor constraint matching + fit ranking."""

from app.funding.investor_match import match_investors, readiness_gate

STARTUP = {
    "sector": "agritech",
    "stage": "mvp",
    "users": 800,
    "monthly_revenue": 60_000,
    "state": "Tamil Nadu",
}


def _ids(items):
    return [x.investor.id for x in items]


def test_eligible_set_for_agri_seed_startup():
    res = match_investors(STARTUP, funding_need=2_000_000, readiness_overall=65)
    eligible = set(_ids(res.eligible))
    assert eligible == {"angel_ravi", "greenshoot_vc"}
    assert res.total_checked == 6


def test_ineligible_reasons_are_named():
    res = match_investors(STARTUP, funding_need=2_000_000, readiness_overall=65)
    by_id = {i.investor.id: i for i in res.ineligible}
    # ticket too big / wrong stage / wrong sector
    assert "meridian_vc" in by_id
    assert any(
        "Ticket" in r or "stage" in r or "Focuses" in r for r in by_id["meridian_vc"].reasons
    )
    # not investing
    assert any("Not currently investing" in r for r in by_id["dormant_fund"].reasons)
    # funding need below min ticket
    assert any("Ticket" in r for r in by_id["agri_corp_vc"].reasons)


def test_fit_ranking_sorted_and_bounded():
    res = match_investors(STARTUP, funding_need=2_000_000, readiness_overall=65)
    fits = [e.fit for e in res.eligible]
    assert fits == sorted(fits, reverse=True)  # ranked by fit, descending
    assert all(0 <= f <= 100 for f in fits)
    # a founder who comfortably clears an angel's (zero) floor is its strongest fit
    assert _ids(res.eligible)[0] == "angel_ravi"


def test_readiness_gate_blocks_low_readiness():
    res = match_investors(STARTUP, funding_need=2_000_000, readiness_overall=40)
    # all now fail the readiness gate → none eligible
    assert res.eligible == []
    assert any("Readiness" in r for i in res.ineligible for r in i.reasons)


def test_readiness_gate_levels():
    assert readiness_gate("mvp") == 60
    assert readiness_gate("series_a") == 70
    assert readiness_gate("growth") == 70
