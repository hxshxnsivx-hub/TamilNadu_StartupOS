"""Investor–startup matching (Req 4.4 · design E6).

Each investor falls into one of three groups, never a hidden rejection:

* **eligible** — every *published* criterion the startup can be checked against
  passes;
* **check with investor** — nothing is violated, but the investor has not
  published a criterion we would need (stage, sector or ticket), so it cannot be
  ruled in or out from data alone (F-A4-019);
* **ineligible** — a published criterion is violated; the reasons cite only
  published criteria.

Readiness is **advice**, not a gate: a low readiness score no longer hides an
investor a founder is otherwise a fit for (F-A4-017). Eligible investors are
ranked by a fit score built from terms that actually vary between investors,
each carrying a short "why", with a stable tie-break. One startup vs. N
independent investors is per-investor evaluation — deterministic, no solver.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.vocab import ROUND_STAGES, Stage, to_round, to_stage
from app.funding.investors import ALL_SECTORS, Investor, real_investors
from app.funding.readiness import NOT_ENOUGH, _band


def _safe_stage(value: object) -> Stage | None:
    try:
        return to_stage(value)
    except ValueError:
        return None


def _accepted_stages(inv: Investor) -> set[Stage]:
    """Company stages an investor accepts, from its mixed stage/round labels.

    ``inv.stages`` holds both company-stage words ("mvp") and round words
    ("series_a"); each is mapped to the founder :class:`Stage` values it implies,
    so a revenue-stage founder matches a Series A investor (F-A4-015).
    """
    accepted: set[Stage] = set()
    for raw in inv.stages:
        if (st := _safe_stage(raw)) is not None:
            accepted.add(st)
            continue
        try:
            rd = to_round(raw)
        except ValueError:
            rd = None
        if rd is not None:
            accepted |= ROUND_STAGES[rd]
    return accepted


@dataclass
class EligibleInvestor:
    investor: Investor
    fit: int
    why: list[str] = field(default_factory=list)


@dataclass
class CheckWithInvestor:
    investor: Investor
    unknowns: list[str]  # published criteria that are missing, so we cannot judge


@dataclass
class IneligibleInvestor:
    investor: Investor
    reasons: list[str]


@dataclass
class InvestorMatchResult:
    eligible: list[EligibleInvestor]
    check_with: list[CheckWithInvestor]
    ineligible: list[IneligibleInvestor]
    readiness_advice: str = ""
    total_checked: int = field(default=0)


def _assess(inv: Investor, s: dict, funding_need: int) -> tuple[list[str], list[str]]:
    """Return (violations of published criteria, unpublished criteria)."""
    sector = s.get("sector")
    founder_stage = _safe_stage(s.get("stage"))
    users = float(s.get("users", 0) or 0)
    revenue = float(s.get("monthly_revenue", 0) or 0)

    if inv.availability == "not_investing":
        reason = inv.not_investing_reason or "Not currently investing"
        return [reason[:1].upper() + reason[1:]], []

    violations: list[str] = []
    unknowns: list[str] = []

    # Ticket: an unpublished range is simply not checked (not a refusal and not a
    # reason to send the founder away to ask) — only a published range can fail.
    if inv.ticket_known and not (inv.min_ticket <= funding_need <= inv.max_ticket):
        violations.append(
            f"Ticket size ₹{inv.min_ticket:,}–₹{inv.max_ticket:,} "
            f"doesn't fit your ₹{funding_need:,} need"
        )

    # Stage
    if not inv.stages:
        unknowns.append("Investment stage not published")
    elif founder_stage is not None and founder_stage not in _accepted_stages(inv):
        violations.append(f"Invests at {', '.join(inv.stages)} — not {founder_stage.value}")

    # Sector
    if not inv.sectors:
        unknowns.append("Sectors not published")
    elif sector and ALL_SECTORS not in inv.sectors and sector not in inv.sectors:
        violations.append(f"Focuses on {', '.join(inv.sectors)}")
    if sector and sector in inv.exclusions:
        violations.append(f"Excludes {sector}")

    # Published traction floors
    if users < inv.min_users:
        violations.append(f"Needs ≥ {inv.min_users:,} users")
    if revenue < inv.min_revenue:
        violations.append(f"Needs ≥ ₹{inv.min_revenue:,}/mo revenue")

    return violations, unknowns


def _ticket_fit(inv: Investor, funding_need: int) -> float:
    """1.0 when the need sits centrally in the range, tapering toward the edges."""
    if not inv.ticket_known or inv.max_ticket <= inv.min_ticket:
        return 0.7  # unpublished or a point ticket: neutral
    span = inv.max_ticket - inv.min_ticket
    pos = (funding_need - inv.min_ticket) / span  # 0 at floor, 1 at ceiling
    return max(0.0, 1.0 - 2 * abs(0.5 - pos))  # 1.0 centred, 0.0 at an edge


# Only terms that genuinely vary between investors (the old fit tied everyone on
# constant stage/geo/track contributions).
_FIT_WEIGHTS = {"sector": 0.30, "ticket": 0.20, "traction": 0.20, "track": 0.15, "geo": 0.15}


def _fit(inv: Investor, s: dict, funding_need: int) -> tuple[int, list[str]]:
    users = float(s.get("users", 0) or 0)
    revenue = float(s.get("monthly_revenue", 0) or 0)
    state = s.get("state")
    sector = s.get("sector")
    why: list[str] = []

    specialist = bool(sector) and ALL_SECTORS not in inv.sectors and sector in inv.sectors
    sector_fit = 1.0 if specialist else 0.7
    if specialist:
        why.append("Specialises in your sector")

    ticket = _ticket_fit(inv, funding_need)
    if inv.ticket_known and ticket >= 0.8:
        why.append("Your need sits well within their ticket range")

    # traction margin above the investor's *published* floors only
    if inv.min_users or inv.min_revenue:
        umarg = min(1.0, users / (inv.min_users * 2)) if inv.min_users else 1.0
        rmarg = min(1.0, revenue / (inv.min_revenue * 2)) if inv.min_revenue else 1.0
        traction = (umarg + rmarg) / 2
        if traction >= 0.75:
            why.append("Comfortably past their traction bar")
    else:
        traction = 0.6  # no published bar: neutral, not a free full mark

    track = (inv.track_record_score / 100) if inv.track_record_known else 0.6
    if inv.track_record_known and inv.track_record_score >= 75:
        why.append("Strong track record")

    geo = 1.0 if state and state in inv.geographies else 0.6
    if geo == 1.0:
        why.append("Invests in your state")

    score = (
        _FIT_WEIGHTS["sector"] * sector_fit
        + _FIT_WEIGHTS["ticket"] * ticket
        + _FIT_WEIGHTS["traction"] * traction
        + _FIT_WEIGHTS["track"] * track
        + _FIT_WEIGHTS["geo"] * geo
    )
    return int(round(100 * score)), why


def _readiness_advice(readiness: int) -> str:
    band = _band(readiness) if readiness > 0 else NOT_ENOUGH
    if band == NOT_ENOUGH:
        return "Answer a few readiness questions to see how investors may view you."
    tail = (
        "strengthen the weak dimensions before reaching out."
        if readiness < 60
        else "you present well; lead with your strongest dimensions."
    )
    return f"Your readiness is {readiness} ({band}) — {tail}"


def match_investors(
    startup: dict,
    funding_need: int,
    readiness_overall: int,
    investors: list[Investor] | None = None,
) -> InvestorMatchResult:
    investors = investors if investors is not None else list(real_investors())
    eligible: list[EligibleInvestor] = []
    check_with: list[CheckWithInvestor] = []
    ineligible: list[IneligibleInvestor] = []

    for inv in investors:
        violations, unknowns = _assess(inv, startup, funding_need)
        if violations:
            ineligible.append(IneligibleInvestor(inv, violations))
        elif unknowns:
            check_with.append(CheckWithInvestor(inv, unknowns))
        else:
            fit, why = _fit(inv, startup, funding_need)
            eligible.append(EligibleInvestor(inv, fit, why))

    # stable tie-break: fit desc, then investor id — never an order that depends
    # on constant fit terms or input order (F-A4-019).
    eligible.sort(key=lambda e: (-e.fit, e.investor.id))
    check_with.sort(key=lambda c: c.investor.id)
    return InvestorMatchResult(
        eligible=eligible,
        check_with=check_with,
        ineligible=ineligible,
        readiness_advice=_readiness_advice(readiness_overall),
        total_checked=len(investors),
    )
