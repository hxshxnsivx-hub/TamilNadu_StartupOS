"""Product decomposition → Supply Feasibility Map (Task 3.6 · v1.1 Req 3.6).

For founders who don't know their Bill of Materials: break a product into likely
component lines (deterministic template + keyword detection; an LLM enriches this
in production), then map each line to ranked suppliers via the matching engine and
flag gaps. Generated BOMs are drafts — the UI confirms them before matching.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.b2b.matching import match_demand
from app.b2b.models import DemandRequest, Match
from app.core.vocab import boundary_hits


@dataclass
class BOMLine:
    category: str
    spec: str
    qty_per_unit: float
    unit: str


@dataclass
class SupplyMapLine:
    line: BOMLine
    matches: list[Match]
    gap: bool  # True when no supplier serves this line


# keyword → BOM template. Cues are matched on word boundaries (so "iot" no longer
# matches inside "patriot" and "smart" cannot drag a saree into a PCB bill), and
# every matching template contributes, deduplicated by category (F-A4-011, F-B4-007).
_TEMPLATES: list[tuple[tuple[str, ...], list[BOMLine]]] = [
    (
        (
            "handloom",
            "saree",
            "textile",
            "apparel",
            "garment",
            "cloth",
            "weaving",
            "weave",
            "weaver",
            "fabric",
            "knitwear",
            "leather",
            "natural dye",
            "dyeing",
        ),
        [
            BOMLine("yarn", "cotton yarn", 0.4, "kg"),
            BOMLine("dye", "natural dye", 0.05, "kg"),
            BOMLine("printing", "label & tag printing", 1, "set"),
            BOMLine("packaging", "product packaging", 1, "unit"),
        ],
    ),
    (
        ("iot", "sensor", "device", "hardware", "electronics", "electronic"),
        [
            BOMLine("pcb", "2-layer PCB", 1, "board"),
            BOMLine("sensor", "sensor module", 2, "unit"),
            BOMLine("packaging", "enclosure & packaging", 1, "unit"),
        ],
    ),
    (
        ("pump", "motor", "machinery", "equipment"),
        [
            BOMLine("pump", "pump/motor unit", 1, "unit"),
            BOMLine("packaging", "crate packaging", 1, "unit"),
        ],
    ),
    (
        ("food", "snack", "beverage", "juice", "pickle", "spice", "packaged"),
        [
            BOMLine("packaging", "food-grade pouch", 1, "unit"),
            BOMLine("printing", "carton & label printing", 1, "set"),
        ],
    ),
]

# When nothing is recognised, say so honestly instead of inventing a packaging line.
_UNKNOWN = [BOMLine("unknown_product", "components not recognised — please list them", 1, "unit")]


def decompose(product: str) -> list[BOMLine]:
    lines: list[BOMLine] = []
    seen: set[str] = set()
    for cues, bom in _TEMPLATES:
        if any(boundary_hits(product, c) for c in cues):
            for b in bom:
                if b.category not in seen:
                    seen.add(b.category)
                    lines.append(BOMLine(**vars(b)))
    return lines or [BOMLine(**vars(b)) for b in _UNKNOWN]


async def build_supply_map(
    product: str,
    monthly_units: int = 1000,
    district: str = "",
    state: str = "Tamil Nadu",
    bom: list[BOMLine] | None = None,
) -> list[SupplyMapLine]:
    bom = bom if bom is not None else decompose(product)
    result: list[SupplyMapLine] = []
    for line in bom:
        demand = DemandRequest(
            category=line.category,
            spec=line.spec,
            quantity=max(1, round(line.qty_per_unit * monthly_units)),
            budget_per_unit=0,  # unknown at decomposition → price stays neutral
            district=district,
            state=state,
        )
        matches = await match_demand(demand)
        result.append(SupplyMapLine(line=line, matches=matches, gap=len(matches) == 0))
    return result
