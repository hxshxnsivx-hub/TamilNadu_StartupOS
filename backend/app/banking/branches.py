"""Branch index — which bank branches are near a founder's pin code, and how far by road.

Built offline by scripts/build_branch_index.py from the RBI-sourced IFSC
master. A branch sits at its pin code's centroid, or, when its RBI address has
no pin, at its neighbourhood's location. The founder's own location is their
pin code's centroid: Vanigam needs only the pin, never the full address.

Road travel time comes from scripts/build_travel_times.py, which runs Dijkstra
over an OpenStreetMap road graph from every pin and stores minutes and road km
per nearby branch. Lookups here are instant. Where a pair has no road time
(outside the precomputed radius, or a district not yet built), an estimate is
used instead and labelled as such; its constants are the medians measured on
the Coimbatore road network.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.banking.models import Branch

DATA = Path(__file__).parent / "data" / "branches_tn5.json"
TRAVEL = Path(__file__).parent / "data" / "travel_tn5.json"

# Measured on the Coimbatore road graph: road distance ≈ 1.34 × straight line,
# average free-flow speed ≈ 34 km/h.
DETOUR_FACTOR = 1.34
ESTIMATE_KMH = 34.0


@dataclass(frozen=True)
class Travel:
    minutes: float
    road_km: float
    basis: str  # "road_network" | "estimate"


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


class BranchIndex:
    def __init__(
        self,
        pins: dict[str, list[float]],
        branches: list[dict],
        travel: dict[str, dict[str, list[float]]] | None = None,
    ) -> None:
        self.pins = {p: (float(v[0]), float(v[1])) for p, v in pins.items() if v}
        fields = Branch.__dataclass_fields__
        self.branches = [Branch(**{k: v for k, v in b.items() if k in fields}) for b in branches]
        self.travel_table = travel or {}

    def travel(self, pin: str, b: Branch, straight_km: float) -> Travel:
        """Road travel from the pin's centre to the branch; estimated if not precomputed."""
        hit = self.travel_table.get(pin, {}).get(b.ifsc)
        if hit:
            return Travel(minutes=hit[0], road_km=hit[1], basis="road_network")
        road = straight_km * DETOUR_FACTOR
        return Travel(
            minutes=round(road / ESTIMATE_KMH * 60, 1), road_km=round(road, 2), basis="estimate"
        )

    def locate(self, pin: str) -> tuple[float, float] | None:
        return self.pins.get(pin)

    def position(self, b: Branch) -> tuple[float, float] | None:
        """A branch's own coordinates if it has them, else its pin's centroid."""
        if b.lat is not None and b.lon is not None:
            return (b.lat, b.lon)
        return self.pins.get(b.pin)

    def nearby(self, pin: str, radius_km: float = 10.0) -> list[tuple[Branch, float]]:
        """Branches within radius (straight line) of the pin's centre, quickest to reach first.

        Returns (branch, straight-line km) pairs ordered by road travel time.
        Returns [] when the pin is not in the index (outside the pilot
        districts, or never located).
        """
        origin = self.locate(pin)
        if origin is None:
            return []
        out = []
        for b in self.branches:
            loc = self.position(b)
            if loc is None:
                continue
            km = round(haversine_km(origin, loc), 1)
            if km <= radius_km:
                out.append((b, km))
        out.sort(key=lambda t: (self.travel(pin, t[0], t[1]).minutes, t[1], t[0].bank))
        return out


@lru_cache
def get_branch_index() -> BranchIndex:
    if not DATA.exists():
        return BranchIndex({}, [])
    raw = json.loads(DATA.read_text(encoding="utf8"))
    travel = json.loads(TRAVEL.read_text(encoding="utf8"))["pins"] if TRAVEL.exists() else {}
    return BranchIndex(raw["pins"], raw["branches"], travel)
