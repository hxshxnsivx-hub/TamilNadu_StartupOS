"""Match a founder to incubators — the first door for idea-to-MVP startups.

Hard rules first, each refusal with a reason a founder can read:
  stage    incubators take idea, prototype and MVP startups (a few take early
           revenue); Series A and growth companies are refused with that reason
  sector   the incubator's stated focus must include a founder sector, unless it
           takes technology startups broadly
  place    incubators in the founder's district, or a neighbouring one that serves
           it (Tiruppur's textile centre for Coimbatore, Kalasalingam for Madurai)

Then a fit score over the signals known for that incubator:

    sector      0.35  focus names the sector (1.0) or takes any tech startup (0.6)
    stage       0.20  takes the founder's stage
    nearness    0.20  1 − travel minutes / 90 (an estimate from pin centres:
                      straight line × 1.34 at 34 km/h); same district 1.0 and
                      neighbouring 0.5 when the founder gave no pin; 0.5 when the
                      incubator's campus pin is not known
    money       0.15  a programme run there can pay this founder (1.0), might
                      (0.6, founder must confirm eligibility), or the incubator
                      offers support only (0.4)
    confidence  0.10  official source 1.0, listing 0.7, to verify 0.4

Each programme is reported with whether it applies to this founder and why, and
with the scheme's current status from the funding catalogue where it is tracked
(SISFS is closed to new incubator calls at present, for example).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.banking.branches import DETOUR_FACTOR, ESTIMATE_KMH, get_branch_index, haversine_km
from app.ecosystem.taxonomy import SECTORS

DATA = Path(__file__).parent / "data" / "incubators.json"
CATALOGUE = Path(__file__).parents[1] / "schemes" / "data" / "funding_catalogue.json"

WEIGHTS = {"sector": 0.35, "stage": 0.20, "nearness": 0.20, "money": 0.15, "confidence": 0.10}
NEAR_MINUTES = 90.0  # incubation means regular visits; an hour and a half away scores zero
# Founder stage -> the incubator stage that takes it. None: past incubation.
STAGE_TO_INCUBATOR = {
    "idea": "pre_seed",
    "pre_seed": "pre_seed",
    "seed": "seed",
    "pre_series_a": "early",
    "series_a": None,
    "growth": None,
}
STAGE_LABEL = {"pre_seed": "idea and prototype", "seed": "MVP", "early": "early revenue"}
NEIGHBOURS = {"coimbatore": {"tiruppur"}, "madurai": {"virudhunagar"}, "chennai": set()}
CONFIDENCE = {"official": 1.0, "secondary": 0.7, "to_verify": 0.4}
# Programme -> funding-catalogue id, where the scheme's status is tracked.
CATALOGUE_ID = {"SISFS": "sisfs", "NIDHI-PRAYAS": "nidhi_prayas", "BioNEST": "birac_big"}
STATUS_TEXT = {
    "active": "open",
    "between_calls": "between calls",
    "closed": "closed to new applications",
    "cohort": "opens by cohort",
}
SISFS_MAX_AGE_YEARS = 2


@dataclass
class IncubatorMatch:
    incubator: dict
    fit: int
    signals: dict[str, float]
    programmes: list[dict]
    travel: dict | None
    why: list[str] = field(default_factory=list)


@dataclass
class IncubatorRefusal:
    incubator: dict
    reasons: list[str]


@lru_cache
def load_incubators() -> tuple[dict, ...]:
    if not DATA.exists():
        return ()
    return tuple(json.loads(DATA.read_text(encoding="utf8"))["incubators"])


@lru_cache
def scheme_status() -> dict[str, str]:
    if not CATALOGUE.exists():
        return {}
    rows = json.loads(CATALOGUE.read_text(encoding="utf8"))["schemes"]
    return {r["id"]: r["status"] for r in rows}


def programme_fit(prog: str, founder) -> dict:
    """Does money from this programme reach this founder now?

    applies: yes | check (founder must confirm eligibility) | closed (eligible, but the
    scheme takes no applications now) | no | support (incubation help, no set money).
    """
    fit = _programme_fit(prog, founder)
    if fit["applies"] in ("yes", "check") and fit.get("status") == STATUS_TEXT["closed"]:
        return {**fit, "applies": "closed", "reason": fit["reason"] + "; scheme closed now"}
    return fit


def _programme_fit(prog: str, founder) -> dict:
    secs = set(founder.sectors)
    status = scheme_status().get(CATALOGUE_ID.get(prog, ""), None)
    out = {"name": prog, "status": STATUS_TEXT.get(status, status) if status else None}
    if prog == "SISFS":
        if founder.dpiit is False:
            return {**out, "applies": "no", "reason": "Needs DPIIT startup recognition"}
        if (
            founder.company_age_years is not None
            and founder.company_age_years > SISFS_MAX_AGE_YEARS
        ):
            return {**out, "applies": "no", "reason": "Company must be under 2 years old"}
        if founder.dpiit and founder.company_age_years is not None:
            return {**out, "applies": "yes", "reason": "Up to ₹20L grant and ₹50L debt"}
        return {
            **out,
            "applies": "check",
            "reason": "Needs DPIIT recognition and a company under 2 years old",
        }
    if prog == "BioNEST":
        if secs & {"biotech_pharma", "healthtech"}:
            return {**out, "applies": "yes", "reason": "Bio-labs; route to BIRAC BIG (up to ₹50L)"}
        return {**out, "applies": "no", "reason": "For biotech and health ventures"}
    if prog in ("NABARD", "RKVY-RAFTAAR"):
        if secs & {"agritech", "food"}:
            return {**out, "applies": "yes", "reason": "Agri seed grants (up to ₹25L)"}
        return {**out, "applies": "no", "reason": "For agriculture and food ventures"}
    if prog in ("NIDHI-SSS", "NIDHI-PRAYAS"):
        return {
            **out,
            "applies": "check",
            "reason": "Science or technology product; selection by the TBI",
        }
    if prog == "TIDE 2.0":
        return {**out, "applies": "check", "reason": "ICT startups only"}
    return {**out, "applies": "support", "reason": "Incubation support; seed money varies"}


def _positions() -> dict[str, tuple[float, float]]:
    """Pin centres from the branch index and the ecosystem index."""
    from app.ecosystem.index import get_ecosystem  # late: index imports nothing from here

    pins = dict(get_branch_index().pins)
    eco = get_ecosystem()
    for dz in eco.districts.values() if eco else ():
        for p in dz.pins.values():
            pins.setdefault(p.pin, (p.lat, p.lon))
    return pins


def judge_incubator(inc: dict, founder, pins: dict) -> IncubatorMatch | IncubatorRefusal:
    reasons: list[str] = []
    district_ok = inc["district"] == founder.district or inc["district"] in NEIGHBOURS.get(
        founder.district, set()
    )
    if not district_ok:
        reasons.append(f"Serves {inc['district'].title()}, not {founder.district.title()}")
    want = STAGE_TO_INCUBATOR.get(founder.stage)
    if want is None:
        reasons.append("Incubators take idea-to-MVP startups; look at investors at your stage")
    elif want not in inc["stages"]:
        took = ", ".join(STAGE_LABEL.get(s, s) for s in inc["stages"])
        reasons.append(f"Takes {took} startups, not {STAGE_LABEL.get(want, want)}")
    general = "general" in inc["sectors"]
    hit = [s for s in founder.sectors if s in inc["sectors"]]
    if not hit and not general:
        named = ", ".join(SECTORS.get(s, s) for s in inc["sectors"])
        reasons.append(f"Focuses on {named}")
    if reasons:
        return IncubatorRefusal(inc, reasons)

    travel = None
    here, there = pins.get(founder.pin or ""), pins.get(inc.get("pin") or "")
    if here and there:
        km = haversine_km(here, there)
        road = km * DETOUR_FACTOR
        minutes = road / ESTIMATE_KMH * 60
        travel = {
            "km": round(km, 1),
            "road_km": round(road, 1),
            "minutes": round(minutes),
            "basis": "estimate",
        }
        nearness = max(0.0, 1 - minutes / NEAR_MINUTES)
    elif not founder.pin:
        nearness = 1.0 if inc["district"] == founder.district else 0.5
    else:
        # Campus pin not known: score as a neighbouring district would, so an unknown
        # distance never outranks a known short one.
        nearness = 0.5

    programmes = [programme_fit(p, founder) for p in inc["programmes"]]
    applies = {p["applies"] for p in programmes}
    money = 1.0 if "yes" in applies else 0.6 if "check" in applies else 0.4
    sig = {
        "sector": 1.0 if hit else 0.6,
        "stage": 1.0,
        "nearness": nearness,
        "money": money,
        "confidence": CONFIDENCE.get(inc.get("confidence"), 0.4),
    }
    known = {k: v for k, v in sig.items() if v is not None}
    total = sum(WEIGHTS[k] for k in known)
    fit = round(100 * sum(WEIGHTS[k] * v for k, v in known.items()) / total)

    why = []
    why.append(
        "Focus includes " + ", ".join(SECTORS.get(s, s) for s in hit)
        if hit
        else "Takes technology startups broadly"
    )
    if travel:
        why.append(f"About {travel['minutes']} min by road (estimate)")
    elif inc["district"] != founder.district:
        why.append(f"In neighbouring {inc['district'].title()}")
    elif founder.pin:
        why.append("Distance not known (campus pin missing)")
    for p in programmes:
        if p["applies"] == "yes":
            why.append(f"{p['name']}: {p['reason']}")
    return IncubatorMatch(inc, fit, known, programmes, travel, why)


def match_incubators(
    founder, limit: int = 10
) -> tuple[list[IncubatorMatch], list[IncubatorRefusal]]:
    pins = _positions()
    judged = [judge_incubator(i, founder, pins) for i in load_incubators()]
    ok = sorted(
        (j for j in judged if isinstance(j, IncubatorMatch)),
        key=lambda m: (-m.fit, m.travel["minutes"] if m.travel else 999, m.incubator["name"]),
    )
    # Incubators in other districts are not shown as refusals: they were never options.
    refused = [
        j
        for j in judged
        if isinstance(j, IncubatorRefusal) and not j.reasons[0].startswith("Serves ")
    ]
    return ok[:limit], refused
