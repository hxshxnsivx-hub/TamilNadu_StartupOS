"""Seed scheme dataset (Task 2.2).

Indicative encodings of real central / Tamil Nadu / bank schemes as rule-trees.
Amounts and criteria change with government notifications — in production each row
carries a curator-owned ``last_verified`` stamp (design §B). Verify before relying.
"""

from __future__ import annotations

from app.schemes.models import Scheme, SchemeType
from app.schemes.rules import Combinator, Op, Rule, RuleGroup

_V = "2026-07-01"  # last-verified stamp for this seed batch


def _all(*rules) -> RuleGroup:
    return RuleGroup(Combinator.ALL, list(rules))


SEED_SCHEMES: list[Scheme] = [
    Scheme(
        id="sisfs",
        name="Startup India Seed Fund Scheme (SISFS)",
        type=SchemeType.GRANT,
        agency="DPIIT",
        level="central",
        min_funding=2_000_000,
        max_funding=5_000_000,
        sectors=[],
        eligibility=_all(
            Rule("startup.dpiit_recognized", Op.IS_TRUE, label="Requires DPIIT recognition"),
            Rule(
                "startup.incorporation_age_years", Op.LTE, 2, label="Startup must be ≤ 2 years old"
            ),
            Rule(
                "startup.entity_type",
                Op.IN,
                ["private_limited", "llp"],
                label="Entity must be Private Limited or LLP",
            ),
        ),
        benefits="Up to ₹20L validation grant; up to ₹50L via convertible debenture.",
        source_url="https://seedfund.startupindia.gov.in/",
        last_verified=_V,
        unmodelled_notes=["Must not have received > ₹10L from other central schemes."],
    ),
    Scheme(
        id="tanseed",
        name="TANSEED (StartupTN)",
        type=SchemeType.GRANT,
        agency="StartupTN",
        level="state",
        min_funding=1_000_000,
        max_funding=1_500_000,
        sectors=[],
        eligibility=_all(
            Rule("founder.state", Op.EQ, "Tamil Nadu", label="Founder must be in Tamil Nadu"),
            Rule(
                "startup.stage",
                Op.IN,
                ["idea", "poc", "prototype", "mvp"],
                label="Early-stage startups only (idea → MVP)",
            ),
        ),
        benefits="Equity-free grant up to ₹10–15L per cohort edition.",
        source_url="https://startuptn.in/",
        last_verified=_V,
    ),
    Scheme(
        id="pmegp",
        name="Prime Minister's Employment Generation Programme (PMEGP)",
        type=SchemeType.SUBSIDY,
        agency="KVIC",
        level="central",
        min_funding=0,
        max_funding=5_000_000,
        sectors=[],
        eligibility=_all(
            Rule("founder.age", Op.GTE, 18, label="Founder must be at least 18"),
            Rule(
                "startup.incorporation_age_years", Op.LTE, 1, label="For new units only (≤ 1 year)"
            ),
        ),
        benefits="15–35% margin-money subsidy (higher for SC/ST/OBC/women/rural).",
        source_url="https://www.kviconline.gov.in/pmegpeportal/",
        last_verified=_V,
    ),
    Scheme(
        id="mudra",
        name="Pradhan Mantri MUDRA Yojana (PMMY)",
        type=SchemeType.LOAN,
        agency="MUDRA / SIDBI",
        level="bank",
        min_funding=50_000,
        max_funding=2_000_000,
        sectors=[],
        eligibility=_all(
            Rule(
                "startup.annual_revenue",
                Op.LTE,
                10_000_000,
                label="For micro/small enterprises (revenue ≤ ₹1Cr)",
            ),
        ),
        benefits="Collateral-free loan: Shishu/Kishore/Tarun tiers up to ₹20L.",
        source_url="https://www.mudra.org.in/",
        last_verified=_V,
    ),
    Scheme(
        id="standup_india",
        name="Stand-Up India",
        type=SchemeType.LOAN,
        agency="SIDBI",
        level="bank",
        min_funding=1_000_000,
        max_funding=10_000_000,
        sectors=[],
        eligibility=RuleGroup(
            Combinator.ALL,
            [
                Rule("founder.age", Op.GTE, 18, label="Founder must be at least 18"),
                RuleGroup(
                    Combinator.ANY,
                    [
                        Rule("founder.caste_category", Op.IN, ["sc", "st"]),
                        Rule("founder.gender", Op.EQ, "female"),
                    ],
                    label="For SC/ST or women entrepreneurs",
                ),
            ],
        ),
        benefits="₹10L–₹1Cr composite loan for greenfield enterprises.",
        source_url="https://www.standupmitra.in/",
        last_verified=_V,
    ),
    Scheme(
        id="needs",
        name="New Entrepreneur-cum-Enterprise Development Scheme (NEEDS)",
        type=SchemeType.SUBSIDY,
        agency="MSME Tamil Nadu",
        level="state",
        min_funding=0,
        max_funding=7_500_000,
        sectors=[],
        eligibility=_all(
            Rule("founder.state", Op.EQ, "Tamil Nadu", label="Founder must be in Tamil Nadu"),
            Rule("founder.age", Op.BETWEEN, [21, 45], label="Founder aged 21–45"),
            Rule("founder.first_graduate", Op.IS_TRUE, label="For first-generation entrepreneurs"),
        ),
        benefits="25% capital subsidy (cap ~₹75L) + 3% interest subvention + EDP training.",
        source_url="https://www.msmeonline.tn.gov.in/",
        last_verified=_V,
    ),
    Scheme(
        id="uyegp",
        name="Unemployed Youth Employment Generation Programme (UYEGP)",
        type=SchemeType.SUBSIDY,
        agency="MSME Tamil Nadu",
        level="state",
        min_funding=0,
        max_funding=1_000_000,
        sectors=[],
        eligibility=_all(
            Rule("founder.state", Op.EQ, "Tamil Nadu", label="Founder must be in Tamil Nadu"),
            Rule("founder.age", Op.GTE, 18, label="Founder must be at least 18"),
        ),
        benefits="25% subsidy (caps ~₹2.5L) for TN unemployed youth ventures.",
        source_url="https://www.msmeonline.tn.gov.in/",
        last_verified=_V,
    ),
    Scheme(
        id="cgtmse",
        name="Credit Guarantee Fund for Micro & Small Enterprises (CGTMSE)",
        type=SchemeType.GUARANTEE,
        agency="CGTMSE",
        level="bank",
        min_funding=0,
        max_funding=50_000_000,
        sectors=[],
        eligibility=_all(
            Rule(
                "startup.entity_type",
                Op.NOT_IN,
                ["sole_proprietor"],
                label="Registered entity required (not sole proprietor)",
            ),
            Rule(
                "startup.annual_revenue",
                Op.LTE,
                500_000_000,
                label="Micro & small enterprises only",
            ),
        ),
        benefits="Collateral-free loan guarantee cover (ceiling ~₹5Cr).",
        source_url="https://www.cgtmse.in/",
        last_verified=_V,
    ),
]


# Ranking metadata (Task 2.4) — attached post-hoc to keep the definitions above tidy.
_META: dict[str, dict[str, list[str]]] = {
    "sisfs": {"target_stages": ["poc", "prototype", "mvp"], "preference_axes": []},
    "tanseed": {"target_stages": ["idea", "poc", "prototype", "mvp"], "preference_axes": []},
    "pmegp": {"target_stages": ["idea"], "preference_axes": ["sc_st", "women", "rural"]},
    "mudra": {"target_stages": ["idea", "mvp", "revenue"], "preference_axes": ["women"]},
    "standup_india": {"target_stages": ["idea"], "preference_axes": ["sc_st", "women"]},
    "needs": {"target_stages": ["idea", "mvp"], "preference_axes": ["first_graduate"]},
    "uyegp": {"target_stages": ["idea"], "preference_axes": ["rural", "women"]},
    "cgtmse": {"target_stages": ["mvp", "revenue", "growth"], "preference_axes": []},
}
for _s in SEED_SCHEMES:
    _m = _META.get(_s.id, {})
    _s.target_stages = _m.get("target_stages", [])
    _s.preference_axes = _m.get("preference_axes", [])
