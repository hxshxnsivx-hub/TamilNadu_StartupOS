"""Domain models for bank loan routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Purpose = Literal["wc", "tl", "startup", "micro"]
Rail = Literal["online", "branch_scheme", "fast_priced"]

# RBI: no collateral for loans up to this amount to micro and small enterprises,
# for loans sanctioned or renewed on or after 1 April 2026 (was ₹10 lakh).
COLLATERAL_FREE_LIMIT_LAKH = 20.0


@dataclass(frozen=True)
class Requirements:
    gst: bool = False
    years_in_business: int = 0
    women_owned: bool = False
    dpiit: bool = False
    self_help_group: bool = False


@dataclass(frozen=True)
class BankScheme:
    id: str
    bank: str | None  # None = offered through many banks (government scheme or guarantee)
    name: str
    category: str
    min_lakh: float | None
    max_lakh: float | None
    purposes: tuple[str, ...]
    collateral: str
    pricing: str
    for_whom: str
    requires: Requirements
    sector: str | None
    status: str
    offered_by_types: tuple[str, ...] | None
    digital: bool
    details: tuple[str, ...]
    source_url: str
    confidence: str

    @property
    def is_guarantee(self) -> bool:
        return self.category == "guar"


@dataclass(frozen=True)
class Branch:
    ifsc: str
    bank: str
    bank_code: str
    type: str
    branch: str
    address: str
    district: str
    pin: str  # "" when neither the RBI address nor a post-office match gave one
    # Own coordinates when the branch was located by its neighbourhood name;
    # otherwise None and the branch sits at its pin code's centroid.
    lat: float | None = None
    lon: float | None = None
    # "pin": pin in the RBI address; "post_office": branch name matched a post
    # office in the same district, whose pin is used; "locality": neighbourhood
    # located on OpenStreetMap.
    located_by: str = "pin"


@dataclass
class LoanNeed:
    """What a founder tells Vanigam about the loan they need."""

    amount_lakh: float
    purpose: Purpose
    years_in_business: int = 0
    sector: str | None = None
    gst_registered: bool = False
    gst_months: int = 0
    women_owned: bool = False
    dpiit: bool = False
    can_offer_collateral: bool = False
    self_help_group: bool = False
    qualifies_for_subsidy: bool | None = None  # from the scheme engine, if known
    needs_within_week: bool = False


@dataclass
class SchemeMatch:
    scheme: BankScheme
    eligible: bool
    reasons: list[str] = field(default_factory=list)
