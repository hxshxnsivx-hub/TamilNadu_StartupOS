"""Idea extraction — structure free text into concept elements (Req 1.2).

Offline heuristic extraction (deterministic, testable). When an LLM provider is
configured the swarm can replace this with richer extraction, but the element
set and domain taxonomy stay the same so downstream scoring is stable.
"""

from __future__ import annotations

from app.swarms.roadmap.models import StartupIdea

_DOMAIN_CUES: list[tuple[str, tuple[str, ...]]] = [
    ("agritech", ("agri", "farm", "crop", "irrigation", "soil", "agriculture")),
    ("healthtech", ("health", "medical", "clinic", "patient", "hospital", "diagnos")),
    ("fintech", ("fintech", "payment", "lending", "loan", "credit", "banking")),
    ("edtech", ("edtech", "education", "learning", "student", "course")),
    ("textile", ("textile", "handloom", "weav", "garment", "apparel", "saree")),
    ("hardware", ("hardware", "device", "iot", "sensor", "robot", "drone")),
    ("foodtech", ("food", "restaurant", "kitchen", "snack", "beverage")),
    ("ecommerce", ("ecommerce", "marketplace", "retail", "d2c", "online store")),
]

_SOLUTION = (
    "solve",
    "solution",
    "help",
    "enable",
    "provide",
    "platform",
    "app",
    "tool",
    "device",
    "service",
)
_MARKET = (
    "for ",
    "customers",
    "market",
    "farmers",
    "students",
    "women",
    "rural",
    "businesses",
    "smes",
)
_VALUE = (
    "cheaper",
    "faster",
    "affordable",
    "save",
    "reduce",
    "increase",
    "better",
    "efficient",
    "low cost",
)
_DIFF = ("unlike", "unique", "first", "only", "different", "patent", "proprietary", "no one")


def _detect_domain(text: str) -> str | None:
    for name, cues in _DOMAIN_CUES:
        if any(c in text for c in cues):
            return name
    return None


def extract_idea(text: str) -> StartupIdea:
    low = f" {text.lower()} "
    idea = StartupIdea(raw_text=text.strip())
    idea.problem = text.strip() or None
    idea.domain = _detect_domain(low)
    if any(k in low for k in _SOLUTION):
        idea.solution = "solution described"
    if any(k in low for k in _MARKET):
        idea.target_market = "target market described"
    if any(k in low for k in _VALUE):
        idea.value_proposition = "value proposition described"
    if any(k in low for k in _DIFF):
        idea.differentiation = "differentiation described"
    return idea
