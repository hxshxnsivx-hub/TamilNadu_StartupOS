"""Risk analysis for each phase of the roadmap.

    score = level (1–3, the domain's typical level adjusted by the founder's own
            situation) × weight (1–3, how much that risk bites in this phase)

Each phase lists its top risks, each with why it applies to this founder, how
to reduce it, and the early warning sign to watch. Adjustments are explicit and
reported, so a founder sees, for example, "capital raised one level: you have
₹2–10 lakh; this domain typically needs ₹10–50 lakh".
"""

from __future__ import annotations

PHASES = ["Ideation", "Validation", "MVP", "Launch", "Growth", "Scale"]
CAPITAL_ORDER = ["under_2L", "2L_10L", "10L_50L", "50L_2.5Cr", "above_2.5Cr"]
CAPITAL_TEXT = {
    "under_2L": "under ₹2 lakh",
    "2L_10L": "₹2–10 lakh",
    "10L_50L": "₹10–50 lakh",
    "50L_2.5Cr": "₹50 lakh–2.5 crore",
    "above_2.5Cr": "above ₹2.5 crore",
}

# risk -> (label, weight per phase, how to reduce it, early warning sign)
RISKS: dict[str, tuple[str, dict[str, int], str, str]] = {
    "market": (
        "Not enough buyers",
        {"Ideation": 3, "Validation": 3, "Launch": 2, "Growth": 2},
        "Pre-sell or take paid pilot orders before building at scale",
        "Fewer than 1 in 5 buyer conversations end in a commitment",
    ),
    "competition": (
        "Crowded market",
        {"Validation": 2, "Launch": 3, "Growth": 3, "Scale": 2},
        "Pick one buyer segment you can serve better and say why in one line",
        "You win on price alone, or lose deals to the same rival twice",
    ),
    "regulatory": (
        "Licences and rules",
        {"MVP": 3, "Launch": 2, "Scale": 2},
        "Apply for licences while building; confirm 'to verify' items with the regulator",
        "An application is pending beyond its stated timeline",
    ),
    "technical": (
        "Product does not work well enough",
        {"Validation": 2, "MVP": 3, "Launch": 1},
        "Prototype the riskiest part first and test it with real users",
        "The same defect returns after two fixes",
    ),
    "supply": (
        "Inputs or parts not reliably available",
        {"MVP": 2, "Launch": 2, "Growth": 2, "Scale": 3},
        "Qualify two suppliers for every critical input",
        "A supplier misses a delivery date or changes a price without notice",
    ),
    "capital": (
        "Running out of money",
        {"MVP": 3, "Launch": 2, "Growth": 3, "Scale": 2},
        "Plan 6 months of runway; line up the funding route before you need it",
        "Runway falls below 4 months",
    ),
    "seasonality": (
        "Seasonal demand or supply",
        {"Launch": 2, "Growth": 2, "Scale": 1},
        "Plan stock and cash around the season; add an off-season product",
        "Sales drop more than 30% month on month outside the season",
    ),
    "receivables": (
        "Slow payments from buyers",
        {"Launch": 3, "Growth": 3, "Scale": 2},
        "Advance payments, smaller first orders, invoice financing (TReDS) for big buyers",
        "Money owed to you exceeds 60 days of sales",
    ),
    "ip": (
        "Copying or ownership of ideas",
        {"Ideation": 2, "MVP": 2, "Scale": 1},
        "File the trademark early; consider a patent search before disclosing a novel mechanism",
        "A look-alike product or name appears",
    ),
    "data": (
        "Personal data and security",
        {"MVP": 2, "Launch": 2, "Growth": 2},
        "Collect only what you need, with consent; DPDP Act basics from day one",
        "You store data you never use, or share it without a written purpose",
    ),
    "execution": (
        "Doing everything with a small, new team",
        {"Validation": 2, "MVP": 2, "Launch": 2, "Growth": 2},
        "Find a mentor or incubator early; hire for the skill you lack first",
        "Milestones slip twice in a row",
    ),
}


def adjusted_levels(domain: dict, facts: dict) -> tuple[dict[str, int], dict[str, str]]:
    """Domain risk levels adjusted by the founder's situation, with the reason for each change."""
    lv = {k: int(domain.get("risk", {}).get(k, 1)) for k in RISKS if k != "execution"}
    why: dict[str, str] = {}
    have, need = facts.get("capital_band"), domain.get("capital_band")
    if have in CAPITAL_ORDER and need in CAPITAL_ORDER:
        gap = CAPITAL_ORDER.index(need) - CAPITAL_ORDER.index(have)
        if gap > 0:
            lv["capital"] = min(3, lv["capital"] + 1)
            why["capital"] = (
                f"you have {CAPITAL_TEXT[have]}; this domain typically needs {CAPITAL_TEXT[need]}"
            )
    if facts.get("funding_route") == "debt" and "capital" not in why:
        lv["capital"] = min(3, lv["capital"] + 1)
        why["capital"] = "a loan must be repaid from early sales"
    if facts.get("geo_scope") == "export":
        lv["regulatory"] = min(3, lv["regulatory"] + 1)
        why["regulatory"] = "export adds destination-country rules and registrations"
    buyers = " ".join(domain.get("buyers", [])).lower()
    if any(g in buyers for g in ("government", "local bodies", "municipal", "primary health")):
        lv["receivables"] = max(lv["receivables"], 3)
        why["receivables"] = "government buyers often pay late"
    years, team = facts.get("founder_years"), facts.get("team_size")
    execution = 1
    if years is not None and years < 2:
        execution += 1
        why["execution"] = "first venture in this field"
    if team is not None and team <= 1:
        execution += 1
        why["execution"] = (
            why.get("execution", "") + "; " if why.get("execution") else ""
        ) + "a solo founder"
    lv["execution"] = min(3, execution)
    return lv, why


# Which risks each council seat speaks to (build spec 11.2).
SEAT_RISKS = {
    "customer": ("market",),
    "technical": ("technical",),
    "regulatory": ("regulatory",),
    "cost": ("supply", "capital"),
    "prior_art": ("competition", "ip"),
    "funding": ("capital",),
    "devil": ("execution",),
}


def council_adjust(lv: dict[str, int], why: dict[str, str], council: dict | None) -> None:
    """Raise a risk by one level where a seat objected with cited evidence.

    A seat objects when it opposes, raises a blocker, or scores a criterion 2 or
    lower. Only opinions with at least one cited claim count; the reason given
    is that seat's own first claim.
    """
    for op in (council or {}).get("opinions", []):
        claims = op.get("claims") or []
        objects = (
            op.get("stance") == "oppose"
            or op.get("blocker")
            or min((op.get("scores") or {"x": 5}).values()) <= 2
        )
        if not (objects and (claims or op.get("blocker"))):
            continue
        reason = (op.get("blocker") or claims[0])["text"].rstrip(".")
        for key in SEAT_RISKS.get(op["seat"], ()):
            if key in lv:
                lv[key] = min(3, lv[key] + 1)
                why[key] = f"review panel ({op['seat'].replace('_', ' ')}): {reason}"


def by_phase(
    domain: dict, facts: dict, top: int = 4, council: dict | None = None
) -> dict[str, list[dict]]:
    lv, why = adjusted_levels(domain, facts)
    council_adjust(lv, why, council)
    out = {}
    for ph in PHASES:
        rows = []
        for key, (label, weights, reduce, warn) in RISKS.items():
            w = weights.get(ph, 0)
            if not w:
                continue
            score = lv[key] * w
            if score < 3:
                continue
            rows.append(
                {
                    "risk": key,
                    "label": label,
                    "level": lv[key],
                    "score": score,
                    "why": why.get(key, f"typical for {domain['label'].lower()}"),
                    "reduce": reduce,
                    "early_warning": warn,
                }
            )
        rows.sort(key=lambda r: (-r["score"], r["risk"]))
        out[ph] = rows[:top]
    return out
