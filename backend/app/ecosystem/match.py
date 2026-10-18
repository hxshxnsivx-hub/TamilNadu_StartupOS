"""Connect a founder to investors, peer startups and companies in their zone.

Investors: hard rules first, each refusal with a reason a founder can read —
not a startup investor, wrong instrument, wrong stage, sector outside the
thesis, cheque size far from the ask. The rest are ranked:

    fit = Σ weight × signal, over the signals known for that investor

    sector     0.35  thesis names the sector (1.0) or invests in any (0.6)
    stage      0.25  invests at the founder's stage
    ticket     0.15  stated cheque size covers the ask (only if both known)
    reachable  0.15  own site has a pitch route or an open call today (1.0),
                     is up but shows neither (0.5), was not readable (0.3)
    nearness   0.10  same city (1.0), elsewhere in Tamil Nadu (0.7)

A signal that is unknown is left out and the weights renormalised, and each
match lists what it was scored on.

Peers: startups in the founder's district sharing a sector — same zone first —
with whether they are hiring, the plainest public sign that a company is
scaling. Companies: the founder's zone and its sector mix (customers,
suppliers and partners cluster where a sector specialises).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.banking.branches import haversine_km
from app.core.stages import ROUND_FITS
from app.ecosystem.incubators import match_incubators
from app.ecosystem.index import Ecosystem
from app.ecosystem.taxonomy import SECTORS
from app.ecosystem.zones import Zone, nearest_zone

SIGNALS = Path(__file__).parent / "data" / "investor_signals.json"
CATALOGUE = Path(__file__).parents[1] / "schemes" / "data" / "funding_catalogue.json"

WEIGHTS = {"sector": 0.35, "stage": 0.25, "ticket": 0.15, "reachable": 0.15, "nearness": 0.10}
# Investor stages that can fund a founder raising each round (one shared table).
STAGE_OK = ROUND_FITS
TICKET_STRETCH = 1.5  # an ask up to 1.5× the stated cheque range still counts, at half weight
CITY = {"chennai": "chennai", "coimbatore": "coimbatore", "madurai": "madurai"}
STAGE_LABEL = {
    "pre_seed": "pre-seed",
    "seed": "seed",
    "pre_series_a": "pre-Series A",
    "early": "early stage",
    "series_a": "Series A",
    "growth": "growth",
}


@dataclass
class Founder:
    sectors: list[str]
    stage: str
    district: str
    pin: str | None = None
    ask_lakh: float | None = None
    instrument: str = "either"  # "equity" | "debt" | "either"
    dpiit: bool | None = None  # DPIIT startup recognition, if known
    company_age_years: float | None = None  # since incorporation, if known


@dataclass
class InvestorMatch:
    investor: dict
    fit: int
    signals: dict[str, float]
    reachability: dict
    why: list[str] = field(default_factory=list)


@dataclass
class InvestorRefusal:
    investor: dict
    reasons: list[str]


@dataclass
class ZoneView:
    zone: Zone
    km: float
    founder_sector_lq: dict[str, float]


@dataclass
class EcosystemMatch:
    zone: ZoneView | None
    sector_zones: list[tuple[Zone, float]]  # zones where the founder's sector clusters, by LQ
    investors: list[InvestorMatch]
    refused: list[InvestorRefusal]
    platforms: list[dict]
    peers: list[dict]
    companies: list[dict]
    company_counts: dict[str, int]
    incubators: list = field(default_factory=list)
    incubators_refused: list = field(default_factory=list)


@lru_cache
def load_signals() -> dict:
    return json.loads(SIGNALS.read_text(encoding="utf8")) if SIGNALS.exists() else {}


@lru_cache
def load_platforms() -> tuple[dict, ...]:
    """Investor platforms from the funding catalogue: one application, many investors."""
    if not CATALOGUE.exists():
        return ()
    rows = json.loads(CATALOGUE.read_text(encoding="utf8"))["schemes"]
    return tuple(
        r
        for r in rows
        if r.get("channel") == "investor"
        and r.get("instrument") == "platform"
        and r.get("status") == "active"
    )


def reachability(inv: dict, signals: dict) -> tuple[float, dict]:
    s = signals.get(inv["slug"])
    if not s or s.get("status") != "ok":
        status = s.get("status") if s else "not_checked"
        return 0.3, {"status": status, "pitch_url": None, "evidence": []}
    if s.get("pitch_url") or s.get("open_call"):
        return 1.0, {
            "status": "pitch_route" if s.get("pitch_url") else "open_call",
            "pitch_url": s.get("pitch_url"),
            "evidence": s.get("evidence", []),
            "checked": s.get("checked"),
        }
    return 0.5, {"status": "no_route_found", "pitch_url": None, "evidence": []}


def judge(inv: dict, f: Founder, signals: dict) -> InvestorMatch | InvestorRefusal:
    reasons: list[str] = []
    if not inv.get("serves_founders"):
        reasons.append(inv.get("not_for_founders_reason") or "Not a startup investor")
        return InvestorRefusal(inv, reasons)
    ins = inv.get("instrument")
    if f.instrument == "equity" and ins == "debt":
        reasons.append("Lends (debt), you asked for equity")
    if f.instrument == "debt" and ins == "equity":
        reasons.append("Takes equity, you asked for debt")
    stages = set(inv.get("stages") or [])
    wanted = STAGE_OK.get(f.stage, {f.stage})
    if stages and not stages & wanted:
        labels = ", ".join(STAGE_LABEL.get(s, s) for s in inv["stages"])
        reasons.append(f"Invests at {labels} — not {STAGE_LABEL.get(f.stage, f.stage)}")
    hit = [s for s in f.sectors if s in (inv.get("sectors") or [])]
    if not hit and not inv.get("generalist"):
        named = [SECTORS.get(s, s) for s in inv.get("sectors") or []]
        reasons.append("Invests in " + (", ".join(named) if named else "an unstated thesis"))
    ticket = inv.get("ticket_lakh")
    tk_signal = None
    if ticket and f.ask_lakh:
        lo, hi = ticket
        if lo <= f.ask_lakh <= hi:
            tk_signal = 1.0
        elif lo / TICKET_STRETCH <= f.ask_lakh <= hi * TICKET_STRETCH:
            tk_signal = 0.5
        else:
            reasons.append(f"Writes ₹{lo:g}–{hi:g}L cheques; you need ₹{f.ask_lakh:g}L")
    if reasons:
        return InvestorRefusal(inv, reasons)

    reach, reach_info = reachability(inv, signals)
    sig = {
        "sector": 1.0 if hit else 0.6,
        "stage": 1.0 if stages else None,
        "ticket": tk_signal,
        "reachable": reach,
        "nearness": 1.0 if (inv.get("city") or "").lower() == CITY.get(f.district) else 0.7,
    }
    known = {k: v for k, v in sig.items() if v is not None}
    total = sum(WEIGHTS[k] for k in known)
    fit = round(100 * sum(WEIGHTS[k] * v for k, v in known.items()) / total)
    why = []
    if hit:
        why.append("Thesis names " + ", ".join(SECTORS.get(s, s) for s in hit))
    else:
        why.append("Invests across sectors")
    if stages:
        why.append(f"Invests at {STAGE_LABEL.get(f.stage, f.stage)}")
    if tk_signal == 1.0:
        why.append("Cheque size covers your ask")
    if reach == 1.0:
        why.append("Takes pitches through its site now")
    if ins == "debt":
        why.append("Lends (debt), not equity")
    elif ins == "both":
        why.append("Offers equity and debt")
    return InvestorMatch(inv, fit, known, reach_info, why)


def _pin_xy(eco: Ecosystem, district: str, pin: str | None) -> tuple[float, float] | None:
    dz = eco.districts.get(district)
    p = dz.pins.get(pin) if dz and pin else None
    return (p.lat, p.lon) if p else None


def match(eco: Ecosystem, f: Founder, limit: int = 10) -> EcosystemMatch:
    signals = load_signals()
    judged = [judge(i, f, signals) for i in eco.investors]
    investors = sorted(
        (j for j in judged if isinstance(j, InvestorMatch)),
        key=lambda m: (-m.fit, m.investor["name"]),
    )
    refused = [j for j in judged if isinstance(j, InvestorRefusal)]

    dz = eco.districts.get(f.district)
    zone_view = None
    sector_zones: list[tuple[Zone, float]] = []
    if dz:
        hit = nearest_zone(dz, f.pin) if f.pin else None
        if hit:
            z, km = hit
            lq = {s: v for s, v in z.specialisations if s in f.sectors}
            zone_view = ZoneView(z, km, lq)
        for z in dz.zones:
            for s, v in z.specialisations:
                if s in f.sectors:
                    sector_zones.append((z, v))
        sector_zones.sort(key=lambda t: -t[1])

    here = _pin_xy(eco, f.district, f.pin)
    zone_pins = set(zone_view.zone.pins) if zone_view else set()
    peers = []
    for s in eco.startups:
        if s["district"] != f.district or not set(s.get("sectors") or []) & set(f.sectors):
            continue
        km = (
            round(haversine_km(here, (s["lat"], s["lon"])), 1)
            if here and s.get("lat") is not None
            else None
        )
        peers.append(
            {
                **s,
                "km": km,
                "same_zone": s.get("pin") in zone_pins,
                "hiring": bool(s.get("careers_url")),
            }
        )
    peers.sort(
        key=lambda s: (not s["same_zone"], s["km"] if s["km"] is not None else 999, s["name"] or "")
    )

    incubators, incubators_refused = match_incubators(f, limit)

    in_zone = [c for c in eco.companies if c["pin"] in zone_pins] if zone_pins else []
    same_sector = [c for c in in_zone if c.get("sector") in f.sectors]
    same_sector.sort(key=lambda c: (-(c.get("paidup_lakh") or 0), c["name"]))
    counts = {
        "zone_companies": len(in_zone),
        "zone_same_sector": len(same_sector),
        "district_same_sector": sum(
            1 for c in eco.companies if c["district"] == f.district and c.get("sector") in f.sectors
        ),
    }
    return EcosystemMatch(
        zone=zone_view,
        sector_zones=sector_zones,
        investors=investors[:limit],
        refused=refused,
        platforms=list(load_platforms()),
        peers=peers[:limit],
        companies=same_sector[:limit],
        company_counts=counts,
        incubators=incubators,
        incubators_refused=incubators_refused,
    )
