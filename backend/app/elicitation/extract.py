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

Confidence tiers are meaningful and drive the bands (slots.py, R157):

  0.90  gazetteer / lexicon exact match
  0.85  structured cue ("the problem is X", a currency amount)
  0.70  weak cue
  0.55  loose positional guess — deliberately BELOW the known band (TAU_FILL
        0.60), in the confirm band: never asked, but said back as "I assumed"
        so the founder confirms it at the restatement, never silently assumed
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.stages import Stage
from app.elicitation.cues import affirmed, compile_cues, matches
from app.elicitation.places import find_district
from app.elicitation.slots import (
    CapitalBand,
    FundingRoute,
    Motivation,
    ProductForm,
    Sector,
)


@dataclass(frozen=True)
class Extraction:
    key: str
    value: object
    confidence: float


# ---------------------------------------------------------------- lexicons
#
# Cues match whole words (app/elicitation/cues.py): "shop" never fires inside
# "workshop". A trailing * marks a stem; a compiled pattern carries context.
# Compounds and longer forms the substring matcher used to reach are listed
# explicitly ("automotive", "application", "seafood"), never as a bare stem
# that would bring the traps back ("auto*" -> automation, "app*" -> apparel).

# 'course' and 'credit' are common in phrases that are not about the sector.
_COURSE = re.compile(r"(?<!of )\bcourses?\b")
_CREDIT = re.compile(r"(?<!carbon )\bcredits?\b")

_SECTOR_CUES: dict[Sector, tuple[str | re.Pattern[str], ...]] = {
    Sector.AGRI: ("agri*", "farm", "farmland", "crop", "irrigation", "soil", "dairy", "poultry"),
    Sector.TEXTILE: (
        "textile",
        "handloom",
        "weav*",
        "garment",
        "apparel",
        "saree",
        "yarn",
        "dyeing",
    ),
    Sector.FOOD: (
        "food",
        "foodtech",
        "foodgrain",
        "seafood",
        "restaurant",
        "kitchen",
        "snack",
        "beverage",
        "bakery",
        "catering",
    ),
    Sector.MANUFACTURING: (
        "manufactur*",
        "factory",
        "fabricat*",
        "machining",
        "foundry",
        "moulding",
    ),
    Sector.AUTO: (
        "auto",
        "automotive",
        "autopart",
        "autorickshaw",
        "vehicle",
        "spare part",
        "automobile",
        "ev",
        "two wheeler",
    ),
    Sector.ELECTRONICS: ("electronic", "pcb", "sensor", "iot", "hardware", "semiconductor"),
    Sector.IT_SERVICES: (
        "software",
        "saas",
        "app",
        "application",
        "webapp",
        "website",
        "it service",
        "platform",
        "portal",
    ),
    Sector.HEALTH: (
        "health*",
        "telehealth",
        "medical",
        "biomedical",
        "clinic",
        "clinical",
        "patient",
        "hospital",
        "diagnos*",
        "pharma*",
    ),
    Sector.EDUCATION: (
        "education",
        "educational",
        "educator",
        "edtech",
        "learning",
        "student",
        _COURSE,
        "tuition",
        "school",
        "preschool",
    ),
    Sector.FINANCE: (
        "fintech",
        "insurtech",
        "payment",
        "lending",
        "loan",
        _CREDIT,
        "insurance",
        "banking",
    ),
    Sector.RETAIL: (
        "retail",
        "ecommerce",
        "marketplace",
        "shop",
        "shopping",
        "shopkeeper",
        "store",
        "storefront",
        "d2c",
        "wholesale",
    ),
}

_FORM_CUES: dict[ProductForm, tuple[str | re.Pattern[str], ...]] = {
    ProductForm.SOFTWARE: (
        "app",
        "application",
        "software",
        "platform",
        "portal",
        "website",
        "saas",
    ),
    ProductForm.PHYSICAL: (
        "manufactur*",
        "product",
        "production",
        "machine",
        "machinery",
        "device",
        "unit",
        "factory",
    ),
    ProductForm.SERVICE: (
        "service",
        "servicing",
        "consult*",
        "training",
        "repair",
        "delivery",
        "agency",
    ),
}

_ROUTE_CUES: dict[FundingRoute, tuple[str | re.Pattern[str], ...]] = {
    FundingRoute.SELF: ("own money", "self fund*", "savings", "bootstrap*", "own funds"),
    FundingRoute.DEBT: ("loan", "bank finance", _CREDIT, "mudra", "borrow*"),
    FundingRoute.EQUITY: ("investor", "equity", "vc", "angel", "funding round"),
    FundingRoute.GRANT: ("grant", "subsidy", "scheme money", "seed fund", "seed funded"),
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
# Intent therefore scores 0.55 — deliberately BELOW TAU_FILL (0.60), in the
# confirm band — so it is said back as an assumption, never silently assumed.
# A denied state cue ("we don't have customers yet") is no evidence (R070).
_STAGE_STATE: dict[Stage, tuple[str, ...]] = {
    Stage.REVENUE: (
        "already selling",
        "have customers",
        "making sales",
        "revenue",
        "orders coming",
        "we sell",
    ),
    Stage.GROWTH: ("growing", "scaling up", "expanding", "second unit"),
    Stage.MVP: ("mvp", "pilot running", "first version", "in beta", "beta version"),
    Stage.PROTOTYPE: (
        "have a prototype",
        "built a prototype",
        "prototype is",
        "sample ready",
        "trial unit",
    ),
    Stage.POC: ("proof of concept", "tested the idea", "validated the idea"),
    Stage.IDEA: ("just an idea", "only an idea", "idea stage", "nothing built"),
}

# Founders describe what they have: "we have a working prototype", "built a
# basic sample". Fixed phrases miss the adjective, so allow up to two words
# between the article and the thing — but only after a have/built verb, so
# "want to build a working prototype" stays intent.
_STAGE_STATE_PATTERNS: dict[Stage, re.Pattern[str]] = {
    Stage.PROTOTYPE: re.compile(
        r"\b(?:have|has|had|built|made|developed|got)\s+(?:a|an|one|our|the)\s+"
        r"(?:[a-z-]+\s+){0,2}(?:prototype|sample|trial unit|working model)\b"
    ),
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

# WHY, in passing (R113): the five-finger rule needs a reason, and a pitch that
# already gave one must not be asked for it. Phrases, kept narrow: the founder's
# own words are stored, cue included.
_WHY_NOW_CUE = re.compile(
    r"\b(?:now that|nowadays|these days|the time is right because|right time (?:because|as))"
    r"\b[^.!?\n]{8,200}",
    re.I,
)
_DIFFERENT_CUE = re.compile(
    r"\b(?:unlike|different from|better than|cheaper than|faster than|no one else|nobody else"
    r"|what makes (?:it|us|ours|mine) different)\b[^.!?\n]{4,200}",
    re.I,
)
# What the founder is after, said about themselves; "income" alone is too
# often the customer's ("farmers lose income").
_MOTIVATION_CUES: dict[Motivation, tuple[str, ...]] = {
    Motivation.SUCCESSION: (
        "family business",
        "father's business",
        "fathers business",
        "carry on the business",
        "take over the business",
    ),
    Motivation.INCOME: ("extra income", "steady income", "earn a living", "support my family"),
    Motivation.INDEPENDENCE: ("my own boss", "work for myself", "be independent", "quit my job"),
    Motivation.IMPACT: ("give back", "make a difference", "social impact", "help my village"),
}


def _compiled(cues: dict) -> dict:
    return {value: compile_cues(needles) for value, needles in cues.items()}


_SECTOR_PATTERNS = _compiled(_SECTOR_CUES)
_FORM_PATTERNS = _compiled(_FORM_CUES)
_ROUTE_PATTERNS = _compiled(_ROUTE_CUES)
_STAGE_STATE_COMPILED = {
    stage: compile_cues(needles)
    + ((_STAGE_STATE_PATTERNS[stage],) if stage in _STAGE_STATE_PATTERNS else ())
    for stage, needles in _STAGE_STATE.items()
}
_STAGE_INTENT_PATTERNS = compile_cues(_STAGE_INTENT)
_MOTIVATION_PATTERNS = _compiled(_MOTIVATION_CUES)

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


def _first_cue(low: str, patterns: dict) -> object | None:
    for value, compiled in patterns.items():
        if matches(low, compiled):
            return value
    return None


def extract(text: str) -> list[Extraction]:
    """Pull whatever is genuinely present. Never invent, never placeholder."""
    if not text or not text.strip():
        return []
    low = f" {text.lower()} "
    out: list[Extraction] = []

    if (sec := _first_cue(low, _SECTOR_PATTERNS)) is not None:
        out.append(Extraction("sector", sec, 0.90))
    if (form := _first_cue(low, _FORM_PATTERNS)) is not None:
        out.append(Extraction("product_form", form, 0.70))
    if (route := _first_cue(low, _ROUTE_PATTERNS)) is not None:
        out.append(Extraction("funding_route", route, 0.85))
    # State evidence wins outright; intent only ever produces a confirm-band
    # hint that the restatement says back as an assumption.
    for stage, compiled in _STAGE_STATE_COMPILED.items():
        if affirmed(low, compiled):
            out.append(Extraction("stage", stage.value, 0.85))
            break
    else:
        if matches(low, _STAGE_INTENT_PATTERNS):
            out.append(Extraction("stage", Stage.IDEA.value, 0.55))

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
        # confirmed at the restatement rather than assumed. First sentence only.
        first = re.split(r"[.!?\n]", text.strip(), maxsplit=1)[0]
        out.append(Extraction("problem", _clean(first)[:200], 0.55))

    if (m := _SOLUTION_CUE.search(text)) is not None:
        out.append(Extraction("solution", _clean(m.group(1)), 0.70))

    if (m := _WHY_NOW_CUE.search(text)) is not None:
        out.append(Extraction("why_now", _clean(m.group(0)), 0.70))
    if (m := _DIFFERENT_CUE.search(text)) is not None:
        out.append(Extraction("differentiation", _clean(m.group(0)), 0.70))
    for motive, compiled in _MOTIVATION_PATTERNS.items():
        if affirmed(low, compiled):
            out.append(Extraction("motivation", motive, 0.70))
            break

    return out


def _clean(s: str) -> str:
    return _TRAIL.sub("", s.strip()).strip().rstrip(",;.").strip()
