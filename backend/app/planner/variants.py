"""Product variants — the ideation half of a domain pack.

From a founder's flavour or model names ("mint lemon", "mint hibiscus") this
finds the pack's starting recipes, says what each variant legally is (a tea, or
an herbal infusion), and looks across the line for two things a founder rarely
sees at the start:

  shared ingredients  bought once for several variants — where the cost comes down
  free extensions     recipes in the pack that need NO ingredient the line does
                      not already buy: new products at no extra sourcing
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.planner.packs import Pack


@dataclass
class Variant:
    key: str
    label: str
    grams: dict[str, float]  # ingredient -> grams per 100 g
    is_tea: bool  # contains tea leaf
    caffeine: bool
    kind: str  # "tea" | "herbal infusion"
    lighter_option: dict | None = None


def _norm(s: str) -> str:
    return "_".join(sorted(re.findall(r"[a-z]+", s.lower().replace("tea", ""))))


def _variant(pack: Pack, key: str) -> Variant:
    r = pack.recipes[key]
    ing = {k: pack.ingredients[k] for k in r["grams_per_100"]}
    is_tea = any(i.get("is_tea") for i in ing.values())
    return Variant(
        key=key,
        label=r["label"],
        grams=r["grams_per_100"],
        is_tea=is_tea,
        caffeine=any(i.get("caffeine") for i in ing.values()),
        kind="tea" if is_tea else "herbal infusion",
        lighter_option=r.get("lighter_option"),
    )


def resolve(pack: Pack, requested: list[str] | None) -> tuple[list[Variant], list[str]]:
    """Variants for the requested names (word order ignored), and names with no recipe."""
    if not pack.recipes:
        return [], list(requested or [])
    if not requested:
        return [_variant(pack, k) for k in pack.recipes], []
    index = {_norm(k): k for k in pack.recipes}
    index.update({_norm(r["label"]): k for k, r in pack.recipes.items()})
    found, unknown = [], []
    for name in requested:
        key = index.get(_norm(name))
        if key and key not in {v.key for v in found}:
            found.append(_variant(pack, key))
        elif not key:
            unknown.append(name)
    return found, unknown


def shared_ingredients(pack: Pack, variants: list[Variant]) -> list[dict]:
    used: dict[str, list[str]] = {}
    for v in variants:
        for ing in v.grams:
            used.setdefault(ing, []).append(v.label)
    rows = [
        {"ingredient": pack.ingredients[k]["label"], "key": k, "used_in": vs, "count": len(vs)}
        for k, vs in used.items()
    ]
    return sorted(rows, key=lambda r: (-r["count"], r["ingredient"]))


def free_extensions(pack: Pack, variants: list[Variant]) -> list[dict]:
    """Pack recipes the line could add without buying a single new ingredient."""
    bought = {ing for v in variants for ing in v.grams}
    chosen = {v.key for v in variants}
    out = []
    for key, r in pack.recipes.items():
        if key in chosen:
            continue
        needs = set(r["grams_per_100"])
        if needs <= bought:
            out.append({"key": key, "label": r["label"], "uses": sorted(needs)})
    return out
