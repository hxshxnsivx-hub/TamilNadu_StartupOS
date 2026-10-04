"""Cost sheet and price ladder per variant, and the levers that cut cost.

Per unit (a 100 g pack, a controller, a garment):
  inputs       food: Σ grams × raw-input yield factor × price per kg, scaled to the
               unit size;
               hardware: Σ quantity × price per part; plus wastage
  packaging    by format
  conversion   contract manufacturer's fee per unit, or own unit: variable cost
               per unit plus the monthly fixed cost spread over monthly volume
  overhead     a percentage of the above
  = cost of goods; ex-factory price at the target gross margin; distributor and
  retail prices by their margins (GST not included).

Every input can be overridden; anything left at the pack's example figure is
reported as such, because example prices are not market quotes.
"""

from __future__ import annotations

from app.planner.packs import Pack
from app.planner.variants import Variant, items_of


def _price(pack: Pack, key: str, yours: dict[str, float]) -> float:
    i = pack.ingredients[key]
    return float(yours.get(key, i.get("example_price_per_kg", i.get("example_price_per_unit", 0))))


def _input_cost(
    pack: Pack, basis: str, items: dict[str, float], yours: dict, unit_g: float
) -> float:
    if basis == "bom":
        return sum(q * _price(pack, k, yours) for k, q in items.items())
    # input_per_output: raw input per unit of finished weight (peel, moisture and trim
    # losses) — e.g. several kg of raw green banana for 1 kg of flour.
    return (
        sum(
            g * pack.ingredients[k].get("input_per_output", 1) / 1000 * _price(pack, k, yours)
            for k, g in items.items()
        )
        * unit_g
        / 100
    )


def cost_sheet(
    pack: Pack,
    variants: list[Variant],
    *,
    fmt: str | None = None,
    mode: str = "co_packer",
    monthly_packs: int | None = None,
    prices: dict[str, float] | None = None,
    overrides: dict | None = None,
) -> dict:
    c = {**pack.costing_defaults, **(overrides or {})}
    yours = prices or {}
    unit_label = c.get("unit_label", "unit")
    contract = c.get("contract_label", "contract manufacturer")
    example_used = sorted({k for v in variants for k in v.items if k not in yours})
    unit_g = float(c.get("unit_grams", 100))
    pk = c.get("packaging_per_unit", {"standard": 0})
    fmt = fmt if fmt in pk else next(iter(pk))
    packaging = float(pk[fmt])
    volume = max(1, int(monthly_packs)) if monthly_packs else None
    fee, var_cost = float(c["contract_fee_per_unit"]), float(c["own_variable_per_unit"])
    fixed_m = float(c["own_fixed_per_month"])
    conversion = var_cost + (fixed_m / volume if volume else 0.0) if mode == "own_unit" else fee
    markup = (1 + c["wastage_pct"] / 100) * (1 + c["overhead_pct"] / 100)

    rows = []
    for v in variants:
        inputs = _input_cost(pack, v.basis, v.items, yours, unit_g) * (1 + c["wastage_pct"] / 100)
        cogs = (inputs + packaging + conversion) * (1 + c["overhead_pct"] / 100)
        ex = cogs / (1 - c["gross_margin_pct"] / 100)
        dist = ex / (1 - c["distributor_margin_pct"] / 100)
        mrp = dist / (1 - c["retailer_margin_pct"] / 100)
        rows.append(
            {
                "variant": v.label,
                "key": v.key,
                "ingredients": round(inputs, 2),
                "packaging": round(packaging, 2),
                "conversion": round(conversion, 2),
                "cogs": round(cogs, 2),
                "ex_factory": round(ex, 2),
                "distributor": round(dist, 2),
                "retail_before_gst": round(mrp, 2),
                "ingredient_share_pct": round(100 * inputs / cogs),
            }
        )

    levers = []
    for v in variants:  # 1. a cheaper recipe or bill of materials
        alt = v.cheaper_option
        if not alt:
            continue
        basis, items = items_of(alt)
        now = _input_cost(pack, v.basis, v.items, yours, unit_g)
        cheaper = _input_cost(pack, basis, items, yours, unit_g)
        if cheaper < now:
            levers.append(
                {
                    "lever": f"{v.label}: {alt['note']}",
                    "saves_per_pack": round((now - cheaper) * markup, 2),
                    "trade_off": alt.get("trade_off", "test it with buyers before switching"),
                }
            )
    if fee > var_cost:  # 2. contract vs own unit
        breakeven = round(fixed_m / (fee - var_cost))
        levers.append(
            {
                "lever": f"Use a {contract} until volume passes the break-even, then your own unit",
                "breakeven_units_per_month": breakeven,
                "trade_off": (
                    f"below ~{breakeven:,} {unit_label}s a month a {contract} is cheaper; "
                    "above it, your own unit"
                ),
            }
        )
    cheapest_fmt = min(pk, key=pk.get)
    if fmt != cheapest_fmt and pk[fmt] > pk[cheapest_fmt]:  # 3. format
        levers.append(
            {
                "lever": c.get("format_lever", f"Lead with {cheapest_fmt.replace('_', ' ')}"),
                "saves_per_pack": round(
                    (pk[fmt] - pk[cheapest_fmt]) * (1 + c["overhead_pct"] / 100), 2
                ),
                "trade_off": "the dearer format may sell better in some channels",
            }
        )
    if rows:  # 4. outlier variants
        median = sorted(r["cogs"] for r in rows)[len(rows) // 2]
        for r in rows:
            if r["cogs"] > 1.5 * median:
                levers.append(
                    {
                        "lever": (
                            f"{r['variant']} costs {r['cogs'] / median:.1f}× the line's median"
                            " — price it as a premium or drop it"
                        ),
                        "trade_off": "a premium variant can lift the whole line's image",
                    }
                )

    turnover_lakh = None
    if volume and rows:
        avg_ex = sum(r["ex_factory"] for r in rows) / len(rows)
        turnover_lakh = round(volume * 12 * avg_ex / 1e5, 1)

    return {
        "format": fmt,
        "mode": mode,
        "unit": unit_label,
        "pack_grams": unit_g if any(v.basis == "grams_per_100" for v in variants) else None,
        "monthly_packs": volume,
        "packs_per_variant_per_month": (
            round(volume / len(variants)) if volume and variants else None
        ),
        "rows": rows,
        "levers": levers,
        "projected_turnover_lakh": turnover_lakh,
        "example_prices_used": example_used,
        "note": c.get("label", ""),
        "gst": "Prices exclude GST.",
    }


def fssai_tier(turnover_lakh: float | None) -> str:
    """FSSAI tier by annual turnover (verify on FoSCoS)."""
    if turnover_lakh is None:
        return "registration or licence"
    if turnover_lakh <= 12:
        return "basic registration"
    if turnover_lakh <= 2000:
        return "State licence"
    return "Central licence"
