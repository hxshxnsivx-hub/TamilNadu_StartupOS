"""Splitting orders across suppliers (Req 3.3) and one-to-one pairing (Req 3.2, 5.4).

allocate: CP-SAT decides how many units each supplier provides for each line:

    for each line l and supplier s of the same category:
        x[l,s] units, y[l,s] in {0, 1} (supplier used for the line)
        min_order[s] * y <= x <= capacity[s] * y
    each line:      sum_s x[l,s] + short[l] = quantity[l];  at most K suppliers
    each supplier:  sum_l x[l,s] <= capacity[s]   (shared across lines)
    price:          a supplier above the line's budget is not used
    minimise        cost + distance penalty - trust bonus + a large penalty per short unit

Every unit that cannot be placed is reported with the reason (capacity,
minimum orders, budget), never silently dropped.

pair: NetworkX maximum-weight matching on the bipartite graph of demands and
suppliers, for one-to-one partnerships (co-development, exclusive vendors),
using the same 40/30/20/10 edge score as matching.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
from ortools.sat.python import cp_model

from app.b2b.matching import _geo, _price_fit, _trust_factor
from app.b2b.models import DemandRequest, SupplyProfile

SHORT_PENALTY = 10_000_000  # per unit: placing demand always beats leaving it unmet
FAR_PENALTY = 2  # ₹ per unit when the supplier is outside the buyer's district
TRUST_BONUS = 1  # ₹ per unit off for trusted suppliers (trust above 80)


@dataclass
class Line:
    id: str
    category: str
    quantity: int
    max_unit_price: float | None = None
    district: str | None = None


def allocate(
    lines: list[Line], suppliers: list[SupplyProfile], max_suppliers_per_line: int = 2
) -> dict:
    model = cp_model.CpModel()
    x: dict[tuple[str, str], cp_model.IntVar] = {}
    y: dict[tuple[str, str], cp_model.IntVar] = {}
    short: dict[str, cp_model.IntVar] = {}
    excluded: dict[str, list[str]] = {}
    cost_terms = []

    for ln in lines:
        short[ln.id] = model.NewIntVar(0, ln.quantity, f"short_{ln.id}")
        options = []
        for s in suppliers:
            if s.category != ln.category:
                continue
            if ln.max_unit_price is not None and s.unit_price > ln.max_unit_price:
                excluded.setdefault(ln.id, []).append(
                    f"{s.name} costs ₹{s.unit_price:g} a unit, above your ₹{ln.max_unit_price:g}"
                )
                continue
            key = (ln.id, s.id)
            x[key] = model.NewIntVar(0, min(ln.quantity, s.max_capacity), f"x_{ln.id}_{s.id}")
            y[key] = model.NewBoolVar(f"y_{ln.id}_{s.id}")
            model.Add(x[key] >= s.min_order * y[key])
            model.Add(x[key] <= s.max_capacity * y[key])
            unit = round(s.unit_price * 100)  # paise, so the objective stays integer
            if ln.district and s.district.lower() != ln.district.lower():
                unit += FAR_PENALTY * 100
            if _trust_factor(s.trust_score) > 1:
                unit -= TRUST_BONUS * 100
            cost_terms.append(unit * x[key])
            options.append(key)
        model.Add(sum(x[k] for k in options) + short[ln.id] == ln.quantity)
        model.Add(sum(y[k] for k in options) <= max_suppliers_per_line)

    for s in suppliers:
        used = [x[k] for k in x if k[1] == s.id]
        if used:
            model.Add(sum(used) <= s.max_capacity)

    model.Minimize(sum(cost_terms) + SHORT_PENALTY * sum(short.values()))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1  # same answer every run
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "lines": [], "total_cost": None}

    by_id = {s.id: s for s in suppliers}
    out_lines, total = [], 0.0
    for ln in lines:
        splits = []
        for (lid, sid), var in x.items():
            units = solver.Value(var)
            if lid == ln.id and units:
                s = by_id[sid]
                splits.append(
                    {
                        "supplier_id": sid,
                        "supplier": s.name,
                        "district": s.district,
                        "units": units,
                        "unit_price": s.unit_price,
                        "cost": round(units * s.unit_price, 2),
                        "trust": s.trust_score,
                    }
                )
                total += units * s.unit_price
        splits.sort(key=lambda r: -r["units"])
        unmet = solver.Value(short[ln.id])
        out_lines.append(
            {
                "line": ln.id,
                "category": ln.category,
                "quantity": ln.quantity,
                "splits": splits,
                "unmet": unmet,
                "why_unmet": _why_unmet(ln, suppliers, excluded.get(ln.id, []), unmet),
            }
        )
    return {
        "status": "optimal" if status == cp_model.OPTIMAL else "feasible",
        "lines": out_lines,
        "total_cost": round(total, 2),
        "rules": {
            "max_suppliers_per_line": max_suppliers_per_line,
            "far_penalty_per_unit": FAR_PENALTY,
            "trust_bonus_per_unit": TRUST_BONUS,
        },
    }


def _why_unmet(
    ln: Line, suppliers: list[SupplyProfile], excluded: list[str], unmet: int
) -> list[str]:
    if not unmet:
        return []
    same = [s for s in suppliers if s.category == ln.category]
    if not same:
        return [
            f"no supplier with known prices for '{ln.category}': use the directory to get quotes"
        ]
    reasons = list(excluded)
    affordable = [s for s in same if ln.max_unit_price is None or s.unit_price <= ln.max_unit_price]
    capacity = sum(s.max_capacity for s in affordable)
    if capacity < ln.quantity:
        reasons.append(f"suppliers within your budget can make {capacity:,} units a month in total")
    small = [s.name for s in affordable if s.min_order > ln.quantity]
    if small:
        reasons.append("minimum order above your quantity: " + ", ".join(small))
    return reasons or ["capacity is taken by your other lines"]


def pair(demands: list[DemandRequest], suppliers: list[SupplyProfile]) -> dict:
    """One supplier per demand and one demand per supplier, maximising total fit."""
    g = nx.Graph()
    for i, d in enumerate(demands):
        for s in suppliers:
            if s.category != d.category:
                continue
            price = _price_fit(d.budget_per_unit, s.unit_price)
            capacity = 100 if s.min_order <= d.quantity <= s.max_capacity else 40
            fit = (0.5 * price + 0.3 * capacity + 0.2 * _geo(d, s)) * _trust_factor(s.trust_score)
            score = min(100.0, fit)
            g.add_edge(("d", i), ("s", s.id), weight=round(score, 2))
    chosen = nx.max_weight_matching(g, maxcardinality=True)
    by_id = {s.id: s for s in suppliers}
    pairs = []
    for a, b in chosen:
        d_node, s_node = (a, b) if a[0] == "d" else (b, a)
        d, s = demands[d_node[1]], by_id[s_node[1]]
        pairs.append(
            {
                "demand": d_node[1],
                "category": d.category,
                "supplier_id": s.id,
                "supplier": s.name,
                "fit": g.edges[a, b]["weight"],
            }
        )
    pairs.sort(key=lambda p: p["demand"])
    unpaired = sorted(set(range(len(demands))) - {p["demand"] for p in pairs})
    return {"pairs": pairs, "unpaired": unpaired, "method": "maximum-weight bipartite matching"}
