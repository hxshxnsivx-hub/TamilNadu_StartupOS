"""Unit tests for investor constraint matching + fit ranking."""

from app.funding.investor_match import match_investors, readiness_gate
from app.funding.investors import SEED_INVESTORS

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
    res = match_investors(
        STARTUP, funding_need=2_000_000, readiness_overall=65, investors=SEED_INVESTORS
    )
    eligible = set(_ids(res.eligible))
    assert eligible == {"angel_ravi", "greenshoot_vc"}
    assert res.total_checked == 6


def test_ineligible_reasons_are_named():
    res = match_investors(
        STARTUP, funding_need=2_000_000, readiness_overall=65, investors=SEED_INVESTORS
    )
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
    res = match_investors(
        STARTUP, funding_need=2_000_000, readiness_overall=65, investors=SEED_INVESTORS
    )
    fits = [e.fit for e in res.eligible]
    assert fits == sorted(fits, reverse=True)  # ranked by fit, descending
    assert all(0 <= f <= 100 for f in fits)
    # a founder who comfortably clears an angel's (zero) floor is its strongest fit
    assert _ids(res.eligible)[0] == "angel_ravi"


def test_readiness_gate_blocks_low_readiness():
    res = match_investors(
        STARTUP, funding_need=2_000_000, readiness_overall=40, investors=SEED_INVESTORS
    )
    # all now fail the readiness gate → none eligible
    assert res.eligible == []
    assert any("Readiness" in r for i in res.ineligible for r in i.reasons)


def test_readiness_gate_levels():
    assert readiness_gate("mvp") == 60
    assert readiness_gate("scale") == 70
    assert readiness_gate("revenue") == 60
    assert readiness_gate("growth") == 70


# ---- the real Tamil Nadu investors (TN Startup Map) ---------------------------------


def test_real_investors_replace_the_invented_ones_by_default():
    from app.funding.investors import real_investors

    real = {i.id for i in real_investors()}
    res = match_investors({"sector": "cleantech", "stage": "mvp"}, 5_000_000, 65)
    checked = {e.investor.id for e in res.eligible} | {i.investor.id for i in res.ineligible}
    assert checked == real and len(real) >= 30
    assert not checked & {i.id for i in SEED_INVESTORS}  # invented names never shown


def test_an_unpublished_ticket_is_not_a_refusal():
    from app.funding.investors import real_investors

    unknown = [i for i in real_investors() if not i.ticket_known]
    assert unknown
    res = match_investors({"sector": "cleantech", "stage": "mvp"}, 5_000_000, 65)
    assert not any("Ticket size" in r for i in res.ineligible for r in i.reasons
                   if not i.investor.ticket_known)  # fmt: skip


def test_a_fund_that_does_not_back_startups_gives_one_reason():
    res = match_investors({"sector": "cleantech", "stage": "mvp"}, 5_000_000, 65)
    not_startup = [i for i in res.ineligible if i.investor.not_investing_reason]
    assert not_startup and all(len(i.reasons) == 1 for i in not_startup)


def test_specialists_rank_above_generalists():
    from app.funding.investors import ALL_SECTORS

    res = match_investors({"sector": "cleantech", "stage": "mvp"}, 5_000_000, 65)
    fits = {e.investor.id: (e.fit, ALL_SECTORS in e.investor.sectors) for e in res.eligible}
    specialists = [f for f, general in fits.values() if not general]
    generalists = [f for f, general in fits.values() if general]
    assert specialists and generalists and min(specialists) > max(generalists)
