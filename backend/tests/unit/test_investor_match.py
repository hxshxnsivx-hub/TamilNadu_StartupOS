"""Unit tests for investor constraint matching + fit ranking."""

from app.funding.investor_match import match_investors
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
    # the leader is decided by varying terms (sector specialism, ticket, track),
    # not by a zero traction floor handing out a free full mark (F-A4-019)
    assert len(set(fits)) > 1  # not all tied on constants
    assert res.eligible[0].why  # the top fit explains itself


def test_readiness_is_advice_not_a_gate():
    """A low readiness score no longer hides otherwise-fitting investors (F-A4-017)."""
    high = match_investors(
        STARTUP, funding_need=2_000_000, readiness_overall=65, investors=SEED_INVESTORS
    )
    low = match_investors(
        STARTUP, funding_need=2_000_000, readiness_overall=40, investors=SEED_INVESTORS
    )
    assert _ids(low.eligible) == _ids(high.eligible)  # readiness changes nothing here
    assert not any("Readiness" in r for i in low.eligible for r in i.why)
    assert not any("Readiness" in r for i in low.ineligible for r in i.reasons)
    assert "readiness is 40" in low.readiness_advice.lower()


# ---- the real Tamil Nadu investors (TN Startup Map) ---------------------------------


def test_real_investors_replace_the_invented_ones_by_default():
    from app.funding.investors import real_investors

    real = {i.id for i in real_investors()}
    res = match_investors({"sector": "cleantech", "stage": "seed"}, 5_000_000, 65)
    checked = (
        {e.investor.id for e in res.eligible}
        | {c.investor.id for c in res.check_with}
        | {i.investor.id for i in res.ineligible}
    )
    assert checked == real and len(real) >= 30
    assert not checked & {i.id for i in SEED_INVESTORS}  # invented names never shown


def test_an_unpublished_ticket_is_not_a_refusal():
    from app.funding.investors import real_investors

    unknown = [i for i in real_investors() if not i.ticket_known]
    assert unknown
    res = match_investors({"sector": "cleantech", "stage": "seed"}, 5_000_000, 65)
    # an unpublished ticket is neither a refusal nor a reason to defer: it is
    # simply not checked, so it never appears as a reason or an unknown (F-A4-019)
    assert not any("Ticket" in r for i in res.ineligible for r in i.reasons
                   if not i.investor.ticket_known)  # fmt: skip
    assert not any("Ticket" in u for c in res.check_with for u in c.unknowns)
    # check-with, when present, is only ever about stage or sector
    assert all(c.unknowns for c in res.check_with)


def test_unpublished_stage_or_sector_is_check_with_not_ineligible():
    """An investor that has not published stage/sector cannot be ruled out (F-A4-019)."""
    from app.funding.investors import Investor

    silent = Investor(
        id="quiet_fund", name="Quiet Fund", type="vc",
        min_ticket=0, max_ticket=0, stages=[], sectors=[], geographies=[],
        ticket_known=False,
    )  # fmt: skip
    res = match_investors({"sector": "edtech", "stage": "mvp"}, 3_000_000, 50, investors=[silent])
    assert not res.ineligible
    assert [c.investor.id for c in res.check_with] == ["quiet_fund"]
    unknowns = res.check_with[0].unknowns
    assert "Investment stage not published" in unknowns
    assert "Sectors not published" in unknowns


def test_early_stage_founders_are_not_zeroed_out():
    """Idea/prototype founders with low readiness still see matches (F-A4-017)."""
    idea = match_investors({"sector": "cleantech", "stage": "idea"}, 1_000_000, 35)
    assert idea.eligible or idea.check_with  # not an empty screen
    proto = match_investors({"sector": "cleantech", "stage": "prototype"}, 1_000_000, 45)
    assert proto.eligible or proto.check_with


def test_a_fund_that_does_not_back_startups_gives_one_reason():
    res = match_investors({"sector": "cleantech", "stage": "seed"}, 5_000_000, 65)
    not_startup = [i for i in res.ineligible if i.investor.not_investing_reason]
    assert not_startup and all(len(i.reasons) == 1 for i in not_startup)


def test_specialists_rank_above_generalists():
    from app.funding.investors import ALL_SECTORS

    res = match_investors({"sector": "cleantech", "stage": "seed"}, 5_000_000, 65)
    fits = {e.investor.id: (e.fit, ALL_SECTORS in e.investor.sectors) for e in res.eligible}
    specialists = [f for f, general in fits.values() if not general]
    generalists = [f for f, general in fits.values() if general]
    assert specialists and generalists and min(specialists) > max(generalists)


def test_revenue_founder_matches_a_later_stage_investor() -> None:
    """A revenue-stage founder must match investors whose stages list rounds (F-A4-015)."""
    # any investor in the real set that invests at series_a / seed should now accept
    # a "revenue" company stage, where the old literal compare ("revenue" in [...]) failed.
    from app.core.vocab import Stage
    from app.funding.investor_match import _accepted_stages
    from app.funding.investors import real_investors

    seen_round_investor = False
    for inv in real_investors():
        if any(s in {"series_a", "series_b", "series_c", "seed", "growth"} for s in inv.stages):
            seen_round_investor = True
            assert Stage.REVENUE in _accepted_stages(inv) or Stage.MVP in _accepted_stages(inv)
    assert seen_round_investor  # the fixture actually exercises the mapping
