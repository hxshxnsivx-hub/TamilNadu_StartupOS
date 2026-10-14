"""Unit tests for the rule engine and the scheme eligibility engine."""

from app.schemes.engine import check_eligibility, compute_age
from app.schemes.rules import Combinator, EvalResult, Op, Rule, RuleGroup, evaluate


# ── primitive operators ──────────────────────────────────────────────────────
def _ev(node, profile) -> EvalResult:
    return evaluate(node, profile)


def test_operators():
    p = {"a": {"age": 30, "flag": True, "cat": "sc", "rev": 500}}
    assert _ev(Rule("a.age", Op.GTE, 18), p).ok
    assert not _ev(Rule("a.age", Op.LT, 18), p).ok
    assert _ev(Rule("a.age", Op.BETWEEN, [21, 45]), p).ok
    assert _ev(Rule("a.cat", Op.IN, ["sc", "st"]), p).ok
    assert _ev(Rule("a.cat", Op.NOT_IN, ["general"]), p).ok
    assert _ev(Rule("a.flag", Op.IS_TRUE), p).ok
    assert not _ev(Rule("a.flag", Op.IS_FALSE), p).ok


def test_missing_field_fails_positive_rule():
    assert not _ev(Rule("a.missing", Op.GTE, 1), {"a": {}}).ok


def test_all_group_collects_reasons():
    g = RuleGroup(
        Combinator.ALL,
        [
            Rule("x.age", Op.GTE, 18, label="18+"),
            Rule("x.state", Op.EQ, "TN", label="in TN"),
        ],
    )
    r = _ev(g, {"x": {"age": 16, "state": "KA"}})
    assert not r.ok
    assert "18+" in r.reasons and "in TN" in r.reasons


def test_any_group_or_semantics():
    g = RuleGroup(
        Combinator.ANY,
        [
            Rule("x.cat", Op.IN, ["sc", "st"]),
            Rule("x.gender", Op.EQ, "female"),
        ],
        label="SC/ST or women",
    )
    assert _ev(g, {"x": {"cat": "general", "gender": "female"}}).ok  # OR passes
    r = _ev(g, {"x": {"cat": "general", "gender": "male"}})
    assert not r.ok and r.reasons == ["SC/ST or women"]


def test_compute_age():
    assert compute_age("1996-07-30") in (29, 30)  # depends on run date
    assert compute_age(None) is None


# ── end-to-end eligibility ───────────────────────────────────────────────────
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
        "stage": "mvp",
        "dpiit_recognized": True,
        "incorporation_age_years": 1,
        "annual_revenue": 500_000,
    },
}
KARTHIK = {
    "founder": {
        "state": "Karnataka",
        "gender": "male",
        "caste_category": "general",
        "first_graduate": False,
        "age": 50,
    },
    "startup": {
        "entity_type": "sole_proprietor",
        "stage": "growth",
        "dpiit_recognized": False,
        "incorporation_age_years": 5,
        "annual_revenue": 2_000_000_000,
    },
}


def test_selvi_is_broadly_eligible():
    res = check_eligibility(SELVI)
    ids = {s.id for s in res.eligible}
    # first-generation SC woman in TN with a young DPIIT startup unlocks these:
    for expected in ("sisfs", "tanseed", "needs", "standup_india", "uyegp"):
        assert expected in ids, expected
    assert res.total_checked == 8


def test_karthik_ineligibility_has_named_reasons():
    res = check_eligibility(KARTHIK)
    by_id = {i.scheme.id: i for i in res.ineligible}

    assert "sisfs" in by_id
    assert any("DPIIT" in r for r in by_id["sisfs"].reasons)

    assert "standup_india" in by_id
    assert by_id["standup_india"].reasons == ["For SC/ST or women entrepreneurs"]

    assert "tanseed" in by_id  # not in Tamil Nadu
    assert any("Tamil Nadu" in r for r in by_id["tanseed"].reasons)


def test_or_branch_via_female_general_founder():
    # general-category woman → Stand-Up India eligible through the OR branch
    profile = {
        "founder": {"gender": "female", "caste_category": "general", "age": 28},
        "startup": {"entity_type": "private_limited"},
    }
    res = check_eligibility(profile)
    assert "standup_india" in {s.id for s in res.eligible}


def test_corrections_checked_against_the_sources_on_2026_10_14():
    """Amounts and exclusions that were wrong before the check (see app/schemes/seed.py)."""
    from app.schemes.seed import SEED_SCHEMES

    by_id = {s.id: s for s in SEED_SCHEMES}
    # a subsidy is a share of the project cost, never the project cost itself
    assert by_id["pmegp"].max_funding == 1_750_000
    assert by_id["uyegp"].max_funding < 500_000
    assert by_id["sisfs"].max_funding == 2_000_000 and "₹50 lakh" in by_id["sisfs"].benefits
    assert by_id["cgtmse"].max_funding == 100_000_000
    assert "3% stake" in by_id["tanseed"].benefits  # not "equity-free"

    proprietor = {
        "founder": {"state": "Tamil Nadu", "age": 30},
        "startup": {"entity_type": "sole_proprietor", "annual_revenue": 2_000_000},
    }
    res = check_eligibility(proprietor)
    assert "cgtmse" in {s.id for s in res.eligible}  # proprietorships are covered
    sisfs = {i.scheme.id: i for i in res.ineligible}["sisfs"]
    assert any("sole proprietorships" in r for r in sisfs.reasons)

    partnership = {
        "founder": {"state": "Tamil Nadu", "age": 30},
        "startup": {"entity_type": "partnership", "dpiit_recognized": True,
                    "incorporation_age_years": 1, "stage": "prototype"},
    }  # fmt: skip
    ids = {s.id for s in check_eligibility(partnership).eligible}
    assert "sisfs" in ids and "tanseed" in ids

    older = {"founder": {"state": "Tamil Nadu", "age": 50}, "startup": {}}
    uyegp = {i.scheme.id: i for i in check_eligibility(older).ineligible}["uyegp"]
    assert any("18–45" in r for r in uyegp.reasons)
    no_dpiit = {"founder": {"state": "Tamil Nadu"}, "startup": {"dpiit_recognized": False}}
    tanseed = {i.scheme.id: i for i in check_eligibility(no_dpiit).ineligible}["tanseed"]
    assert any("DPIIT" in r for r in tanseed.reasons)
