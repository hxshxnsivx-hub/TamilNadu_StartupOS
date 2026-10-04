"""One call from a founder's answers to a specific plan: variants, costs, roadmap.

Facts come from the elicitation slots (sector, product form, stage, capital,
funding route, district, experience, team) plus the domain pack's own answers
(flavours, format, production mode, channels, volume). What is still unknown is
returned as the next questions to ask, so ideation stays a conversation: the
plan sharpens with every answer instead of guessing.
"""

from __future__ import annotations

from typing import Any

from app.planner import registry
from app.planner.costing import cost_sheet, fssai_tier
from app.planner.packs import COMMON, Pack, detect_pack, load_packs
from app.planner.risks import by_phase
from app.planner.roadmap import build
from app.planner.variants import free_extensions, resolve, shared_ingredients


def _templates(pack: Pack | None) -> list:
    common = {t.id: t for t in load_packs()[COMMON].templates}
    if pack:
        for t in pack.templates:
            common[t.id] = t  # same id replaces the common template
    # fresh copies: applicability prunes depends_on in place
    from copy import deepcopy

    return deepcopy(list(common.values()))


def build_plan(
    text: str = "",
    slots: dict[str, Any] | None = None,
    *,
    domain: str | None = None,
    variants: list[str] | None = None,
    fmt: str | None = None,
    production_mode: str | None = None,
    channels: list[str] | None = None,
    monthly_packs: int | None = None,
    prices: dict[str, float] | None = None,
    costing: dict | None = None,
    confidence: float = 0.8,
) -> dict:
    slots = dict(slots or {})
    packs = load_packs()
    domains = registry.load()["domains"]
    # `domain` may name a registry domain or a deep pack; otherwise both are detected.
    reg = domains.get(domain) if domain else None
    if reg is None and not (domain and domain in packs):
        found = registry.detect_domain(text)
        reg = domains.get(found) if found else None
    pack_id = (reg or {}).get("pack") or (domain if domain in packs else None) or detect_pack(text)
    pack = packs.get(pack_id) if pack_id and pack_id != COMMON else None
    if reg is None and pack is not None:  # a pack's registry card names the pack
        reg = next((d for d in domains.values() if d.get("pack") == pack.id), None)

    answered = {
        "variants": variants,
        "format": fmt,
        "production_mode": production_mode,
        "channels": channels,
        "monthly_packs": monthly_packs,
    }
    next_questions = [
        q for q in (pack.questions if pack else []) if answered.get(q["slot"]) in (None, [], "")
    ]
    fmt = fmt or (next(iter(pack.formats)) if pack and pack.formats else "standard")
    production_mode = production_mode or "co_packer"

    chosen, unknown = resolve(pack, variants) if pack else ([], [])
    costs = None
    if pack and chosen:
        costs = cost_sheet(
            pack,
            chosen,
            fmt=fmt,
            mode=production_mode,
            monthly_packs=monthly_packs,
            prices=prices,
            overrides=costing,
        )

    ch = set(channels or [])
    district = (slots.get("district") or "").lower()
    turnover = costs["projected_turnover_lakh"] if costs else None
    facts = {
        **slots,
        "sector": slots.get("sector") or (pack.sector if pack else (reg or {}).get("sector")),
        "product_form": slots.get("product_form")
        or ("physical" if pack else ((reg or {}).get("forms") or [None])[0]),
        "has_regulatory": bool(reg and reg.get("regulatory") and not pack),
        "in_tamil_nadu": district not in ("outside_tn", "outside tamil nadu"),
        "sells_online": "online" in ch,
        "sells_retail": "retail" in ch,
        "sells_horeca": "horeca" in ch,
        # has_<flag>: some variant's inputs carry the flag; lacks_<flag>: some variant's do not
        **{f"has_{f}": True for v in chosen for f, on in v.flags.items() if on},
        **{f"lacks_{f}": True for v in chosen for f, on in v.flags.items() if not on},
        "production_mode": production_mode,
        "projected_turnover_lakh": turnover,
    }
    context = {
        "n_variants": len(chosen) or "the",
        "fssai_tier": fssai_tier(turnover),
        "format_label": (pack.formats if pack else {}).get(fmt, fmt.replace("_", " ").capitalize()),
        "regulatory_items": [
            f"{item['title']}: {item['text']}"
            + (" (confirm with the regulator)" if item["confidence"] == "to_verify" else "")
            for item in (registry.card(reg)["regulatory_items"] if reg else [])
        ],
    }
    road = build(_templates(pack), facts, context, confidence)
    risks = by_phase(reg, facts) if reg else {}

    district_id = district if district in registry.DISTRICTS else None
    return {
        "domain": {"id": pack.id, "label": pack.label, "about": pack.about} if pack else None,
        "domain_card": registry.card(reg, district_id) if reg else None,
        "domain_note": (
            None
            if pack
            else (
                "Registry domain found, but no deep pack yet: licences, schemes and risks are"
                " specific; milestones use the common spine."
                if reg
                else "No domain matches this product yet, so only the common spine is used."
                " Add a registry card or a pack to make it specific."
            )
        ),
        "risks_by_phase": risks,
        "variants": [
            {
                "key": v.key,
                "label": v.label,
                "kind": v.kind,
                "flags": v.flags,
                "basis": v.basis,
                "recipe": v.items,
            }
            for v in chosen
        ],
        "unknown_variants": unknown,
        "recipe_note": pack.recipe_note if pack else "",
        "shared_ingredients": shared_ingredients(pack, chosen) if pack else [],
        "free_extensions": free_extensions(pack, chosen) if pack else [],
        "sourcing": (
            [
                {
                    "ingredient": pack.ingredients[k]["label"],
                    "where": pack.ingredients[k]["sourcing"],
                }
                for k in sorted({k for v in chosen for k in v.items})
            ]
            if pack
            else []
        ),
        "costs": costs,
        "regulatory": [r for r in (pack.regulatory if pack else [])],
        "roadmap": {
            "milestones": [
                {
                    "id": p.milestone.id,
                    "phase": p.milestone.phase.value,
                    "title": p.milestone.title,
                    "deliverables": p.milestone.deliverables,
                    "months": {
                        "optimistic": p.milestone.timeline.optimistic,
                        "realistic": p.milestone.timeline.realistic,
                        "pessimistic": p.milestone.timeline.pessimistic,
                    },
                    "depends_on": p.milestone.depends_on,
                    "critical": p.milestone.critical,
                    "why": p.template.why,
                    "because": p.because,
                    "from": p.template.pack,
                    "risks": [r["label"] for r in risks.get(p.milestone.phase.value, [])[:2]],
                }
                for p in road["ordered"]
            ],
            "critical_path": road["critical_path"],
            "months_realistic": road["months_realistic"],
        },
        "next_questions": next_questions,
    }
