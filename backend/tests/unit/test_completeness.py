"""Unit tests for the completeness scorer — all four tiers + edge cases."""

from app.services.completeness import (
    CompletenessInput,
    score_completeness,
)

BASIC = {
    "name": "Selvi",
    "email": "selvi@example.com",
    "phone": "+919876543210",
    "date_of_birth": "1988-01-01",
    "gender": "female",
    "state": "Tamil Nadu",
    "district": "Erode",
    "city": "Erode",
}
EDUCATION = {
    "highest_qualification": "Diploma",
    "institution": "Govt Polytechnic",
    "graduation_year": 2008,
}
STARTUP = {
    "startup_name": "Kaithari Weaves",
    "entity_type": "sole_proprietor",
    "domain": "handloom",
    "stage": "idea",
}


def test_incomplete_below_basic_scores_zero():
    r = score_completeness(CompletenessInput(founder={"name": "Selvi"}))
    assert r.score == 0
    assert r.tier == "incomplete"
    assert any(f.startswith("founder.") for f in r.missing_fields)


def test_basic_only_scores_40():
    r = score_completeness(CompletenessInput(founder=dict(BASIC)))
    assert r.score == 40
    assert r.tier == "basic"
    # Next tier blocked by education fields.
    assert "founder.highest_qualification" in r.missing_fields


def test_basic_plus_education_scores_60():
    r = score_completeness(CompletenessInput(founder={**BASIC, **EDUCATION}))
    assert r.score == 60
    assert r.tier == "standard"
    assert r.missing_fields == [
        f"startup.{f}" for f in ("startup_name", "entity_type", "domain", "stage")
    ]


def test_with_startup_scores_80():
    r = score_completeness(CompletenessInput(founder={**BASIC, **EDUCATION}, startup=dict(STARTUP)))
    assert r.score == 80
    assert r.tier == "verified"
    assert r.missing_fields == ["documents.verified"]


def test_full_with_verified_docs_scores_100():
    r = score_completeness(
        CompletenessInput(
            founder={**BASIC, **EDUCATION},
            startup=dict(STARTUP),
            has_verified_documents=True,
        )
    )
    assert r.score == 100
    assert r.tier == "investment_ready"
    assert r.missing_fields == []
    assert "verified_documents" in r.verified_fields


def test_tiers_are_cumulative_not_additive():
    # Verified docs without startup details must NOT jump to 100 — caps at 60.
    r = score_completeness(
        CompletenessInput(founder={**BASIC, **EDUCATION}, startup=None, has_verified_documents=True)
    )
    assert r.score == 60


def test_score_is_always_a_valid_tier():
    for inp in [
        CompletenessInput(founder={}),
        CompletenessInput(founder=dict(BASIC)),
        CompletenessInput(founder={**BASIC, **EDUCATION}),
    ]:
        assert score_completeness(inp).score in (0, 40, 60, 80, 100)
