"""Branch allocation — rank (scheme, branch) options for a founder's pin code.

    score = Σ weight × signal, over the signals we actually have

Designed signals and weights:
    track_record 0.35  branch's record on that scheme (bank-wise sanction data,
                       later Vanigam's own outcomes)
    value        0.20  how good the scheme is for this founder (subsidy,
                       no-collateral, guarantee)
    nearness     0.15  1 − road minutes / NEAR_MINUTES (road time from the
                       pin's centre; estimated where not precomputed)
    digital      0.15  can be applied for online (fewer visits)
    speed        0.15  measured days to sanction from past users

track_record and speed have no data yet. Rather than invent values, they are
left out and the remaining weights are renormalised; the response lists which
signals were used and which were missing, so the ranking is honest about
what it knows.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.banking.branches import BranchIndex, Travel, get_branch_index
from app.banking.matcher import MatchResult, match
from app.banking.models import BankScheme, Branch, LoanNeed
from app.banking.router import RailDecision, decide

WEIGHTS = {"track_record": 0.35, "value": 0.20, "nearness": 0.15, "digital": 0.15, "speed": 0.15}
VALUE = {
    "none_rbi": 0.9,
    "guarantee": 0.8,
    "group": 0.6,
    "hybrid": 0.6,
    "unsecured": 0.4,
    "collateral": 0.3,
}
# Public sector banks take in-principle applications through PSB Loans in 59
# Minutes, which saves a visit for founders who already file GST and ITR.
ONLINE_INTAKE_TYPES = {"public"}
# A branch this many minutes away by road scores zero on nearness.
NEAR_MINUTES = 40.0


@dataclass
class Option:
    scheme: BankScheme
    branch: Branch | None
    km: float | None
    travel: Travel | None
    channel: str  # "online" | "online_then_branch" | "branch"
    score: int
    signals: dict[str, float]


@dataclass
class Allocation:
    rail: RailDecision
    options: list[Option]
    guarantees: list[BankScheme]
    matched: MatchResult
    pin_located: bool
    signals_used: list[str]
    signals_missing: list[str]


def _value(s: BankScheme) -> float:
    v = VALUE.get(s.collateral, 0.5)
    if s.category == "gov":
        v = 1.0  # subsidy or state-backed scheme loan
    return v


def _channel(s: BankScheme, b: Branch | None, has_records: bool) -> str:
    if s.digital:
        return "online"
    if b is not None and b.type in ONLINE_INTAKE_TYPES and has_records:
        return "online_then_branch"
    return "branch"


def allocate(
    need: LoanNeed,
    pin: str,
    radius_km: float = 10.0,
    limit: int = 5,
    index: BranchIndex | None = None,
    result: MatchResult | None = None,
) -> Allocation:
    index = index or get_branch_index()
    result = result or match(need)
    rail = decide(need)
    has_records = need.gst_registered and need.gst_months >= 6

    near = index.nearby(pin, radius_km)
    # nearby() is ordered by road time, so the first branch of a bank is its quickest to reach.
    nearest_by_bank: dict[str, tuple[Branch, float]] = {}
    for b, km in near:
        nearest_by_bank.setdefault(b.bank, (b, km))
    nearest_by_type: dict[str, list[tuple[Branch, float]]] = {}
    for b, km in nearest_by_bank.values():
        nearest_by_type.setdefault(b.type, []).append((b, km))

    used = ["value", "nearness", "digital"]
    missing = ["track_record", "speed"]
    total = sum(WEIGHTS[k] for k in used)

    options: list[Option] = []
    for m in result.loans:
        s = m.scheme
        if s.bank:
            candidates = [nearest_by_bank[s.bank]] if s.bank in nearest_by_bank else [(None, None)]
        else:
            candidates = [
                bk for t in (s.offered_by_types or ()) for bk in nearest_by_type.get(t, [])
            ] or [(None, None)]
        for b, km in candidates:
            channel = _channel(s, b, has_records)
            trip = index.travel(pin, b, km) if b is not None else None
            sig = {
                "value": _value(s),
                "nearness": max(0.0, 1 - trip.minutes / NEAR_MINUTES) if trip else 0.0,
                "digital": 1.0 if channel != "branch" else 0.0,
            }
            score = round(100 * sum(WEIGHTS[k] * sig[k] for k in used) / total)
            options.append(Option(s, b, km, trip, channel, score, sig))

    options.sort(key=lambda o: (-o.score, o.travel.minutes if o.travel else 999, o.scheme.id))
    # One option per (scheme, bank): a founder needs a choice of banks, not ten
    # branches of the same one.
    seen: set[tuple[str, str]] = set()
    unique: list[Option] = []
    for o in options:
        key = (o.scheme.id, o.branch.bank if o.branch else "")
        if key not in seen:
            seen.add(key)
            unique.append(o)

    return Allocation(
        rail=rail,
        options=unique[:limit],
        guarantees=[g.scheme for g in result.guarantees],
        matched=result,
        pin_located=index.locate(pin) is not None,
        signals_used=used,
        signals_missing=missing,
    )
