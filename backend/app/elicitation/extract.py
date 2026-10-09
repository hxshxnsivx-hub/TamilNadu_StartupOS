"""Offline slot extraction (Req 1.2 AC2).

Replaces `swarms/roadmap/idea.py::extract_idea`, which substring-matched ten
keywords and then wrote the LITERAL string "solution described" into the
solution field. It never extracted anything; that is the root cause of the
generic output.

Two implementations behind one interface:

  * this module — deterministic, no network, works on 2G and offline. It is
    the BASELINE and must always be present.
  * an LLM path (when a provider is configured) that returns the same shape.

The deterministic path is not a stopgap. Many target users are on intermittent
connections, and an ideation flow that stops working without a network is not
usable for them.

Confidence tiers are meaningful and drive the stopping rule (TAU_FILL = 0.60):

  0.90  gazetteer / lexicon exact match
  0.85  structured cue ("the problem is X", a currency amount)
  0.70  weak cue
  0.55  loose positional guess — deliberately BELOW the fill threshold, so it
        becomes a confirmation question rather than a silent assumption
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.elicitation.places import find_district
from app.elicitation.slots import (
    CapitalBand,
    FundingRoute,
    ProductForm,
    Sector,
)


@dataclass(frozen=True)
class Extraction:
    key: str
    value: object
    confidence: float


# ---------------------------------------------------------------- lexicons

_SECTOR_CUES: dict[Sector, tuple[str, ...]] = {
    Sector.AGRI: ("agri", "farm", "crop", "irrigation", "soil", "dairy", "poultry"),
    Sector.TEXTILE: (
        "textile",
        "handloom",
        "weav",
        "garment",
        "apparel",
        "saree",
        "yarn",
        "dyeing",
    ),
    Sector.FOOD: ("food", "restaurant", "kitchen", "snack", "beverage", "bakery", "catering"),
    Sector.MANUFACTURING: ("manufactur", "factory", "fabricat", "machining", "foundry", "moulding"),
    Sector.AUTO: ("auto", "vehicle", "spare part", "automobile", "ev ", "two wheeler"),
    Sector.ELECTRONICS: ("electronic", "pcb", "sensor", "iot", "hardware", "semiconductor"),
    Sector.IT_SERVICES: ("software", "saas", "app", "website", "it service", "platform", "portal"),
    Sector.HEALTH: ("health", "medical", "clinic", "patient", "hospital", "diagnos", "pharma"),
    Sector.EDUCATION: ("education", "edtech", "learning", "student", "course", "tuition", "school"),
    Sector.FINANCE: ("fintech", "payment", "lending", "loan", "credit", "insurance", "banking"),
    Sector.RETAIL: ("retail", "ecommerce", "marketplace", "shop", "store", "d2c", "wholesale"),
}

_FORM_CUES: dict[ProductForm, tuple[str, ...]] = {
    ProductForm.SOFTWARE: ("app", "software", "platform", "portal", "website", "saas"),
    ProductForm.PHYSICAL: ("manufactur", "product", "machine", "device", "unit", "factory"),
    ProductForm.SERVICE: ("service", "consult", "training", "repair", "delivery", "agency"),
}

_ROUTE_CUES: dict[FundingRoute, tuple[str, ...]] = {
    FundingRoute.SELF: ("own money", "self fund", "savings", "bootstrap", "own funds"),
    FundingRoute.DEBT: ("loan", "bank finance", "credit", "mudra", "borrow"),
    FundingRoute.EQUITY: ("investor", "equity", "vc", "angel", "funding round"),
    FundingRoute.GRANT: ("grant", "subsidy", "scheme money", "seed fund"),
}

# Stage evidence is split by KIND, because the two are not equally reliable.
#
# STATE cues report something that already exists ("we have a prototype",
# "already selling") — strong evidence of where the founder actually is.
#
# INTENT cues report a wish ("I want to start", "planning to"). These are NOT
# evidence of stage: a founder with a working prototype will still say "I want
# to start a finishing unit". Treating intent as state is how the system
# confidently mislabels someone as pre-idea and then hands them a roadmap that
# begins three steps behind where they are.
#
# Intent therefore scores 0.55 — deliberately BELOW TAU_FILL (0.60) — so it
# becomes a confirmation question instead of a silent assumption.
_STAGE_STATE: dict[str, tuple[str, ...]] = {
    "revenue": (
        "already selling",
        "have customers",
        "making sales",
        "revenue",
        "orders coming",
        "we sell",
    ),
    "growth": ("growing", "scaling up", "expanding", "second unit"),
    "mvp": ("mvp", "pilot running", "first version", "in beta", "beta version"),
    "prototype": (
        "have a prototype",
        "built a prototype",
        "prototype is",
        "sample ready",
        "trial unit",
    ),
    "poc": ("proof of concept", "tested the idea", "validated the idea"),
    "idea": ("just an idea", "only an idea", "idea stage", "nothing built"),
}

_STAGE_INTENT: tuple[str, ...] = (
    "want to start",
    "planning to",
    "thinking of",
    "hoping to",
    "would like to start",
    "plan to start",
    "going to start",
)

# "5 lakh", "₹2,00,000", "10L", "1.5 crore"
_MONEY = re.compile(
    r"(?:₹|rs\.?\s*)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l\b|crore|cr\b|thousand|k\b)?",
    re.I,
)

# Sentence-bounded, deliberately. An unbounded `.{12,160}` runs straight
# through the full stop and swallows the next sentence, so "The problem is X.
# I want to build Y with 15 lakh" captured the funding plan as the problem and
# then repeated it as the solution. `[^.!?\n]` stops at the sentence.
_PROBLEM_CUE = re.compile(
    r"(?:problem|issue|difficulty|struggle|challenge)\s+(?:is|:)?\s*([^.!?\n]{12,200})", re.I
)
_SOLUTION_CUE = re.compile(
    r"(?:i want to|i plan to|we will|solution is)\s+([^.!?\n]{12,200})", re.I
)

# Trailing funding//capital clauses belong to capital_band, not to the
# sentence describing what is being built.
_TRAIL = re.compile(r"\s+(?:with|using|for)\s+[\d,.]+\s*(?:lakh|lakhs|crore|cr|l|k)\b.*$", re.I)


def _to_rupees(num: str, unit: str | None) -> float:
    n = float(num.replace(",", ""))
    u = (unit or "").lower()
    if u.startswith("l"):
        return n * 100_000
    if u.startswith("c"):
        return n * 10_000_000
    if u.startswith(("k", "t")):
        return n * 1_000
    return n


def _band(rupees: float) -> CapitalBand:
    if rupees < 200_000:
        return CapitalBand.UNDER_2L
    if rupees < 1_000_000:
        return CapitalBand.L2_10
    if rupees < 5_000_000:
        return CapitalBand.L10_50
    if rupees < 25_000_000:
        return CapitalBand.L50_2_5CR
    return CapitalBand.ABOVE_2_5CR


def _first_cue(low: str, cues: dict) -> object | None:
    for value, needles in cues.items():
        if any(n in low for n in needles):
            return value
    return None


def extract(text: str) -> list[Extraction]:
    """Pull whatever is genuinely present. Never invent, never placeholder."""
    if not text or not text.strip():
        return []
    low = f" {text.lower()} "
    out: list[Extraction] = []

    if (sec := _first_cue(low, _SECTOR_CUES)) is not None:
        out.append(Extraction("sector", sec, 0.90))
    if (form := _first_cue(low, _FORM_CUES)) is not None:
        out.append(Extraction("product_form", form, 0.70))
    if (route := _first_cue(low, _ROUTE_CUES)) is not None:
        out.append(Extraction("funding_route", route, 0.85))
    # State evidence wins outright; intent only ever produces a low-confidence
    # hint that the stopping rule will turn into a confirmation question.
    for stage, needles in _STAGE_STATE.items():
        if any(n in low for n in needles):
            out.append(Extraction("stage", stage, 0.85))
            break
    else:
        if any(n in low for n in _STAGE_INTENT):
            out.append(Extraction("stage", "idea", 0.55))

    # Capital: only trust a figure that actually carries a unit, otherwise
    # "I have 3 employees" becomes a ₹3 budget.
    for m in _MONEY.finditer(text):
        num, unit = m.group(1), m.group(2)
        if not unit:
            continue
        rupees = _to_rupees(num, unit)
        if rupees >= 10_000:
            out.append(Extraction("capital_band", _band(rupees), 0.85))
            break

    if (district := find_district(text)) is not None:
        out.append(Extraction("district", district, 0.85))

    # The actual words the founder used — not a placeholder token.
    if (m := _PROBLEM_CUE.search(text)) is not None:
        out.append(Extraction("problem", _clean(m.group(1)), 0.85))
    elif len(text.strip()) >= 25:
        # Loose positional guess at 0.55, deliberately BELOW TAU_FILL so it is
        # confirmed rather than assumed. First sentence only.
        first = re.split(r"[.!?\n]", text.strip(), maxsplit=1)[0]
        out.append(Extraction("problem", _clean(first)[:200], 0.55))

    if (m := _SOLUTION_CUE.search(text)) is not None:
        out.append(Extraction("solution", _clean(m.group(1)), 0.70))

    return out


def _clean(s: str) -> str:
    return _TRAIL.sub("", s.strip()).strip().rstrip(",;.").strip()
