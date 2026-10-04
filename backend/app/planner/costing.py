"""Cost sheet and price ladder per variant, and the levers that cut cost.

Per pack:
  ingredients  Σ grams × price/kg, scaled to the pack size, plus wastage
  packaging    by format (pouch, tea bags, iced)
  conversion   co-packer fee per pack, or own unit: variable cost per pack plus
               the monthly fixed cost spread over the monthly volume
  overhead     a percentage of the above
  = cost of goods; ex-factory price at the target gross margin; distributor and
  retail prices by their margins (GST not included).

Every input can be overridden; anything left at the pack's example figure is
reported as such, because example prices are not market quotes.
"""

from __future__ import annotations

from app.planner.packs import Pack
from app.planner.variants import Variant


def _ingredient_cost(grams: dict[str, float], prices: dict[str, float], pack_g: float) -> float:
    return sum(g / 1000 * prices[k] for k, g in grams.items()) * pack_g / 100


def cost_sheet(
    pack: Pack,
    variants: list[Variant],
    *,
    fmt: str = "loose_leaf",
    mode: str = "co_packer",
    monthly_packs: int | None = None,
    prices: dict[str, float] | None = None,
    overrides: dict | None = None,
) -> dict:
    c = {**pack.costing_defaults, **(overrides or {})}
    yours = prices or {}
    price = {k: float(yours.get(k, i["example_price_per_kg"])) for k, i in pack.ingredients.items()}
    example_used = sorted({k for v in variants for k in v.grams if k not in yours}, key=lambda k: k)
    pack_g = float(c["pack_grams"])
    packaging = float(
        c["packaging_per_pack"].get(fmt, next(iter(c["packaging_per_pack"].values())))
    )
    volume = max(1, int(monthly_packs or 0)) if monthly_packs else None
    per_variant_volume = (volume / len(variants)) if volume and variants else None

    if mode == "own_unit":
        fixed = float(c["own_unit_fixed_per_month"]) / volume if volume else None
        conversion = float(c["own_unit_variable_per_pack"]) + (fixed or 0.0)
    else:
        fixed = None
        conversion = float(c["co_packer_fee_per_pack"])

    rows = []
    for v in variants:
        ing = _ingredient_cost(v.grams, price, pack_g) * (1 + c["wastage_pct"] / 100)
        base = ing + packaging + conversion
        cogs = base * (1 + c["overhead_pct"] / 100)
        ex = cogs / (1 - c["gross_margin_pct"] / 100)
        dist = ex / (1 - c["distributor_margin_pct"] / 100)
        mrp = dist / (1 - c["retailer_margin_pct"] / 100)
        rows.append(
            {
                "variant": v.label,
                "key": v.key,
                "ingredients": round(ing, 2),
                "packaging": round(packaging, 2),
                "conversion": round(conversion, 2),
                "cogs": round(cogs, 2),
                "ex_factory": round(ex, 2),
                "distributor": round(dist, 2),
                "retail_before_gst": round(mrp, 2),
                "ingredient_share_pct": round(100 * ing / cogs),
            }
        )

    levers = []
    for v in variants:  # 1. lighter fruit recipes
        if v.lighter_option:
            now = _ingredient_cost(v.grams, price, pack_g)
            lighter = _ingredient_cost(v.lighter_option["grams_per_100"], price, pack_g)
            if lighter < now:
                levers.append(
                    {
                        "lever": f"{v.label}: {v.lighter_option['note']}",
                        "saves_per_pack": round(
                            (now - lighter)
                            * (1 + c["wastage_pct"] / 100)
                            * (1 + c["overhead_pct"] / 100),
                            2,
                        ),
                        "trade_off": (
                            "test in the taste panel; fruit pieces are also what buyers see"
                        ),
                    }
                )
    fee, var_cost, fixed_m = (
        float(c["co_packer_fee_per_pack"]),
        float(c["own_unit_variable_per_pack"]),
        float(c["own_unit_fixed_per_month"]),
    )
    if fee > var_cost:  # 2. co-packer vs own unit break-even
        breakeven = round(fixed_m / (fee - var_cost))
        levers.append(
            {
                "lever": "Co-packer until volume passes the break-even, then your own unit",
                "breakeven_packs_per_month": breakeven,
                "trade_off": (
                    f"below ~{breakeven:,} packs a month a co-packer is cheaper; "
                    "above it, your own unit"
                ),
            }
        )
    pk = c["packaging_per_pack"]  # 3. format
    if fmt != "loose_leaf" and "loose_leaf" in pk and pk[fmt] > pk["loose_leaf"]:
        levers.append(
            {
                "lever": "Lead with loose-leaf pouches; add tea bags once a flavour sells",
                "saves_per_pack": round(
                    (pk[fmt] - pk["loose_leaf"]) * (1 + c["overhead_pct"] / 100), 2
                ),
                "trade_off": "tea bags sell better in some channels",
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
                        "trade_off": "a premium flavour can lift the whole line's image",
                    }
                )

    turnover_lakh = None
    if volume and rows:
        avg_ex = sum(r["ex_factory"] for r in rows) / len(rows)
        turnover_lakh = round(volume * 12 * avg_ex / 1e5, 1)

    return {
        "format": fmt,
        "mode": mode,
        "pack_grams": pack_g,
        "monthly_packs": volume,
        "packs_per_variant_per_month": round(per_variant_volume) if per_variant_volume else None,
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
