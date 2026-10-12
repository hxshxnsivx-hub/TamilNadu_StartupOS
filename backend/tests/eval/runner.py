"""Run one quality-test idea as a full offline conversation and check it.

The conversation: the idea, then the engine's questions answered from the
idea's scripted answers ("skip" when there is none), "yes" to the restated
objective, then the roadmap. Research is replayed from the recorded fixture,
so the run is the same every time and needs no network or API key.
"""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from app.agents import ideation as agent
from app.agents.grounding import BANNED
from app.core.config import get_settings
from app.core.redis import set_redis
from app.planner.plan import build_plan
from app.research import novelty as novelty_mod
from app.research import scan as scan_mod

EVAL = Path(__file__).parent
MAX_TURNS = 20
# Writing mistakes that once reached founders; checked in every conversation.
WRITING = [
    ("proper nouns keep their capitals", re.compile(r"\btamil Nadu\b")),
    (
        "counts agree with nouns",
        re.compile(r"\b1 [\w-]+ (?:projects|papers|trials|patents)\b"),
    ),
    ("numbers are readable", re.compile(r"\b\d{5,}\b")),
    ("one colon per sentence", re.compile(r":[^.?!:]*:\s")),
    ("zero is said as none", re.compile(r"\bonly 0\b")),
]


def load_ideas() -> list[dict]:
    return json.loads((EVAL / "ideas.json").read_text(encoding="utf8"))["ideas"]


def load_fixture(idea_id: str) -> dict:
    return json.loads((EVAL / "fixtures" / f"{idea_id}.json").read_text(encoding="utf8"))


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Result:
    id: str
    checks: list[Check] = field(default_factory=list)
    transcript: list[tuple[str, str]] = field(default_factory=list)
    asked: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]


@contextmanager
def offline(fixture: dict):
    """No model, no Redis, and research answered from the recording."""
    st = get_settings()
    saved = (st.anthropic_api_key, scan_mod.scan, novelty_mod.check)

    async def replay_scan(*_a, **_k):
        return fixture["scan"]

    async def replay_novelty(*_a, **_k):
        return fixture["novelty"]

    st.anthropic_api_key = ""
    set_redis(None)
    scan_mod.scan, novelty_mod.check = replay_scan, replay_novelty
    try:
        yield
    finally:
        st.anthropic_api_key, scan_mod.scan, novelty_mod.check = saved


def _answer(action: dict, answers: dict) -> str:
    slot = action.get("slot") or ""
    if slot.startswith("dyn:"):
        return answers.get("dynamic", "skip")
    return answers.get(slot, "skip")


async def converse(idea: dict, result: Result) -> agent.AgentSession:
    s, greeting = agent.new_session("Eval")
    result.transcript.append(("agent", greeting))
    text = idea["idea"]
    for _ in range(MAX_TURNS):
        result.transcript.append(("founder", text))
        done = await agent.turn(s, text)
        result.transcript.append(("agent", done.get("reply", "")))
        action = done["action"]
        if action["kind"] == "ask":
            result.asked.append(action["slot"])
            text = _answer(action, idea.get("answers", {}))
        elif action["kind"] == "confirm":
            text = "yes"
        else:  # generate (the roadmap was built in this turn) or done
            break
    return s


async def run_idea(idea: dict) -> Result:
    result = Result(idea["id"])
    exp = idea["expect"]
    fixture = load_fixture(idea["id"])
    with offline(fixture):
        s = await converse(idea, result)
        slots = {k: getattr(v.value, "value", v.value) for k, v in s.elicitation.slots.items()}
        plan = build_plan(agent._idea_text(s), slots, council=s.council)

    said = " ".join(t for who, t in result.transcript if who == "agent")
    add = result.checks.append

    got = (plan.get("domain_card") or {}).get("id")
    add(Check("domain", got == exp["domain"], f"expected {exp['domain']}, got {got}"))
    got = (plan.get("domain") or {}).get("id")
    add(Check("pack", got == exp["pack"], f"expected {exp['pack']}, got {got}"))

    cats = set(fixture["scan"].get("vanigam_categories", []))
    want = set(exp.get("categories_include", []))
    add(
        Check(
            "categories",
            want <= cats,
            f"missing {sorted(want - cats)} from {sorted(cats)}",
        )
    )

    again = [k for k in exp.get("must_not_ask", []) if k in result.asked]
    add(Check("no re-asking", not again, f"asked for {again} though the idea gave them"))

    n = len([a for a in result.asked if a])
    add(Check("question limit", n <= exp["max_questions"], f"{n} questions asked"))

    add(Check("reached roadmap", bool(s.roadmap), "no roadmap after the restatement"))

    titles = " | ".join(m["title"] for m in (s.roadmap or {}).get("milestones", []))
    for word in exp.get("roadmap_must_include", []):
        add(
            Check(
                f"milestone '{word}'",
                word.lower() in titles.lower(),
                f"titles: {titles}",
            )
        )

    risk_keys = {r["risk"] for rows in plan.get("risks_by_phase", {}).values() for r in rows}
    for key in exp.get("risks_must_include", []):
        add(Check(f"risk '{key}'", key in risk_keys, f"risks: {sorted(risk_keys)}"))

    for text in exp.get("must_mention", []):
        add(Check(f"mentions '{text}'", text.lower() in said.lower(), "not in any reply"))

    for text in exp.get("must_not_mention", []):
        add(Check(f"never says '{text}'", text.lower() not in said.lower(), "said it"))

    for name, pattern in WRITING:
        bad = pattern.search(said)
        add(Check(name, bad is None, f"'{bad.group(0)}'" if bad else ""))

    claim = BANNED.search(said)
    add(
        Check(
            "no novelty claim",
            claim is None,
            f"said '{claim.group(0)}'" if claim else "",
        )
    )
    return result
