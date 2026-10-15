"""Scheme eligibility engine — filter schemes for a profile, with reasons.

Soundness (design Correctness Property 1): a scheme is returned as *eligible* only
if it satisfies every encoded rule. Completeness (Property 2): every *ineligible*
scheme carries at least one specific violated rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.schemes.models import Scheme
from app.schemes.rules import evaluate
from app.schemes.seed import SEED_SCHEMES


@dataclass
class EligibleScheme:
    scheme: Scheme


@dataclass
class IneligibleScheme:
    scheme: Scheme
    reasons: list[str]


@dataclass
class EligibilityResult:
    eligible: list[Scheme]
    ineligible: list[IneligibleScheme]

    @property
    def total_checked(self) -> int:
        return len(self.eligible) + len(self.ineligible)


def compute_age(date_of_birth: str | None) -> int | None:
    if not date_of_birth:
        return None
    try:
        dob = date.fromisoformat(date_of_birth)
    except ValueError:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def normalise_profile(profile: dict) -> dict:
    """Derive convenience fields (e.g. founder.age from date_of_birth)."""
    p = {
        "founder": dict(profile.get("founder") or {}),
        "startup": dict(profile.get("startup") or {}),
    }
    if "age" not in p["founder"]:
        age = compute_age(p["founder"].get("date_of_birth"))
        if age is not None:
            p["founder"]["age"] = age
    return p


def check_eligibility(profile: dict, schemes: list[Scheme] | None = None) -> EligibilityResult:
    schemes = schemes if schemes is not None else SEED_SCHEMES
    p = normalise_profile(profile)
    eligible: list[Scheme] = []
    ineligible: list[IneligibleScheme] = []

    for scheme in schemes:
        result = evaluate(scheme.eligibility, p)
        if result.ok:
            eligible.append(scheme)
        else:
            ineligible.append(IneligibleScheme(scheme, result.reasons))

    return EligibilityResult(eligible=eligible, ineligible=ineligible)
