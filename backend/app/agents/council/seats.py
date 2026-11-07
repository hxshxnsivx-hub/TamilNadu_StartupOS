"""The seven seats and the opinion each must return (build spec 7.1, 7.2).

Seats differ by construction, not by name alone: each answers one question,
sees its own slice of the evidence, and must cite it. The devil's advocate is
not allowed to support.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

CRITERIA = ("need", "feasibility", "compliance", "economics", "differentiation")
CRITERION_WORDS = {
    "need": "who needs it and pays for it",
    "feasibility": "whether it can be built",
    "compliance": "the approvals it needs",
    "economics": "cost and money",
    "differentiation": "what makes it different",
}


@dataclass(frozen=True)
class Seat:
    id: str
    name: str
    question: str
    kinds: frozenset[str]  # evidence slice this seat reads
    brief: str
    must_oppose: bool = False


_ALL = frozenset(
    {"field", "papers", "trials", "projects", "patents", "local", "coverage", "novelty", "domain",
     "regulatory", "funding", "risk", "cost"}
)  # fmt: skip

SEATS: tuple[Seat, ...] = (
    Seat(
        "customer",
        "Customer",
        "Who pays, and what do they use today?",
        frozenset({"local", "domain", "field", "novelty", "coverage"}),
        "Judge whether a real buyer exists and what they use today. Ask who pays.",
    ),
    Seat(
        "technical",
        "Technical",
        "Can it be built, at what unit cost and reliability?",
        frozenset({"projects", "papers", "field", "novelty", "coverage"}),
        "Judge whether it can be built reliably with what exists: open projects, papers.",
    ),
    Seat(
        "regulatory",
        "Clinical and regulatory",
        "Which approvals and validations apply?",
        frozenset({"regulatory", "trials", "field", "risk", "coverage"}),
        "Judge which licences, approvals and validation studies it needs before sale.",
    ),
    Seat(
        "cost",
        "Cost and supply",
        "What do inputs cost, and where can cost be cut?",
        frozenset({"cost", "domain", "risk", "projects"}),
        "Judge unit cost, supply and where cost can be cut.",
    ),
    Seat(
        "prior_art",
        "Prior art",
        "What exists, and where is the gap?",
        frozenset({"papers", "patents", "projects", "novelty", "local", "coverage"}),
        "Judge what already exists and where this idea can differ. Never call it new.",
    ),
    Seat(
        "funding",
        "Funding",
        "Which schemes and incubators fit, and are they open?",
        frozenset({"funding", "domain", "risk"}),
        "Judge which schemes and incubators fit and whether they are open now.",
    ),
    Seat(
        "devil",
        "Devil's advocate",
        "Why would this fail?",
        _ALL,
        "Argue why this would fail. You may not support it; find the strongest objection.",
        must_oppose=True,
    ),
)
BY_ID = {s.id: s for s in SEATS}


class Claim(BaseModel):
    text: str = Field(min_length=3, max_length=400)
    evidence: list[str] = Field(default_factory=list, max_length=6)
    # Which criterion the claim is about, and whether it speaks for (up), against
    # (down) or neither (neutral). Synthesis pairs on these so a claim is never
    # quoted for the wrong criterion or a neutral claim shown as a weakness (F-A1-020).
    criterion: str | None = None
    direction: Literal["up", "neutral", "down"] = "neutral"


Direction = Literal["up", "neutral", "down"]


def infer_claim_focus(scores: dict[str, int]) -> tuple[str | None, Direction]:
    """The criterion a seat is most opinionated about, and the direction of that
    opinion — used to label rule claims that arrive without an explicit focus."""
    if not scores:
        return None, "neutral"
    crit = max(scores, key=lambda c: abs(scores[c] - 3))
    s = scores[crit]
    direction: Direction = "up" if s >= 4 else "down" if s <= 2 else "neutral"
    return crit, direction


class Opinion(BaseModel):
    seat: str
    stance: Literal["support", "conditional", "oppose"]
    scores: dict[str, int]  # criterion -> 1..5
    confidence: float = Field(ge=0.0, le=1.0)
    claims: list[Claim] = Field(default_factory=list, max_length=4)
    blocker: Claim | None = None
    ask_founder: str | None = Field(default=None, max_length=300)
    variant: str | None = Field(default=None, max_length=300)
    basis: Literal["model", "rules"] = "rules"
    dropped_claims: int = 0


def validate(raw: dict, seat: Seat, evidence_ids: set[str], basis: str) -> Opinion | None:
    """Check an opinion against the pack: uncited claims go, a blocker needs a citation."""
    try:
        op = Opinion.model_validate({**raw, "seat": seat.id, "basis": basis})
    except ValidationError:
        return None
    op.scores = {c: max(1, min(5, int(v))) for c, v in op.scores.items() if c in CRITERIA}
    if not op.scores:
        return None
    kept = []
    for c in op.claims:
        c.evidence = [e for e in c.evidence if e in evidence_ids]
        if c.evidence:
            kept.append(c)
    op.dropped_claims = len(op.claims) - len(kept)
    op.claims = kept
    # Label any claim that arrived without a focus (every rule claim, and model
    # claims before the prompt carries the fields) from the seat's own scores.
    crit, direction = infer_claim_focus(op.scores)
    for c in op.claims:
        if c.criterion is None:
            c.criterion, c.direction = crit, direction
    if op.blocker is not None:
        op.blocker.evidence = [e for e in op.blocker.evidence if e in evidence_ids]
        if not op.blocker.evidence:
            op.blocker = None
        elif op.blocker.criterion is None:
            op.blocker.criterion, op.blocker.direction = crit, "down"
    if not op.claims:
        op.confidence = round(op.confidence / 2, 2)  # nothing it said could be backed
    if seat.must_oppose and op.stance == "support":
        op.stance = "conditional"
    return op
