"""Domain packs — what makes a roadmap specific to the product being built.

A pack is a JSON file in data/packs/: the questions that product raises, its
ingredients or components, starting recipes, a cost model, regulatory items
(each with a confidence and a source) and milestone templates. `common.json`
is the spine every founder shares; a domain pack adds to it and can replace a
common template by using the same id.

Adding a domain is a data change, not a code change: write a new pack file.

Template applicability is a rule tree, evaluated by the scheme engine's own
evaluator (app.schemes.rules.evaluate), so a milestone can say why it is there
("because one of your blends has no tea leaves").
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemes.rules import Combinator, Op, Rule, RuleGroup

PACK_DIR = Path(__file__).parent / "data" / "packs"
COMMON = "common"


def parse_rule(d: dict | None) -> Rule | RuleGroup:
    """JSON rule -> Rule/RuleGroup. Missing means 'always applies' (an empty ALL)."""
    if not d:
        return RuleGroup(Combinator.ALL, [])
    for key in ("all", "any", "none"):
        if key in d:
            return RuleGroup(Combinator(key), [parse_rule(x) for x in d[key]], label=d.get("label"))
    return Rule(d["field"], Op(d["op"]), d.get("value"), label=d.get("label"))


@dataclass
class Template:
    id: str
    phase: str
    title: str
    deliverables: list[tuple[str, Rule | RuleGroup | None]]  # (text, condition or None)
    effort_weeks: float
    min_months: int
    relevance: int
    why: str
    pack: str
    core: bool = False
    depends_on: list[str] = field(default_factory=list)
    applies: Rule | RuleGroup = field(default_factory=lambda: RuleGroup(Combinator.ALL, []))
    done_from_stage: str | None = None
    calendar: bool = (
        False  # waiting on an office or a lab: team size and experience do not shorten it
    )


@dataclass
class Pack:
    id: str
    label: str
    about: str
    sector: str | None
    cues: list[str]
    questions: list[dict]
    templates: list[Template]
    ingredients: dict[str, dict] = field(default_factory=dict)
    recipes: dict[str, dict] = field(default_factory=dict)
    recipe_note: str = ""
    costing_defaults: dict[str, Any] = field(default_factory=dict)
    regulatory: list[dict] = field(default_factory=list)
    kinds: dict[str, Any] = field(default_factory=dict)  # {"default": label, "rules": [...]}
    name_noise: list[str] = field(default_factory=list)  # words ignored when matching names
    formats: dict[str, str] = field(default_factory=dict)  # format id -> label


def _load(path: Path) -> Pack:
    raw = json.loads(path.read_text(encoding="utf8"))
    templates = [
        Template(
            id=t["id"],
            phase=t["phase"],
            title=t["title"],
            deliverables=[
                (d, None) if isinstance(d, str) else (d["text"], parse_rule(d["applies"]))
                for d in t.get("deliverables", [])
            ],
            effort_weeks=t["effort_weeks"],
            min_months=t.get("min_months", 1),
            relevance=t.get("relevance", 50),
            why=t.get("why", ""),
            pack=raw["id"],
            core=t.get("core", False),
            depends_on=t.get("depends_on", []),
            applies=parse_rule(t.get("applies")),
            done_from_stage=t.get("done_from_stage"),
            calendar=t.get("calendar", False),
        )
        for t in raw.get("templates", [])
    ]
    return Pack(
        id=raw["id"],
        label=raw["label"],
        about=raw.get("about", ""),
        sector=raw.get("sector"),
        cues=raw.get("cues", []),
        questions=raw.get("questions", []),
        templates=templates,
        ingredients=raw.get("ingredients", {}),
        recipes=raw.get("recipes", {}),
        recipe_note=raw.get("recipe_note", ""),
        costing_defaults=raw.get("costing_defaults", {}),
        regulatory=raw.get("regulatory", []),
        kinds=raw.get("kinds", {}),
        name_noise=raw.get("name_noise", []),
        formats=raw.get("formats", {}),
    )


@lru_cache
def load_packs() -> dict[str, Pack]:
    return {p.id: p for p in (_load(f) for f in sorted(PACK_DIR.glob("*.json")))}


def detect_pack(text: str) -> str | None:
    """The domain pack whose cue words appear most in the founder's text, if any."""
    low = f" {(text or '').lower()} "
    best, best_hits = None, 0
    for pack in load_packs().values():
        hits = sum(1 for c in pack.cues if re.search(rf"\b{re.escape(c)}\b", low))
        if hits > best_hits:
            best, best_hits = pack.id, hits
    return best
