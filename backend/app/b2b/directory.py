"""Real suppliers to ask for quotes: Tamil Nadu companies by what they make.

The seed catalogue has prices and capacities but only a handful of suppliers.
The MCA company master data (ecosystem layer) has thousands of real companies
with their NIC 2004 activity code, PIN and paid-up capital, but no prices. This
module maps a bill-of-materials category to activity codes and returns the
nearest matching companies, so a founder knows whom to ask.

Every row says where it comes from: registry data from 2020 can be out of date,
and an activity code says what a company registered to do, not what it sells
today. Verify before ordering.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache

from app.ecosystem.index import DATA as ECO_DATA
from app.ecosystem.index import get_ecosystem

# BOM category -> NIC 2004 activity-code prefixes (more specific first).
CATEGORY_NIC: dict[str, tuple[str, ...]] = {
    "yarn": ("1711", "171"),
    "fabric": ("1711", "1712", "1730", "172"),
    "dye": ("1712", "2411", "2422"),
    "printing": ("2221", "2222", "222"),
    "packaging": ("2102", "2520", "2109"),
    "pcb": ("3210",),
    "electronics": ("3210", "3220", "3230", "32"),
    "sensor": ("3312", "3313", "3210"),
    "pump": ("2912",),
    "motor": ("3110",),
    "machinery": ("29",),
    "metal_parts": ("2899", "289", "28"),
    "plastic_parts": ("2520",),
    "chemicals": ("241", "242", "24"),
    "food_ingredients": ("15",),
    "garments": ("1810", "18"),
    "leather": ("191", "192", "19"),
    "furniture": ("3610", "36"),
}
WHOLESALE = ("51",)  # traders can supply most categories in small lots
SOURCE = "MCA company master data, Tamil Nadu (data.gov.in, 2020)"


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


@lru_cache
def _pins() -> dict[str, tuple[float, float]]:
    """PIN -> (lat, lon), from the ecosystem data file."""
    if not ECO_DATA.exists():
        return {}
    raw = json.loads(ECO_DATA.read_text(encoding="utf8"))
    return {p: (v["lat"], v["lon"]) for p, v in raw.get("pins", {}).items()}


def _size(paidup_lakh: float | None) -> str:
    p = paidup_lakh or 0
    if p >= 1000:
        return "large"
    if p >= 100:
        return "medium"
    return "small" if p > 0 else "unknown"


def suppliers_for(
    category: str,
    *,
    pin: str | None = None,
    district: str | None = None,
    limit: int = 10,
    include_traders: bool = True,
) -> dict:
    """The nearest real companies registered for this kind of supply."""
    prefixes = CATEGORY_NIC.get(category)
    if not prefixes:
        return {"category": category, "suppliers": [], "known": False,
                "note": f"No activity codes mapped for '{category}' yet."}  # fmt: skip
    eco = get_ecosystem()
    companies = eco.companies if eco else []
    here = _pins().get(pin or "")
    rows = []
    for c in companies:
        nic = str(c.get("nic") or "")
        rank = next((i for i, p in enumerate(prefixes) if nic.startswith(p)), None)
        trader = rank is None and include_traders and nic.startswith(WHOLESALE)
        if rank is None and not trader:
            continue
        there = _pins().get(str(c.get("pin") or ""))
        km = round(_km(here, there), 1) if here and there else None
        rows.append(
            {
                "name": c["name"],
                "cin": c.get("cin"),
                "district": c.get("district"),
                "pin": c.get("pin"),
                "activity_code": nic,
                "kind": "trader" if trader else "maker",
                "size": _size(c.get("paidup_lakh")),
                "registered_year": c.get("year"),
                "km": km,
                "_rank": 9 if trader else rank,
                "_same_district": bool(district and c.get("district") == district),
            }
        )
    rows.sort(
        key=lambda r: (
            r["_rank"],
            not r["_same_district"],
            r["km"] if r["km"] is not None else 9999,
            r["name"],
        )
    )
    out = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows[:limit]]
    return {
        "category": category,
        "known": True,
        "suppliers": out,
        "total": len(rows),
        "source": SOURCE,
        "note": (
            "Registered activity, not confirmed products or prices. Ask each for a quote"
            " and check the company is active before ordering."
        ),
    }
