"""Branch index — which bank branches are near a founder's pin code.

Built offline by scripts/build_branch_index.py from the RBI-sourced IFSC
master. Each branch is placed at its pin code's centroid, so distances are
approximate (±2–3 km) and straight-line, not road distance. The founder's own
location is likewise their pin code's centroid: Vanigam needs only the pin,
never the full address.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from app.banking.models import Branch

DATA = Path(__file__).parent / "data" / "branches_tn5.json"


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


class BranchIndex:
    def __init__(self, pins: dict[str, list[float]], branches: list[dict]) -> None:
        self.pins = {p: (float(v[0]), float(v[1])) for p, v in pins.items() if v}
        self.branches = [Branch(**{k: b[k] for k in Branch.__dataclass_fields__}) for b in branches]

    def locate(self, pin: str) -> tuple[float, float] | None:
        return self.pins.get(pin)

    def nearby(self, pin: str, radius_km: float = 10.0) -> list[tuple[Branch, float]]:
        """Branches within radius of the pin's centroid, nearest first.

        Returns [] when the pin is not in the index (outside the pilot
        districts, or never located).
        """
        origin = self.locate(pin)
        if origin is None:
            return []
        out = []
        for b in self.branches:
            loc = self.pins.get(b.pin)
            if loc is None:
                continue
            km = round(haversine_km(origin, loc), 1)
            if km <= radius_km:
                out.append((b, km))
        out.sort(key=lambda t: (t[1], t[0].bank, t[0].branch))
        return out


@lru_cache
def get_branch_index() -> BranchIndex:
    if not DATA.exists():
        return BranchIndex({}, [])
    raw = json.loads(DATA.read_text(encoding="utf8"))
    return BranchIndex(raw["pins"], raw["branches"])
