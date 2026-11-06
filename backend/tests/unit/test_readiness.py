"""Unit tests for funding readiness scoring and gap analysis."""

from app.funding.gaps import GAP_THRESHOLD, analyze_gaps
from app.funding.readiness import NOT_ENOUGH, RUBRIC, WEIGHTS, score_readiness

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


def test_empty_profile_is_not_assessed_not_a_zero_score():
    # nothing answered: unknown, not a hard zero (F-A4-016)
    r = score_readiness({})
    assert r.overall == 0
    assert r.band == NOT_ENOUGH
    assert set(r.dimensions) == set(WEIGHTS)
    assert set(r.not_assessed) == set(WEIGHTS)  # every dimension unassessed
    assert all(c == 0.0 for c in r.coverage.values())
    assert r.next_inputs  # it tells the founder what to answer first


def test_overall_is_computed_over_assessed_dimensions_only():
    # a founder who has fully answered only the team dimension is scored on it,
    # not dragged to ~zero by the five dimensions they have not touched yet.
    team_only = {
        "founder_experience_years": 6,
        "team_size": 4,
        "has_domain_expertise": True,
        "advisors_count": 3,
    }
    r = score_readiness(team_only)
    assert r.coverage["team"] == 1.0
    assert r.not_assessed == [d for d in WEIGHTS if d != "team"]
    # overall equals the team dimension alone (only assessed dimension)
    assert r.overall == r.dimensions["team"]
    assert r.band != NOT_ENOUGH


def test_known_false_flag_counts_as_coverage_but_zero_points():
    # answering "no" to every legal question is a real answer: the dimension is
    # assessed (coverage 1.0) and scores 0 — different from never answering.
    answered_no = dict.fromkeys((inp.key for inp in RUBRIC["legal"]), False)
    r = score_readiness(answered_no)
    assert r.coverage["legal"] == 1.0
    assert r.dimensions["legal"] == 0
    assert "legal" not in r.not_assessed


def test_adding_a_true_fact_never_lowers_a_dimension():
    # monotonicity (F-A4-016): each added answer only raises its dimension
    base: dict = {}
    for inp in RUBRIC["financial"]:
        before = score_readiness(base).dimensions["financial"]
        base[inp.key] = 12 if inp.kind == "num" else True
        after = score_readiness(base).dimensions["financial"]
        assert after >= before


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
    profile = {"is_registered": True}  # mostly weak
    r = score_readiness(profile)
    gaps = analyze_gaps(profile, r)
    assert gaps, "expected recommendations for weak dimensions"
    weak_dims = {d for d, s in r.dimensions.items() if s < GAP_THRESHOLD}
    assert {g.dimension for g in gaps} <= weak_dims
    ratios = [g.ratio for g in gaps]
    assert ratios == sorted(ratios, reverse=True)  # impact/effort descending
    # the entity is already registered, so that action is not offered again
    assert not any(g.action.startswith("Register the entity") for g in gaps)


def test_no_gaps_for_strong_profile():
    assert analyze_gaps(STRONG, score_readiness(STRONG)) == []


def test_gap_impact_is_the_real_rubric_delta():
    """Each action's impact equals the dimension change it actually makes (F-A4-018)."""
    from app.funding.gaps import _PLAYBOOK

    profile: dict = {}  # nothing answered: every action has room to help
    r = score_readiness(profile)
    recs = {(g.dimension, g.action): g for g in analyze_gaps(profile, r)}
    for dim, actions in _PLAYBOOK.items():
        for action in actions:
            if action.precondition and not action.precondition(profile):
                continue
            after = score_readiness({**profile, **action.sets}).dimensions[dim]
            expected = after - r.dimensions[dim]
            if expected <= 0:
                continue
            assert recs[(dim, action.label)].impact_points == expected


def test_mvp_founder_is_not_told_to_ship_an_mvp():
    """A precondition keeps stage-reached actions out once the founder is there (F-A4-018)."""
    profile = {"stage": "mvp", "feature_completeness": 20}
    gaps = analyze_gaps(profile, score_readiness(profile))
    assert not any("Ship an MVP" in g.action for g in gaps)
    # an idea-stage founder, by contrast, is offered it
    idea = {"stage": "idea", "feature_completeness": 20}
    assert any("Ship an MVP" in g.action for g in analyze_gaps(idea, score_readiness(idea)))


def test_unknown_input_actions_are_marked_conditional():
    # nothing answered in legal: the register action is offered "if not done yet"
    profile: dict = {}
    gaps = {g.action: g for g in analyze_gaps(profile, score_readiness(profile))}
    reg = next(g for a, g in gaps.items() if a.startswith("Register the entity"))
    assert reg.conditional is True
    # a founder who said they are NOT registered gets it unconditionally
    not_reg = analyze_gaps({"is_registered": False}, score_readiness({"is_registered": False}))
    reg2 = next(g for g in not_reg if g.action.startswith("Register the entity"))
    assert reg2.conditional is False


def test_revenue_stage_scores_above_mvp_not_zero() -> None:
    """A revenue-stage founder must not fall through to a 0 product score (F-A4-015)."""
    base = {"feature_completeness": 50, "has_ip": False}
    mvp = score_readiness({**base, "stage": "mvp"})
    revenue = score_readiness({**base, "stage": "revenue"})
    # "revenue" used to be absent from the stage table and scored like "idea"
    assert revenue.dimensions["product"] > mvp.dimensions["product"]


def test_stage_spelling_variants_score_the_same() -> None:
    base = {"feature_completeness": 50}
    assert (
        score_readiness({**base, "stage": "launched"}).dimensions["product"]
        == score_readiness({**base, "stage": "revenue"}).dimensions["product"]
    )
