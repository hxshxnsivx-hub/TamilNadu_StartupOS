"""Rail router — decide how a founder should go for a loan before choosing a bank.

Three rails:
  * online         — founders with GST and banking history share data by
                     consent and receive offers (ULI, OCEN, PSB Loans in 59
                     Minutes, bank digital loans). Location barely matters.
  * branch_scheme  — subsidy loans (NEEDS, UYEGP, AABCS, KKT, PMEGP) sponsored
                     by the DIC to a specific branch. Location decides.
  * fast_priced    — fintech and bank unsecured loans when speed beats cost.

Subsidy comes first: when a founder qualifies for one, part of the loan is
written off, which no bank rate can beat. Every decision carries the question
and answer that produced it, so the founder can see why.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.banking.models import COLLATERAL_FREE_LIMIT_LAKH, LoanNeed

GST_MONTHS_FOR_ONLINE = 6


@dataclass
class Step:
    question: str
    answer: str


@dataclass
class RailDecision:
    primary: str
    also: list[str]
    collateral_route: str
    guarantee_options: list[str]
    steps: list[Step] = field(default_factory=list)


def decide(need: LoanNeed) -> RailDecision:
    steps: list[Step] = []
    has_records = need.gst_registered and need.gst_months >= GST_MONTHS_FOR_ONLINE
    steps.append(
        Step(
            f"Do you have {GST_MONTHS_FOR_ONLINE}+ months of GST returns?",
            (
                "Yes: online lenders can assess you from your data"
                if has_records
                else "No: online data-based offers are unlikely yet"
            ),
        )
    )

    if need.qualifies_for_subsidy:
        primary = "branch_scheme"
        steps.append(
            Step("Do you qualify for a subsidy scheme?", "Yes: a subsidy loan comes first")
        )
    elif has_records:
        primary = "online"
        steps.append(
            Step(
                "Do you qualify for a subsidy scheme?",
                "No or not known: start with online offers",
            )
        )
    else:
        primary = "branch_scheme"
        steps.append(
            Step(
                "Do you qualify for a subsidy scheme?",
                "No or not known: a branch loan such as MUDRA or a bank MSE loan",
            )
        )

    also: list[str] = []
    if has_records and primary != "online":
        also.append("online")

    guarantees: list[str] = []
    if need.amount_lakh <= COLLATERAL_FREE_LIMIT_LAKH:
        collateral = "none_by_rbi_rule"
        steps.append(
            Step(
                f"Is the amount ₹{COLLATERAL_FREE_LIMIT_LAKH:g}L or less?",
                "Yes: no collateral for micro and small enterprises (RBI, from 1 Apr 2026)",
            )
        )
    else:
        guarantees.append("CGTMSE")
        if need.dpiit:
            guarantees.append("CGSS")
        if need.purpose == "tl":
            guarantees.append("MCGS-MSME")
        if need.amount_lakh <= 200:
            guarantees.append("TNCGS")
        collateral = "guarantee" if guarantees else "security"
        if need.can_offer_collateral:
            collateral = "guarantee_or_security"
        steps.append(
            Step(
                f"Is the amount ₹{COLLATERAL_FREE_LIMIT_LAKH:g}L or less?",
                "No: ask the bank to cover the loan with " + ", ".join(guarantees),
            )
        )

    if need.needs_within_week:
        also.append("fast_priced")
        steps.append(
            Step(
                "Do you need the money within a week?",
                "Yes: fast lenders are an option, at higher interest; compare the cost",
            )
        )

    return RailDecision(
        primary=primary,
        also=also,
        collateral_route=collateral,
        guarantee_options=guarantees,
        steps=steps,
    )
