"""The registered-startup journey: which registrations apply, why, and in what order.

    facts (entity, turnover, employees, ...) + the startup's registry domain
      -> each step from data/steps.json judged on the facts:
           required     its rules hold
           recommended  not compulsory, but worth doing (with the reason)
           not_needed   its rules fail on known facts (with the reason)
           unknown      a missing fact decides it (with the question to ask)
           done         the founder says it is done
      -> the domain's own licences (FSSAI, BIS, ...) from the planner's library
      -> ordered by phase, then by dependency; the next steps are the
         required ones whose prerequisites are done

Rules are judged with three values (true, false, not known yet), so a fact the
founder has not given never silently counts as "no".
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.elicitation.entry import journey_facts
from app.planner import registry
from app.planner.packs import parse_rule
from app.schemes.rules import Combinator, Rule, RuleGroup, _apply

DATA = Path(__file__).parent / "data" / "steps.json"
PHASES_EXTRA = "Licences"


@lru_cache
def library() -> dict:
    return json.loads(DATA.read_text(encoding="utf8"))


def _fields(node: Rule | RuleGroup) -> list[str]:
    if isinstance(node, Rule):
        return [node.field]
    return [f for child in node.rules for f in _fields(child)]


def judge(node: Rule | RuleGroup, facts: dict[str, Any]) -> tuple[bool | None, list[str]]:
    """(True, False or None for "not known yet"; the reasons it is not True)."""
    if isinstance(node, Rule):
        if facts.get(node.field) is None:
            return None, []
        ok = _apply(node.op, facts[node.field], node.value)
        return ok, [] if ok else [node.describe()]
    results = [judge(child, facts) for child in node.rules]
    values = [v for v, _ in results]
    if node.combinator is Combinator.ALL:
        if False in values:
            return False, [r for v, rs in results if v is False for r in rs]
        return (None, []) if None in values else (True, [])
    if node.combinator is Combinator.ANY:
        if True in values:
            return True, []
        if None in values:
            return None, []
        return False, [node.label or "none of the conditions apply"]
    # NONE: true only when no child is true
    if True in values:
        return False, [node.label or "an exclusion applies"]
    return (None, []) if None in values else (True, [])


def _met(node: Rule | RuleGroup, facts: dict[str, Any]) -> list[str]:
    """Labels of the conditions that hold, to say why a step applies."""
    if isinstance(node, Rule):
        return [node.label] if node.label and judge(node, facts)[0] else []
    return [m for child in node.rules for m in _met(child, facts)]


def _questions(fields: list[str]) -> list[dict]:
    asks = library()["facts"]
    seen, out = set(), []
    for f in fields:
        if f in asks and f not in seen:
            seen.add(f)
            out.append({"fact": f, **asks[f]})
    return out


def _step(raw: dict, facts: dict, done: set[str]) -> dict:
    rule = parse_rule(raw.get("applies"))
    value, reasons = judge(rule, facts)
    label = raw.get("applies", {}).get("label") if isinstance(raw.get("applies"), dict) else None
    missing = [f for f in _fields(rule) if facts.get(f) is None]
    row = {
        "id": raw["id"],
        "phase": raw["phase"],
        "title": raw["title"],
        "why": raw["why"],
        "documents": raw.get("documents", []),
        "link": raw.get("link"),
        "days": raw.get("days"),
        "fee": raw.get("fee"),
        "confidence": raw.get("confidence", "secondary"),
        "depends_on": raw.get("depends_on", []),
        "questions": [],
    }
    if raw["id"] in done:
        row["status"], row["reason"] = "done", "you said this is done"
    elif value is True:
        row["status"] = "recommended" if raw.get("recommended_only") else "required"
        row["reason"] = label or "; ".join(_met(rule, facts)) or "your facts meet its conditions"
    elif value is None:
        row["status"], row["reason"] = "unknown", "depends on facts not given yet"
        row["questions"] = _questions(missing)
    else:
        rec = raw.get("recommended")
        rec_value = judge(parse_rule(rec), facts)[0] if rec else False
        if rec_value:
            row["status"], row["reason"] = "recommended", rec.get("label", "worth doing")
        else:
            row["status"] = "not_needed"
            row["reason"] = (
                "applies only when " + "; ".join(dict.fromkeys(reasons))
                if reasons
                else "does not apply"
            )
    row["advice"] = [
        a["text"]
        for a in raw.get("advice", [])
        if not a.get("when") or judge(parse_rule(a["when"]), facts)[0]
    ]
    return row


def _licences(domain_id: str | None, district: str | None, done: set[str]) -> list[dict]:
    if not domain_id:
        return []
    d = registry.load()["domains"].get(domain_id)
    if d is None:
        return []
    rows = []
    for item in registry.card(d, district)["regulatory_items"]:
        sid = f"lic:{item['id']}"
        rows.append(
            {
                "id": sid,
                "phase": PHASES_EXTRA,
                "title": item["title"],
                "why": item["text"],
                "documents": [],
                "link": item.get("source"),
                "days": None,
                "fee": None,
                "confidence": item.get("confidence", "secondary"),
                "depends_on": ["udyam"],
                "questions": [],
                "advice": [],
                "status": "done" if sid in done else "required",
                "reason": f"applies to {d['label'].lower()}"
                + (
                    " (confirm with the authority)" if item.get("confidence") == "to_verify" else ""
                ),
            }
        )
    return rows


def _order(rows: list[dict]) -> list[dict]:
    """By phase, then so that every step comes after the steps it depends on."""
    phases = library()["_meta"]["phases"]
    by_id = {r["id"]: r for r in rows}
    placed: list[dict] = []
    seen: set[str] = set()

    def place(r: dict, trail: frozenset = frozenset()) -> None:
        if r["id"] in seen or r["id"] in trail:
            return
        for dep in r["depends_on"]:
            if dep in by_id:
                place(by_id[dep], trail | {r["id"]})
        seen.add(r["id"])
        placed.append(r)

    for r in sorted(rows, key=lambda r: phases.index(r["phase"]) if r["phase"] in phases else 99):
        place(r)
    return placed


def normalise(facts: dict[str, Any]) -> dict[str, Any]:
    """Facts that follow from other facts, so they are never asked for."""
    f = {k: v for k, v in facts.items() if v is not None}
    if f.get("entity") == "none":
        f.setdefault("registered", False)
    if f.get("registered") is False:
        f.setdefault("years_since_incorporation", 0)  # registering now
    return f


def journey(
    facts: dict[str, Any],
    domain_id: str | None = None,
    done: list[str] | None = None,
    *,
    reg_subtype: str | None = None,
) -> dict:
    """`reg_subtype` (the Start screen's answer) fills registered, and entity when
    it follows (app/elicitation/entry.py); a fact in `facts` outranks it."""
    given = {k: v for k, v in facts.items() if v is not None}
    facts = normalise({**journey_facts(reg_subtype), **given})
    done_set = set(done or [])
    rows = [_step(raw, facts, done_set) for raw in library()["steps"]]
    rows += _licences(domain_id, facts.get("district"), done_set)
    active = {
        r["id"] for r in rows if r["status"] in ("required", "recommended", "unknown", "done")
    }
    for r in rows:  # a dependency that does not apply is not a prerequisite
        r["depends_on"] = [d for d in r["depends_on"] if d in active]
    rows = _order(rows)
    status = {r["id"]: r["status"] for r in rows}
    for r in rows:
        r["waiting_on"] = [d for d in r["depends_on"] if status.get(d) != "done"]
    next_steps = [r["id"] for r in rows if r["status"] == "required" and not r["waiting_on"]][:3]
    questions = _questions([q["fact"] for r in rows for q in r["questions"]])
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {
        "steps": rows,
        "next": next_steps,
        "questions": questions,
        "counts": counts,
        "domain_id": domain_id,
        "checked_on": library()["_meta"]["checked_on"],
        "note": (
            "Details change: each step links to the official place to do it. Steps marked"
            " to_verify should be confirmed with the authority before you rely on them."
        ),
    }
