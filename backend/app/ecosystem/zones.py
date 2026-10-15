"""Hotspot zones — cut each district into the places where business activity clusters.

1. Activity per pin code: an equal-weight index of the layers we have — MCA
   companies registered there, startups located there, bank branches there —
   each as log(1 + count) scaled to 0–1 within the district.
2. Hotspots: Getis-Ord Gi* over pin codes, neighbours = pins within the
   district's link distance: twice the median nearest-pin spacing among the
   more active half of its pins (rural pins would stretch it), kept within
   2.5–4 km. A pin with z ≥ HOT_Z sits in a statistically significant cluster
   of high activity (90% one-sided), not merely a busy pin among quiet ones.
3. Zones: Gi* is smooth, so peaks are found on raw activity instead. Every hot
   pin climbs to the most active hot pin within PEAK_FACTOR × link distance,
   until it reaches a local peak; each peak and the pins that climb to it form
   one zone. A large hot area so splits into several zones around its own
   centres instead of one blob. Zones are named after their peak pin's post
   office.
4. Profile: sector counts per zone and their location quotient against the
   district (LQ = zone share / district share). LQ ≥ 1.25 with enough firms
   marks what a zone specialises in.

Pins outside every hotspot still belong to the district; they are reported
with their nearest zone and the distance to it.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass, field

from app.banking.branches import haversine_km

HOT_Z = 1.645
MIN_LINK_KM = 2.5
MAX_LINK_KM = 4.0
PEAK_FACTOR = 0.75
SPECIALISE_LQ = 1.25
SPECIALISE_MIN = 10


@dataclass
class PinActivity:
    pin: str
    lat: float
    lon: float
    district: str
    name: str
    layers: dict[str, int]  # "companies" | "startups" | "branches" -> count
    sectors: Counter = field(default_factory=Counter)
    index: float = 0.0
    z: float = 0.0


@dataclass
class Zone:
    id: str
    district: str
    name: str
    peak_pin: str
    pins: list[str]
    lat: float
    lon: float
    peak_z: float
    layers: dict[str, int]
    sectors: dict[str, int]
    specialisations: list[tuple[str, float]]  # (sector, LQ), strongest first


@dataclass
class DistrictZones:
    district: str
    link_km: float
    zones: list[Zone]
    pins: dict[str, PinActivity]
    zone_of: dict[str, str]  # pin -> zone id, hot pins only


def _index(pins: list[PinActivity]) -> None:
    layers = sorted({k for p in pins for k in p.layers})
    tops = {k: max(math.log1p(p.layers.get(k, 0)) for p in pins) for k in layers}
    live = [k for k in layers if tops[k] > 0]
    for p in pins:
        p.index = (
            sum(math.log1p(p.layers.get(k, 0)) / tops[k] for k in live) / len(live) if live else 0
        )


def _link_km(pins: list[PinActivity]) -> float:
    active = sorted(pins, key=lambda p: -p.index)[: max(10, len(pins) // 2)]
    if len(active) < 2:
        return MIN_LINK_KM
    nn = [
        min(haversine_km((a.lat, a.lon), (b.lat, b.lon)) for b in active if b is not a)
        for a in active
    ]
    return min(MAX_LINK_KM, max(MIN_LINK_KM, 2 * statistics.median(nn)))


def _gi_star(pins: list[PinActivity], d: float) -> None:
    """Sets p.z: Getis-Ord Gi* with binary weights for pins within d (itself included)."""
    n = len(pins)
    xs = [p.index for p in pins]
    mean = sum(xs) / n
    s = math.sqrt(max(sum(x * x for x in xs) / n - mean * mean, 1e-12))
    for p in pins:
        near = [q for q in pins if haversine_km((p.lat, p.lon), (q.lat, q.lon)) <= d]
        w = len(near)  # binary weights, self included
        denom = s * math.sqrt(max((n * w - w * w) / (n - 1), 1e-12)) if n > 1 else 1
        p.z = (sum(q.index for q in near) - mean * w) / denom


def build_district(district: str, pins: list[PinActivity]) -> DistrictZones:
    by_pin = {p.pin: p for p in pins}
    if not pins:
        return DistrictZones(district, MIN_LINK_KM, [], {}, {})
    _index(pins)
    d = _link_km(pins)
    _gi_star(pins, d)
    hot = {p.pin for p in pins if p.z >= HOT_Z}
    reach = d * PEAK_FACTOR

    def climb(pin: str) -> str:
        while True:
            here = (by_pin[pin].lat, by_pin[pin].lon)
            near = [q for q in hot if haversine_km(here, (by_pin[q].lat, by_pin[q].lon)) <= reach]
            up = max(near, key=lambda q: (by_pin[q].index, q))
            if up == pin:
                return pin
            pin = up

    members: dict[str, list[str]] = {}
    for pin in sorted(hot):
        members.setdefault(climb(pin), []).append(pin)

    total = Counter()
    for p in pins:
        total.update(p.sectors)
    total_n = sum(total.values()) or 1

    zones, zone_of = [], {}
    ranked = sorted(members.items(), key=lambda kv: (-len(kv[1]), -by_pin[kv[0]].index))
    for i, (peak, ps) in enumerate(ranked, 1):
        zid = f"{district}-{i}"
        layers, sectors = Counter(), Counter()
        for q in ps:
            layers.update(by_pin[q].layers)
            sectors.update(by_pin[q].sectors)
            zone_of[q] = zid
        n = sum(sectors.values()) or 1
        lq = [
            (s, round((c / n) / (total[s] / total_n), 2))
            for s, c in sectors.items()
            if c >= SPECIALISE_MIN and total[s]
        ]
        spec = sorted((x for x in lq if x[1] >= SPECIALISE_LQ), key=lambda x: -x[1])
        zones.append(
            Zone(
                id=zid,
                district=district,
                name=by_pin[peak].name or peak,
                peak_pin=peak,
                pins=sorted(ps),
                lat=round(sum(by_pin[q].lat for q in ps) / len(ps), 5),
                lon=round(sum(by_pin[q].lon for q in ps) / len(ps), 5),
                peak_z=round(by_pin[peak].z, 2),
                layers=dict(layers),
                sectors=dict(sectors.most_common()),
                specialisations=spec,
            )
        )
    return DistrictZones(district, round(d, 2), zones, by_pin, zone_of)


def nearest_zone(dz: DistrictZones, pin: str) -> tuple[Zone, float] | None:
    """The pin's own zone (distance 0) or the closest zone centre."""
    if pin in dz.zone_of:
        return next(z for z in dz.zones if z.id == dz.zone_of[pin]), 0.0
    p = dz.pins.get(pin)
    if p is None or not dz.zones:
        return None
    z = min(dz.zones, key=lambda z: haversine_km((p.lat, p.lon), (z.lat, z.lon)))
    return z, round(haversine_km((p.lat, p.lon), (z.lat, z.lon)), 1)
