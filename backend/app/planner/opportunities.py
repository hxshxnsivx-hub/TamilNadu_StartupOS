"""Opportunity cards for a founder with experience but no idea (task 1.1.5).

The experience conversation learns what the founder can do (skills, years,
assets, the line of work they know, where they live). After its restatement
the founder is offered three to five opportunity cards and picks one, or none
(elicitation/engine.py, CHOOSING, R066). A picked card is written into the idea
slots (`idea_slots`) and the idea conversation continues from it.

What a card must carry (R048): the idea it stands for, what it asks of the
founder (`skills_used`, `assets_used`, so a fit can be said and checked) and the
sources it rests on. A card with no source, or one still in draft review, is
never offered: "only real, cited sources" holds for opportunities as much as
for schemes.

THE RANKING IS NOT BUILT YET. It is task 1.1.5.3, and it waits on the sector
taxonomy (task 4.1.2, owner decision D5): the registry's domain cards have no
skills, assets or sources to match against yet, and 190 of 240 are drafts
(R048). Until then `rank` offers nothing, and the conversation says so plainly
rather than inventing opportunities (agents/ideation.py, NO_CARDS).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.elicitation.slots import ProductForm, Sector

MAX_CARDS = 5


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=200)
    url: HttpUrl


class Card(BaseModel):
    """One opportunity as offered to the founder. Every field shown is backed by
    `sources`; a card without one does not validate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9_]{2,64}$")
    label: str = Field(min_length=3, max_length=120)
    # the idea it stands for, written into the idea slots when picked
    problem: str = Field(min_length=3)
    solution: str = Field(min_length=3)
    sector: Sector
    product_form: ProductForm
    beneficiary: str = Field(min_length=3)
    # what it asks of the founder (R048), so the fit can be said and checked
    skills_used: list[str] = Field(min_length=1)
    assets_used: list[str] = Field(default_factory=list)
    sources: list[Citation] = Field(min_length=1)
    # a draft card is never offered (R048); the registry's own review states
    review: Literal["base", "approved"]


def rank(facts: dict[str, Any]) -> list[Card]:
    """The cards that fit these experience facts, best first.

    Task 1.1.5.3, waiting on the sector taxonomy (4.1.2, D5): there is nothing
    cited to rank yet, so nothing is offered."""
    return []


def offer(cards: list[Card]) -> list[Card]:
    """At most MAX_CARDS, each offered once."""
    seen: set[str] = set()
    out: list[Card] = []
    for c in cards:
        if c.id not in seen:
            seen.add(c.id)
            out.append(c)
    return out[:MAX_CARDS]


def idea_slots(card: Card) -> dict[str, Any]:
    """The slot values a picked card writes back (task 1.1.5.5)."""
    return {
        "problem": card.problem,
        "solution": card.solution,
        "sector": card.sector,
        "product_form": card.product_form,
        "beneficiary": card.beneficiary,
    }


def idea_text(card: Card) -> str:
    """The idea the card stands for, in words: what research searches for once
    the founder has picked it (R118)."""
    return f"{card.problem} {card.solution}"


__all__ = ["MAX_CARDS", "Card", "Citation", "idea_slots", "idea_text", "offer", "rank"]
