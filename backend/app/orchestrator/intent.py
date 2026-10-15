"""Intent classification — the confidence cascade (design E1).

Stage 1 here is the deterministic keyword router (fast, free, testable). When its
confidence is below ``AUTO_ROUTE`` the orchestrator escalates to an embedding/LLM
classifier (added as those land); below ``CLARIFY`` it asks one question instead
of guessing. Input is assumed already normalised to English by the translation
layer, so English keywords suffice.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

CLARIFY = 0.5  # below this → ask a clarifying question
AUTO_ROUTE = 0.8  # at/above this → route without escalation


class Intent(str, Enum):
    PROFILE_UPDATE = "profile_update"
    IDEA_INPUT = "idea_input"
    ROADMAP_REQUEST = "roadmap_request"
    SCHEME_QUERY = "scheme_query"
    B2B_SEARCH = "b2b_search"
    FUNDING_QUERY = "funding_query"
    DOCUMENT_UPLOAD = "document_upload"
    GENERAL_QUESTION = "general_question"


# Intent → owning swarm (GENERAL is handled by the orchestrator itself).
INTENT_SWARM: dict[Intent, str] = {
    Intent.PROFILE_UPDATE: "profile",
    Intent.DOCUMENT_UPLOAD: "profile",
    Intent.IDEA_INPUT: "roadmap",
    Intent.ROADMAP_REQUEST: "roadmap",
    Intent.SCHEME_QUERY: "scheme",
    Intent.B2B_SEARCH: "b2b",
    Intent.FUNDING_QUERY: "funding",
    Intent.GENERAL_QUESTION: "orchestrator",
}

# Ordered so earlier intents win ties (more specific signals first).
_KEYWORDS: list[tuple[Intent, tuple[str, ...]]] = [
    (
        Intent.IDEA_INPUT,
        (
            "startup idea",
            "my idea",
            "business idea",
            "i have an idea",
            "i want to build",
            "i want to start",
            "idea is",
            "i have experience",
        ),
    ),
    (
        Intent.B2B_SEARCH,
        (
            "supplier",
            "raw material",
            "vendor",
            "bill of materials",
            "bom",
            "procure",
            "sourcing",
            "manufacturer",
            "b2b",
            "partner",
        ),
    ),
    (
        Intent.FUNDING_QUERY,
        (
            "investor",
            "raise funding",
            "raise money",
            "venture capital",
            "vc ",
            "angel",
            "seed round",
            "pitch",
            "valuation",
            "investor readiness",
        ),
    ),
    (
        Intent.SCHEME_QUERY,
        (
            "scheme",
            "subsidy",
            "grant",
            "government loan",
            "eligible",
            "eligibility",
            "tanseed",
            "pmegp",
            "mudra",
            "sisf",
        ),
    ),
    (
        Intent.DOCUMENT_UPLOAD,
        ("upload", "aadhaar", "pan card", "certificate", "gstin", "document", "mark sheet"),
    ),
    (
        Intent.ROADMAP_REQUEST,
        (
            "roadmap",
            "next steps",
            "how do i start",
            "milestone",
            "plan for",
            "guide me",
            "what should i do",
        ),
    ),
    (
        Intent.PROFILE_UPDATE,
        (
            "update my profile",
            "my name is",
            "my age",
            "my education",
            "my qualification",
            "my details",
            "profile",
        ),
    ),
]


@dataclass
class Classification:
    intent: Intent
    confidence: float
    swarm: str
    matched: tuple[str, ...]

    @property
    def should_clarify(self) -> bool:
        return self.confidence < CLARIFY

    @property
    def needs_escalation(self) -> bool:
        return CLARIFY <= self.confidence < AUTO_ROUTE


def classify_keywords(text: str) -> Classification:
    low = f" {text.lower()} "
    best: tuple[Intent, tuple[str, ...]] | None = None
    for intent, phrases in _KEYWORDS:
        hits = tuple(p for p in phrases if p in low)
        if hits and (best is None or len(hits) > len(best[1])):
            best = (intent, hits)

    if best is None:
        # No domain signal → a general question the orchestrator answers directly.
        return Classification(Intent.GENERAL_QUESTION, 0.5, "orchestrator", ())

    intent, hits = best
    # Curated domain keywords are strong: one hit already auto-routes.
    confidence = min(0.95, 0.8 + 0.07 * (len(hits) - 1))
    return Classification(intent, confidence, INTENT_SWARM[intent], hits)
