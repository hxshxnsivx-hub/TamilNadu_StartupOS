"""Seed scheme dataset (Task 2.2).

Indicative encodings of real central / Tamil Nadu / bank schemes as rule-trees.
Amounts and criteria change with government notifications — in production each row
carries a curator-owned ``last_verified`` stamp (design §B). Verify before relying.
"""

from __future__ import annotations

from app.schemes.models import Scheme, SchemeType
from app.schemes.rules import Combinator, Op, Rule, RuleGroup

# Checked again against official and published sources on this date (amounts, who is
# eligible): all eight.
_CHECKED = "2026-10-14"


def _all(*rules) -> RuleGroup:
    return RuleGroup(Combinator.ALL, list(rules))


SEED_SCHEMES: list[Scheme] = [
    Scheme(
        id="sisfs",
        name="Startup India Seed Fund Scheme (SISFS)",
        type=SchemeType.GRANT,
        agency="DPIIT",
        level="central",
        min_funding=0,
        max_funding=2_000_000,  # the grant; the ₹50L part is debt, in the benefits
        sectors=[],
        eligibility=_all(
            Rule("startup.dpiit_recognized", Op.IS_TRUE, label="Requires DPIIT recognition"),
            Rule(
                "startup.incorporation_age_years", Op.LTE, 2, label="Startup must be ≤ 2 years old"
            ),
            Rule(
                "startup.entity_type",
                Op.NOT_IN,
                ["sole_proprietor"],
                label="Not open to sole proprietorships (or public limited companies)",
            ),
        ),
        benefits=(
            "A grant of up to ₹20 lakh for proof of concept, prototype or trials, paid in"
            " milestone instalments; separately, up to ₹50 lakh as convertible debentures or"
            " debt for market entry. Applied for through an approved incubator."
        ),
        source_url="https://seedfund.startupindia.gov.in/",
        last_verified=_CHECKED,
        unmodelled_notes=[
            "Must not have received more than ₹10 lakh from other central or state schemes"
            " (prizes and subsidised space do not count).",
            "Indian promoters must hold at least 51%.",
            "Not formed by splitting up or reconstructing an existing business.",
        ],
    ),
    Scheme(
        id="tanseed",
        name="TANSEED (StartupTN)",
        type=SchemeType.GRANT,
        agency="StartupTN",
        level="state",
        min_funding=0,
        max_funding=1_500_000,
        sectors=[],
        eligibility=_all(
            Rule("founder.state", Op.EQ, "Tamil Nadu", label="Founder must be in Tamil Nadu"),
            Rule("startup.dpiit_recognized", Op.IS_TRUE, label="Requires DPIIT recognition"),
            Rule(
                "startup.stage",
                Op.IN,
                ["idea", "poc", "prototype", "mvp"],
                label="Early-stage startups only (idea → MVP)",
            ),
        ),
        benefits=(
            "An equity-linked grant (StartupTN takes a 3% stake): up to ₹15 lakh for green-tech,"
            " rural-impact and women-led startups, up to ₹10 lakh for others, paid in"
            " instalments, with a one-year accelerator programme."
        ),
        source_url="https://startuptn.in/",
        last_verified=_CHECKED,
        unmodelled_notes=[
            "Opens in rounds (TANSEED 8.0 closed on 20 December 2025): watch startuptn.in.",
            "The startup must be registered in Tamil Nadu and listed with StartupTN.",
        ],
    ),
    Scheme(
        id="pmegp",
        name="Prime Minister's Employment Generation Programme (PMEGP)",
        type=SchemeType.SUBSIDY,
        agency="KVIC",
        level="central",
        min_funding=0,
        max_funding=1_750_000,  # 35% of a ₹50L project, the highest rate
        sectors=[],
        eligibility=_all(
            Rule("founder.age", Op.GTE, 18, label="Founder must be at least 18"),
            Rule(
                "startup.incorporation_age_years", Op.LTE, 1, label="For new units only (≤ 1 year)"
            ),
        ),
        benefits=(
            "A subsidy of 15–35% of the project cost (35% for special categories in rural areas)"
            " on projects up to ₹50 lakh in manufacturing or ₹20 lakh in services; a bank lends"
            " the rest after your own 5–10%."
        ),
        source_url="https://www.kviconline.gov.in/pmegpeportal/",
        last_verified=_CHECKED,
    ),
    Scheme(
        id="mudra",
        name="Pradhan Mantri MUDRA Yojana (PMMY)",
        type=SchemeType.LOAN,
        agency="MUDRA / SIDBI",
        level="bank",
        min_funding=0,
        max_funding=1_000_000,  # for a first loan; Tarun Plus (₹20L) needs a repaid Tarun loan
        sectors=[],
        eligibility=_all(
            Rule(
                "startup.annual_revenue",
                Op.LTE,
                100_000_000,
                label="For micro enterprises (turnover up to ₹10 crore)",
            ),
        ),
        benefits=(
            "A collateral-free loan for a non-farm business: Shishu up to ₹50,000, Kishore up to"
            " ₹5 lakh, Tarun up to ₹10 lakh; Tarun Plus, up to ₹20 lakh, only after repaying a"
            " Tarun loan."
        ),
        source_url="https://www.mudra.org.in/",
        last_verified=_CHECKED,
        unmodelled_notes=["Not open to anyone in default with a bank or lender."],
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
        benefits=(
            "A composite loan (term loan and working capital) of ₹10 lakh to ₹1 crore, without"
            " collateral, for a first-time (greenfield) business."
        ),
        source_url="https://www.standupmitra.in/",
        last_verified=_CHECKED,
        unmodelled_notes=[
            "Extended to FY 2025; confirm on standupmitra.in or with your bank that it is open.",
            "In a company or firm, SC/ST or women founders must hold at least 51%.",
        ],
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
            Rule(
                "founder.age",
                Op.BETWEEN,
                [21, 45],
                label="Founder aged 21–45 (some sources: 21–35 for the general category)",
            ),
            Rule("founder.first_graduate", Op.IS_TRUE, label="For first-generation entrepreneurs"),
        ),
        benefits=(
            "A 25% capital subsidy (up to ₹75 lakh; 10% more for SC/ST and differently-abled"
            " founders) on projects up to ₹5 crore, a 3% interest subvention, and"
            " entrepreneurship training."
        ),
        source_url="https://www.msmeonline.tn.gov.in/",
        last_verified=_CHECKED,
    ),
    Scheme(
        id="uyegp",
        name="Unemployed Youth Employment Generation Programme (UYEGP)",
        type=SchemeType.SUBSIDY,
        agency="MSME Tamil Nadu",
        level="state",
        min_funding=0,
        max_funding=375_000,
        sectors=[],
        eligibility=_all(
            Rule("founder.state", Op.EQ, "Tamil Nadu", label="Founder must be in Tamil Nadu"),
            Rule(
                "founder.age",
                Op.BETWEEN,
                [18, 45],
                label="Founder aged 18–45 (18–35 for the general category)",
            ),
        ),
        benefits=(
            "A 25% subsidy on projects up to ₹15 lakh in manufacturing or ₹5 lakh in services"
            " and business, capped at about ₹3.75 lakh (published figures differ; confirm with"
            " your District Industries Centre)."
        ),
        source_url="https://www.msmeonline.tn.gov.in/",
        last_verified=_CHECKED,
        unmodelled_notes=[
            "Family income up to ₹5 lakh a year.",
            "At least 8th standard, and 3 years' residence in Tamil Nadu.",
            "Entrepreneurship training (EDP) is required.",
        ],
    ),
    Scheme(
        id="cgtmse",
        name="Credit Guarantee Fund for Micro & Small Enterprises (CGTMSE)",
        type=SchemeType.GUARANTEE,
        agency="CGTMSE",
        level="bank",
        min_funding=0,
        max_funding=100_000_000,
        sectors=[],
        eligibility=_all(
            Rule(
                "startup.annual_revenue",
                Op.LTE,
                500_000_000,
                label="Micro & small enterprises only",
            ),
        ),
        benefits=(
            "A guarantee (75–85% of the loan) that lets a bank lend without collateral to micro"
            " and small enterprises, up to ₹10 crore since 1 April 2025. The lender pays the"
            " fee, though some pass it on."
        ),
        source_url="https://www.cgtmse.in/",
        last_verified=_CHECKED,
        unmodelled_notes=["Udyam registration is required."],
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
