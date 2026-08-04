"""Unit tests for scheme ranking (relevance + approval-likelihood)."""

from app.schemes.ranking import rank_schemes
from app.schemes.seed import SEED_SCHEMES

SELVI = {
    "founder": {
        "state": "Tamil Nadu",
        "gender": "female",
        "caste_category": "sc",
        "first_graduate": True,
        "age": 30,
    },
    "startup": {
        "entity_type": "private_limited",
        "stage": "idea",
        "dpiit_recognized": True,
        "incorporation_age_years": 1,
        "annual_revenue": 500_000,
    },
}


def _by_id(ranked):
    return {r.scheme.id: r for r in ranked}


def test_preference_axis_boosts_likelihood():
    ranked = rank_schemes(SELVI, SEED_SCHEMES)
    r = _by_id(ranked)
    # Stand-Up India favours SC/ST + women → Selvi matches both → high likelihood
    assert r["standup_india"].likelihood >= 80
    # a scheme with no preference axes stays neutral
    assert r["cgtmse"].likelihood == 60


def test_matched_axes_appear_in_why():
    r = _by_id(rank_schemes(SELVI, SEED_SCHEMES))
    why = " ".join(r["standup_india"].why).lower()
    assert "sc/st" in why or "women" in why


def test_stage_fit_affects_relevance():
    idea_stage = _by_id(rank_schemes(SELVI, SEED_SCHEMES))
    # UYEGP targets 'idea' → on-stage for Selvi
    growth = {**SELVI, "startup": {**SELVI["startup"], "stage": "growth"}}
    growth_r = _by_id(rank_schemes(growth, SEED_SCHEMES))
    assert idea_stage["uyegp"].relevance > growth_r["uyegp"].relevance


def test_funding_need_fit():
    r = _by_id(rank_schemes(SELVI, SEED_SCHEMES, funding_need=1_200_000))
    # TANSEED band is 10–15L → 12L fits
    assert r["tanseed"].relevance >= 60
    assert any("funding" in w for w in r["tanseed"].why)


def test_results_sorted_descending():
    ranked = rank_schemes(SELVI, SEED_SCHEMES)
    scores = [r.score for r in ranked]
    assert scores == sorted(scores, reverse=True)
