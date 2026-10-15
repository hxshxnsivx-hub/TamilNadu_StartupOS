"""Bank scheme matching — which bank loan schemes fit a founder's need.

Same contract as the scheme eligibility engine: every scheme that does not
match carries at least one plain-language reason, so a refusal is always a
fix list. Guarantees (CGTMSE, CGSS, MCGS, TNCGS) are not loans; they are
returned separately as overlays that can sit on top of a matching loan.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.banking.catalogue import load_schemes
from app.banking.models import BankScheme, LoanNeed, SchemeMatch

PURPOSE_LABEL = {
    "wc": "working capital",
    "tl": "machinery, equipment or premises",
    "startup": "startup growth",
    "micro": "a small amount",
}


def _fmt(lakh: float) -> str:
    return f"₹{lakh / 100:g}Cr" if lakh >= 100 else f"₹{lakh:g}L"


def check(scheme: BankScheme, need: LoanNeed) -> SchemeMatch:
    why: list[str] = []
    req = scheme.requires
    if scheme.status != "active":
        why.append("Not open now")
    if need.purpose not in scheme.purposes:
        why.append(f"Does not fund {PURPOSE_LABEL[need.purpose]}")
    if scheme.max_lakh is not None and need.amount_lakh > scheme.max_lakh:
        why.append(f"Maximum is {_fmt(scheme.max_lakh)}")
    if scheme.min_lakh is not None and need.amount_lakh < scheme.min_lakh:
        why.append(f"Minimum is {_fmt(scheme.min_lakh)}")
    if req.gst and not need.gst_registered:
        why.append("Needs GST registration")
    if req.years_in_business > need.years_in_business:
        why.append(f"Needs {req.years_in_business}+ year(s) in business")
    if req.women_owned and not need.women_owned:
        why.append("Only for women-owned businesses (51%+)")
    if req.dpiit and not need.dpiit:
        why.append("Needs DPIIT startup recognition")
    if req.self_help_group and not need.self_help_group:
        why.append("Only for self-help groups")
    if scheme.collateral == "collateral" and not need.can_offer_collateral:
        why.append("Needs property or other security")
    if scheme.sector and scheme.sector != need.sector:
        why.append(f"Only for the {scheme.sector} sector")
    return SchemeMatch(scheme=scheme, eligible=not why, reasons=why)


@dataclass
class MatchResult:
    loans: list[SchemeMatch]
    guarantees: list[SchemeMatch]
    rejected: list[SchemeMatch]


def match(need: LoanNeed, schemes: tuple[BankScheme, ...] | None = None) -> MatchResult:
    schemes = schemes if schemes is not None else load_schemes()
    loans, guarantees, rejected = [], [], []
    for s in schemes:
        if s.collateral == "na":  # mentoring and other non-loan support
            continue
        m = check(s, need)
        if not m.eligible:
            rejected.append(m)
        elif s.is_guarantee:
            guarantees.append(m)
        else:
            loans.append(m)
    return MatchResult(loans=loans, guarantees=guarantees, rejected=rejected)
