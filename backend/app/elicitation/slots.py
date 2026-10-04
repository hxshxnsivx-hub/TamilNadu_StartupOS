"""The slot schema — the five-finger frame made computable (Req 1.2 AC3–AC4).

The client's "five finger rule" is the completeness predicate for an objective.
To be computable each finger must be bound to named slots with types and
admissible values, not to a vibe.

One adjustment to the literal five: WHERE and WHO collapse into a single
finger. For this product "where" is a Tamil Nadu district and "who" is a
beneficiary segment, and both answer the same underlying question — *who and
where is the demand*. Keeping them apart left WHO with no home. So:

    WHAT · WHY · WHO_WHERE · WHEN · HOW

DECISION CLASSES, NOT DOMAIN SIZE
---------------------------------
`decision_classes` is the number of equivalence classes a slot's values map to
*across all its consumers* — NOT `len(domain)`. This is the single most
important field here and it is not a detail.

Scoring question value by information gain over raw domain size makes
`district` (38 values) outrank `problem`, so the system opens by asking a
founder which district they live in before asking what they want to build.
That is a correct answer to the wrong objective: 38 districts are not 38
different decisions. Every consumer that reads `district` branches on roughly
three classes — TN-rural, TN-urban, outside-TN — because that is the
granularity at which scheme eligibility actually changes.

This is value-of-information in Howard's sense: information is worth what it
changes about a decision, not what it costs to encode.
Howard, *Information Value Theory*, IEEE Trans. SSC 2(1), 1966.
https://doi.org/10.1109/TSSC.1966.300074

Setting `decision_classes` is a modelling act per slot and MUST be revisited
whenever a consumer's branching changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Finger(str, Enum):
    """The five-finger frame. Every REQUIRED slot belongs to exactly one."""

    WHAT = "what"
    WHY = "why"
    WHO_WHERE = "who_where"
    WHEN = "when"
    HOW = "how"


class Need(str, Enum):
    REQUIRED = "required"  # blocks progress past elicitation
    ENRICHING = "enriching"  # improves output, never blocks


class EntryMode(str, Enum):
    """Which door the user came through (Req 1.6 AC1).

    Both modes run the SAME machine — same selector, same stopping rule, same
    state machine. Only the REQUIRED set differs. The experience path is not a
    parallel implementation.
    """

    IDEA = "idea"  # "I have an idea"        (Req 1.2)
    EXPERIENCE = "experience"  # "find me an opportunity" (Req 1.6)


# ---------------------------------------------------------------- taxonomies


class Sector(str, Enum):
    """Canonical sector taxonomy (Req 2.7).

    Defined here because no canonical enum existed anywhere in the codebase —
    `idea.py` carried eight ad-hoc substring cue lists and `schemes/seed.py`
    used free strings. Downstream consumers (schemes, B2B, opportunity
    matching) must all read THIS enum so a founder's sector means one thing.
    """

    AGRI = "agri"
    TEXTILE = "textile"
    FOOD = "food"
    MANUFACTURING = "manufacturing"
    AUTO = "auto"
    ELECTRONICS = "electronics"
    IT_SERVICES = "it_services"
    HEALTH = "health"
    EDUCATION = "education"
    FINANCE = "finance"
    RETAIL = "retail"
    OTHER = "other"


class ProductForm(str, Enum):
    SOFTWARE = "software"
    PHYSICAL = "physical"
    SERVICE = "service"
    HYBRID = "hybrid"


class CapitalBand(str, Enum):
    UNDER_2L = "under_2L"
    L2_10 = "2L_10L"
    L10_50 = "10L_50L"
    L50_2_5CR = "50L_2.5Cr"
    ABOVE_2_5CR = "above_2.5Cr"


class FundingRoute(str, Enum):
    SELF = "self"
    DEBT = "debt"
    EQUITY = "equity"
    GRANT = "grant"
    MIXED = "mixed"


class GeoScope(str, Enum):
    LOCAL = "local"
    DISTRICT = "district"
    STATE = "state"
    NATIONAL = "national"
    EXPORT = "export"


class TimeHorizon(str, Enum):
    UNDER_6M = "<6mo"
    M6_12 = "6-12mo"
    Y1_2 = "1-2y"
    OVER_2Y = ">2y"


class Motivation(str, Enum):
    INCOME = "income"
    INDEPENDENCE = "independence"
    IMPACT = "impact"
    SUCCESSION = "succession"


# ---------------------------------------------------------------- slot table


@dataclass(frozen=True)
class Slot:
    key: str
    finger: Finger
    need: Need
    kind: str  # "text" | "enum" | "int" | "multi"
    decision_classes: int  # see module docstring — NOT len(domain)
    consumers: tuple[str, ...]  # who reads it (the elicit-once contract)
    enum: type[Enum] | None = None
    bounds: tuple[int, int] | None = None
    question: str = ""
    # Slots carrying data with a heightened protection class are never asked
    # during ideation. See SENSITIVE below.
    sensitive: bool = False
    examples: tuple[str, ...] = field(default_factory=tuple)


SLOTS: tuple[Slot, ...] = (
    # ---- WHAT ------------------------------------------------------------
    Slot(
        "problem",
        Finger.WHAT,
        Need.REQUIRED,
        "text",
        8,
        ("roadmap", "feasibility"),
        question="What problem are you trying to solve, and for whom?",
        examples=("Small weavers in Erode can't reach buyers outside the district",),
    ),
    Slot(
        "solution",
        Finger.WHAT,
        Need.REQUIRED,
        "text",
        8,
        ("roadmap", "feasibility"),
        question="What will you actually make or do to solve it?",
    ),
    Slot(
        "sector",
        Finger.WHAT,
        Need.REQUIRED,
        "enum",
        12,
        ("roadmap", "scheme", "opportunity", "b2b"),
        enum=Sector,
        question="Which sector does this sit in?",
    ),
    Slot(
        "product_form",
        Finger.WHAT,
        Need.REQUIRED,
        "enum",
        4,
        ("roadmap", "b2b"),
        enum=ProductForm,
        question="Is this software, a physical product, a service, or a mix?",
    ),
    # ---- WHO / WHERE -----------------------------------------------------
    Slot(
        "beneficiary",
        Finger.WHO_WHERE,
        Need.REQUIRED,
        "text",
        8,
        ("roadmap", "opportunity"),
        question="Who pays for it, or benefits from it?",
    ),
    Slot(
        "district",
        Finger.WHO_WHERE,
        Need.REQUIRED,
        "enum",
        3,
        ("scheme", "opportunity"),
        question="Which district will you operate from?",
    ),
    Slot(
        "geo_scope",
        Finger.WHO_WHERE,
        Need.ENRICHING,
        "enum",
        5,
        ("roadmap", "opportunity"),
        enum=GeoScope,
        question="How far do you want to reach — local, state, national, export?",
    ),
    # ---- WHEN ------------------------------------------------------------
    Slot(
        "stage",
        Finger.WHEN,
        Need.REQUIRED,
        "enum",
        7,
        ("roadmap", "scheme", "funding"),
        question="Where are you today — just an idea, a prototype, already selling?",
    ),
    Slot(
        "time_horizon",
        Finger.WHEN,
        Need.ENRICHING,
        "enum",
        4,
        ("roadmap",),
        enum=TimeHorizon,
        question="When do you want to be running?",
    ),
    Slot(
        "urgency_reason",
        Finger.WHEN,
        Need.ENRICHING,
        "text",
        4,
        ("feasibility",),
        question="Is anything forcing the timing?",
    ),
    # ---- HOW -------------------------------------------------------------
    Slot(
        "capital_band",
        Finger.HOW,
        Need.REQUIRED,
        "enum",
        5,
        ("roadmap", "scheme", "opportunity"),
        enum=CapitalBand,
        question="Roughly how much can you put in to start?",
    ),
    Slot(
        "funding_route",
        Finger.HOW,
        Need.REQUIRED,
        "enum",
        5,
        ("roadmap", "scheme", "funding"),
        enum=FundingRoute,
        question="How do you expect to fund it — your own money, a loan, a grant, investors?",
    ),
    Slot(
        "team_size",
        Finger.HOW,
        Need.ENRICHING,
        "int",
        4,
        ("roadmap",),
        bounds=(1, 20),
        question="How many people will be working on this?",
    ),
    Slot(
        "founder_years",
        Finger.HOW,
        Need.ENRICHING,
        "int",
        5,
        ("roadmap", "opportunity"),
        bounds=(0, 40),
        question="How many years have you worked in this line?",
    ),
    Slot(
        "founder_skills",
        Finger.HOW,
        Need.ENRICHING,
        "multi",
        8,
        ("roadmap", "opportunity"),
        question="What can you already do well?",
    ),
    Slot(
        "owned_assets",
        Finger.HOW,
        Need.ENRICHING,
        "multi",
        5,
        ("opportunity", "scheme"),
        question="Do you already own land, machinery or premises you'd use?",
    ),
    # ---- WHY -------------------------------------------------------------
    Slot(
        "why_now",
        Finger.WHY,
        Need.ENRICHING,
        "text",
        4,
        ("feasibility",),
        question="Why is now the right time for this?",
    ),
    Slot(
        "differentiation",
        Finger.WHY,
        Need.ENRICHING,
        "text",
        4,
        ("feasibility",),
        question="What makes yours different from what already exists?",
    ),
    Slot(
        "motivation",
        Finger.WHY,
        Need.ENRICHING,
        "enum",
        4,
        ("opportunity",),
        enum=Motivation,
        question=(
            "What are you mainly after — income, independence, impact, "
            "continuing a family business?"
        ),
    ),
)

BY_KEY: dict[str, Slot] = {s.key: s for s in SLOTS}


# ---------------------------------------------------------------- protection

# Slots that carry data with the same protection class as Caste_Category
# (Req 1.6 AC10: explicit separate consent, encryption at rest, purpose
# limitation). These are DELIBERATELY absent from the table above.
#
# The elicitation conversation must never ask for them in the same breath as
# the idea. They belong to a later, separately-consented step, and treating
# every slot as equivalent is exactly how a consent boundary gets violated by
# accident.
SENSITIVE_DEFERRED: frozenset[str] = frozenset(
    {"caste_category", "bank_statement", "investible_amount_evidenced", "aadhaar", "pan"}
)


# ---------------------------------------------------------------- entry modes


def _required_for(mode: EntryMode) -> frozenset[str]:
    if mode is EntryMode.IDEA:
        return frozenset(s.key for s in SLOTS if s.need is Need.REQUIRED)
    # Req 1.6: the user has no idea yet — that is the entire point — so the
    # idea-shaped slots cannot be required. What they DO have is experience,
    # so the slots describing it are promoted.
    drop = {"problem", "solution", "beneficiary"}
    promote = {"founder_skills", "founder_years", "owned_assets", "motivation"}
    base = {s.key for s in SLOTS if s.need is Need.REQUIRED} - drop
    return frozenset(base | promote)


REQUIRED_BY_MODE: dict[EntryMode, frozenset[str]] = {
    mode: _required_for(mode) for mode in EntryMode
}


def fingers_covered(filled: set[str], mode: EntryMode) -> set[Finger]:
    """Which fingers have at least one REQUIRED slot filled."""
    req = REQUIRED_BY_MODE[mode]
    return {BY_KEY[k].finger for k in filled if k in req and k in BY_KEY}


def missing_required(filled: set[str], mode: EntryMode) -> set[str]:
    return set(REQUIRED_BY_MODE[mode]) - filled
