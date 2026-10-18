"""Investor–startup matching (Req 4.4 · design E6).

Hard constraints first (ticket, stage, sector, availability, traction thresholds,
exclusions, readiness gate) — every unmatched investor carries its violated
constraints. Eligible investors are then ranked by a weighted fit score. A single
startup vs. N independent investors is per-investor constraint evaluation, so this
is deterministic (no solver needed); CP-SAT is reserved for combinatorial cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.stages import Stage, parse_stage
from app.funding.investors import ALL_SECTORS, Investor, real_investors

_LATE_STAGES = {Stage.GROWTH, Stage.SCALE}
FIT_WEIGHTS = {"sector": 0.30, "stage": 0.25, "traction": 0.20, "geo": 0.15, "track": 0.10}


def readiness_gate(stage: str) -> int:
    return 70 if parse_stage(stage) in _LATE_STAGES else 60


@dataclass
class EligibleInvestor:
    investor: Investor
    fit: int


@dataclass
class IneligibleInvestor:
    investor: Investor
    reasons: list[str]


@dataclass
class InvestorMatchResult:
    eligible: list[EligibleInvestor]
    ineligible: list[IneligibleInvestor]
    total_checked: int = field(default=0)


def _violations(inv: Investor, s: dict, funding_need: int, readiness: int) -> list[str]:
    sector = s.get("sector")
    found = parse_stage(s.get("stage"))
    stage = found.value if found else s.get("stage")
    users = float(s.get("users", 0) or 0)
    revenue = float(s.get("monthly_revenue", 0) or 0)
    # geography is a soft ranking factor (see _fit), not a hard constraint
    reasons: list[str] = []
    if inv.availability == "not_investing" and inv.not_investing_reason:
        # the deciding reason; the rest would only be noise
        return [inv.not_investing_reason[:1].upper() + inv.not_investing_reason[1:]]

    if inv.ticket_known and not (inv.min_ticket <= funding_need <= inv.max_ticket):
        reasons.append(
            f"Ticket size ₹{inv.min_ticket:,}–₹{inv.max_ticket:,} "
            f"doesn't fit your ₹{funding_need:,} need"
        )
    if not inv.stages:
        reasons.append("Investment stage not published")
    elif stage not in inv.stages:
        reasons.append(f"Invests at {', '.join(inv.stages)} — not {stage}")
    if not inv.sectors:
        reasons.append("Sectors not published")
    elif ALL_SECTORS not in inv.sectors and sector not in inv.sectors:
        reasons.append(f"Focuses on {', '.join(inv.sectors)}")
    if sector in inv.exclusions:
        reasons.append(f"Excludes {sector}")
    if inv.availability == "not_investing":
        reasons.append(
            inv.not_investing_reason[:1].upper() + inv.not_investing_reason[1:]
            if inv.not_investing_reason
            else "Not currently investing"
        )
    if users < inv.min_users:
        reasons.append(f"Needs ≥ {inv.min_users:,} users")
    if revenue < inv.min_revenue:
        reasons.append(f"Needs ≥ ₹{inv.min_revenue:,}/mo revenue")
    if readiness < readiness_gate(stage or ""):
        reasons.append(f"Readiness must be ≥ {readiness_gate(stage or '')} for this stage")
    return reasons


def _fit(inv: Investor, s: dict) -> int:
    users = float(s.get("users", 0) or 0)
    revenue = float(s.get("monthly_revenue", 0) or 0)
    state = s.get("state")

    sector = 80 if ALL_SECTORS in inv.sectors else 100  # a specialist in your sector fits best
    stage = 100
    # traction margin above the investor's floor
    umarg = 1.0 if inv.min_users == 0 else min(1.0, users / max(1, inv.min_users * 2))
    rmarg = 1.0 if inv.min_revenue == 0 else min(1.0, revenue / max(1, inv.min_revenue * 2))
    traction = round(50 + 50 * (umarg + rmarg) / 2)
    geo = 100 if state in inv.geographies else 60
    track = inv.track_record_score

    return int(
        round(
            FIT_WEIGHTS["sector"] * sector
            + FIT_WEIGHTS["stage"] * stage
            + FIT_WEIGHTS["traction"] * traction
            + FIT_WEIGHTS["geo"] * geo
            + FIT_WEIGHTS["track"] * track
        )
    )


def match_investors(
    startup: dict,
    funding_need: int,
    readiness_overall: int,
    investors: list[Investor] | None = None,
) -> InvestorMatchResult:
    investors = investors if investors is not None else list(real_investors())
    eligible: list[EligibleInvestor] = []
    ineligible: list[IneligibleInvestor] = []

    for inv in investors:
        reasons = _violations(inv, startup, funding_need, readiness_overall)
        if reasons:
            ineligible.append(IneligibleInvestor(inv, reasons))
        else:
            eligible.append(EligibleInvestor(inv, _fit(inv, startup)))

    eligible.sort(key=lambda e: e.fit, reverse=True)
    return InvestorMatchResult(eligible, ineligible, total_checked=len(investors))
