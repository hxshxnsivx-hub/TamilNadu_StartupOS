"""Load the ecosystem data and build each district's hotspot zones once."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.banking.branches import get_branch_index
from app.ecosystem.zones import DistrictZones, PinActivity, build_district

DATA = Path(__file__).parent / "data" / "ecosystem_3d.json"


@dataclass
class Ecosystem:
    meta: dict
    districts: dict[str, DistrictZones]
    companies: list[dict]
    startups: list[dict]
    investors: list[dict]


def build(raw: dict, branch_pins: Counter) -> Ecosystem:
    by_pin: dict[str, PinActivity] = {}
    for pin, p in raw["pins"].items():
        by_pin[pin] = PinActivity(
            pin=pin,
            lat=p["lat"],
            lon=p["lon"],
            district=p["district"],
            name=p.get("name") or pin,
            layers={"companies": 0, "startups": 0, "branches": branch_pins.get(pin, 0)},
        )
    for c in raw["companies"]:
        if c["pin"] in by_pin:
            by_pin[c["pin"]].layers["companies"] += 1
            if c.get("sector"):
                by_pin[c["pin"]].sectors[c["sector"]] += 1
    for s in raw["startups"]:
        if s.get("pin") in by_pin:
            by_pin[s["pin"]].layers["startups"] += 1
            for sec in s.get("sectors") or []:
                by_pin[s["pin"]].sectors[sec] += 1
    districts = {}
    for did in raw["_meta"]["districts"]:
        districts[did] = build_district(did, [p for p in by_pin.values() if p.district == did])
    return Ecosystem(raw["_meta"], districts, raw["companies"], raw["startups"], raw["investors"])


@lru_cache
def get_ecosystem() -> Ecosystem | None:
    if not DATA.exists():
        return None
    raw = json.loads(DATA.read_text(encoding="utf8"))
    branch_pins = Counter(b.pin for b in get_branch_index().branches if b.pin)
    return build(raw, branch_pins)
