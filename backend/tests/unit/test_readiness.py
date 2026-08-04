"""Unit tests for funding readiness scoring and gap analysis."""

from app.funding.gaps import GAP_THRESHOLD, analyze_gaps
from app.funding.readiness import WEIGHTS, score_readiness

STRONG = {
    "founder_experience_years": 6,
    "team_size": 4,
    "has_domain_expertise": True,
    "advisors_count": 3,
    "stage": "launched",
    "feature_completeness": 90,
    "has_ip": True,
    "users": 2000,
    "monthly_revenue": 200000,
    "retention_rate": 70,
    "partnerships": 3,
    "has_market_validation": True,
    "runway_months": 12,
    "revenue_growth_pct": 25,
    "has_unit_economics": True,
    "has_projections": True,
    "has_pitch_deck": True,
    "deck_completeness": 100,
    "has_clear_problem": True,
    "has_differentiation": True,
    "is_registered": True,
    "dpiit_recognized": True,
    "has_ip_filing": True,
    "is_compliant": True,
    "has_cap_table": True,
}


def test_empty_profile_is_not_ready():
    r = score_readiness({})
    assert r.overall == 0
    assert r.band == "Not Ready"
    assert set(r.dimensions) == set(WEIGHTS)


def test_strong_profile_is_highly_ready():
    r = score_readiness(STRONG)
    assert r.overall >= 81
    assert r.band == "Highly Ready"
    assert all(0 <= v <= 100 for v in r.dimensions.values())


def test_bands_are_ordered():
    weak = score_readiness({"founder_experience_years": 1})
    strong = score_readiness(STRONG)
    assert weak.overall < strong.overall


def test_more_traction_raises_that_dimension():
    low = score_readiness(
        {
            **STRONG,
            "users": 0,
            "monthly_revenue": 0,
            "retention_rate": 0,
            "partnerships": 0,
            "has_market_validation": False,
        }
    )
    assert low.dimensions["traction"] < score_readiness(STRONG).dimensions["traction"]


def test_gaps_only_for_weak_dimensions_and_ranked():
    r = score_readiness({"is_registered": True})  # mostly weak
    gaps = analyze_gaps(r)
    assert gaps, "expected recommendations for weak dimensions"
    weak_dims = {d for d, s in r.dimensions.items() if s < GAP_THRESHOLD}
    assert {g.dimension for g in gaps} <= weak_dims
    ratios = [g.ratio for g in gaps]
    assert ratios == sorted(ratios, reverse=True)  # impact/effort descending


def test_no_gaps_for_strong_profile():
    assert analyze_gaps(score_readiness(STRONG)) == []
