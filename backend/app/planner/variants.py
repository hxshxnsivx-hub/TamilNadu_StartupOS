"""Product variants — the ideation half of a domain pack.

A variant is one recipe (food: grams per 100 g) or one bill of materials
(hardware: quantity per unit). From a founder's variant names this finds the
pack's starting recipes, says what kind each variant is (rules in the pack,
from flags on its inputs: a blend with no tea leaf is an herbal infusion; a
controller with a GSM module is a connected product), and looks across the
line for two things a founder rarely sees at the start:

  shared inputs     bought once for several variants — where the cost comes down
  free extensions   recipes in the pack that need NO input the line does not
                    already buy: new products at no extra sourcing
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.planner.packs import Pack


@dataclass
class Variant:
    key: str
    label: str
    basis: str  # "grams_per_100" | "bom"
    items: dict[str, float]  # input -> grams per 100 g, or quantity per unit
    kind: str
    flags: dict[str, bool] = field(default_factory=dict)  # any input carries the flag
    cheaper_option: dict | None = None


def _norm(s: str, drop: tuple[str, ...]) -> str:
    low = s.lower().replace("_", " ")  # "jasmine_tea" is two words, like the recipe key
    for w in drop:
        low = re.sub(rf"\b{re.escape(w)}\b", " ", low)
    return "_".join(sorted(re.findall(r"[a-z]+", low)))


def items_of(recipe: dict) -> tuple[str, dict[str, float]]:
    if "bom" in recipe:
        return "bom", recipe["bom"]
    return "grams_per_100", recipe["grams_per_100"]


def _variant(pack: Pack, key: str) -> Variant:
    r = pack.recipes[key]
    basis, items = items_of(r)
    inputs = [pack.ingredients[k] for k in items]
    flags = sorted({f for i in inputs for f, v in i.items() if isinstance(v, bool)})
    any_flag = {f: any(i.get(f) for i in inputs) for f in flags}
    kind = pack.kinds.get("default", "")
    for rule in pack.kinds.get("rules", []):
        if any_flag.get(rule["if_any"]):
            kind = rule["label"]
            break
    return Variant(key, r["label"], basis, items, kind, any_flag, r.get("cheaper_option"))


def resolve(pack: Pack, requested: list[str] | None) -> tuple[list[Variant], list[str]]:
    """Variants for the requested names (word order ignored), and names with no recipe."""
    if not pack.recipes:
        return [], list(requested or [])
    if not requested:
        return [_variant(pack, k) for k in pack.recipes], []
    drop = tuple(pack.name_noise)
    index = {_norm(k.replace("_", " "), drop): k for k in pack.recipes}
    index.update({_norm(r["label"], drop): k for k, r in pack.recipes.items()})
    found, unknown = [], []
    for name in requested:
        key = index.get(_norm(name, drop))
        if key and key not in {v.key for v in found}:
            found.append(_variant(pack, key))
        elif not key:
            unknown.append(name)
    return found, unknown


def shared_ingredients(pack: Pack, variants: list[Variant]) -> list[dict]:
    used: dict[str, list[str]] = {}
    for v in variants:
        for k in v.items:
            used.setdefault(k, []).append(v.label)
    rows = [
        {"ingredient": pack.ingredients[k]["label"], "key": k, "used_in": vs, "count": len(vs)}
        for k, vs in used.items()
    ]
    return sorted(rows, key=lambda r: (-r["count"], r["ingredient"]))


def free_extensions(pack: Pack, variants: list[Variant]) -> list[dict]:
    """Pack recipes the line could add without buying a single new input."""
    bought = {k for v in variants for k in v.items}
    chosen = {v.key for v in variants}
    out = []
    for key, r in pack.recipes.items():
        if key in chosen:
            continue
        needs = set(items_of(r)[1])
        if needs <= bought:
            out.append({"key": key, "label": r["label"], "uses": sorted(needs)})
    return out
