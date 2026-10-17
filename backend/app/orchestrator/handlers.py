"""The task nodes of the conversation machine: each calls its swarm's own code.

All offline and deterministic. The founder's profile lives in the orchestrator
state (``entities["profile"] = {"founder": {...}, "startup": {...}}``) so every
node reads the same facts; the idea lives in the ideation session the whole
conversation is saved in.
"""

from __future__ import annotations

import re

from app.agents import ideation
from app.b2b.decompose import decompose
from app.funding.gaps import analyze_gaps
from app.funding.readiness import score_readiness
from app.orchestrator.graph import Handler, HandlerResult, TurnContext
from app.orchestrator.intent import Intent
from app.schemes.swarm import SchemeSwarm
from app.services.completeness import CompletenessInput, score_completeness
from app.swarms.roadmap import RoadmapSwarm

_NAME = re.compile(r"\bmy name is ([A-Za-z][A-Za-z .'-]{0,60}?)(?:[,.!?]|$| and )", re.I)
_schemes = SchemeSwarm()
_roadmaps = RoadmapSwarm()


def _profile(ctx: TurnContext) -> dict:
    p = ctx.state.entities.setdefault("profile", {})
    p.setdefault("founder", {})
    p.setdefault("startup", {})
    return p


def _say_list(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


async def idea_discussion(ctx: TurnContext) -> HandlerResult:
    """The ideation agent shapes the idea; a roadmap request shows the roadmap so far."""
    s = ctx.session
    if ctx.classification.intent == Intent.ROADMAP_REQUEST:
        if s.roadmap:
            road = s.roadmap
        elif s.idea:
            rm = _roadmaps.generate(s.idea)
            road = {
                "milestones": [{"title": m.title, "phase": m.phase.value} for m in rm.milestones],
                "feasibility_score": rm.feasibility.score,
            }
        else:
            return HandlerResult(
                "I can build a roadmap once I know the idea. Tell me about it in your own words.",
                done=False,
                data={"roadmap": None},
            )
        ms = road["milestones"]
        reply = (
            f"Your roadmap has {len(ms)} milestones. It starts with "
            f"{_say_list([m['title'] for m in ms[:3]])}."
        )
        return HandlerResult(reply, done=False, data={"roadmap": road})

    out = await ideation.turn(s, ctx.text, language=ctx.language)
    data = {k: out.get(k) for k in ("action", "known", "evidence", "roadmap", "novelty")}
    return HandlerResult(out.get("reply") or "", done=False, data=data)


async def profile_collection(ctx: TurnContext) -> HandlerResult:
    """Take what the founder said about themselves, then score the profile's completeness."""
    p = _profile(ctx)
    if m := _NAME.search(ctx.text):
        p["founder"]["name"] = m.group(1).strip().title()
    r = score_completeness(CompletenessInput(founder=p["founder"], startup=p["startup"]))
    reply = f"Your profile is {r.score}% complete."
    if r.missing_fields:
        fields = [f.split(".", 1)[1].replace("_", " ") for f in r.missing_fields]
        reply += f" To reach the next level I still need your {_say_list(fields)}."
    if ctx.classification.intent == Intent.DOCUMENT_UPLOAD:
        reply += " You can upload documents from the verification screen."
    data = {"score": r.score, "tier": r.tier, "missing_fields": r.missing_fields}
    return HandlerResult(reply, done=True, data=data)


async def scheme_discovery(ctx: TurnContext) -> HandlerResult:
    """Every seeded scheme checked against the profile, the best three named."""
    rec = _schemes.recommend(_profile(ctx))
    top = rec.ranked_eligible[:3]
    if top:
        reply = (
            f"Of {rec.total_checked} schemes, you qualify for {len(rec.ranked_eligible)}."
            f" The best fits are {_say_list([r.scheme.name for r in top])}."
        )
    else:
        reply = (
            f"I checked {rec.total_checked} schemes and could not yet prove you eligible for"
            " any. Most need your age, district and startup stage; add those to your profile"
            " and I will check again."
        )
    data = {
        "total_checked": rec.total_checked,
        "eligible": [{"id": r.scheme.id, "name": r.scheme.name, "why": r.why} for r in top],
    }
    return HandlerResult(reply, done=True, data=data)


async def b2b_matching(ctx: TurnContext) -> HandlerResult:
    """A draft bill of materials for the product, the start of supplier matching."""
    product = (ctx.session.idea if ctx.session is not None else "") or ctx.text
    bom = decompose(product)
    reply = (
        f"For this product you will need {_say_list([b.spec for b in bom])}."
        " Open the suppliers screen to see Tamil Nadu companies for each."
    )
    data = {"bom": [{"category": b.category, "spec": b.spec} for b in bom]}
    return HandlerResult(reply, done=True, data=data)


async def funding_assessment(ctx: TurnContext) -> HandlerResult:
    """Readiness across six dimensions, and the single most useful thing to do next."""
    p = _profile(ctx)
    r = score_readiness({**p["founder"], **p["startup"]})
    gaps = analyze_gaps(r)
    reply = f"Your funding readiness is {r.overall} out of 100 ({r.band})."
    if gaps:
        reply += f" The most useful next step: {gaps[0].action}"
    data = {
        "overall": r.overall,
        "band": r.band,
        "dimensions": r.dimensions,
        "next_step": gaps[0].action if gaps else None,
    }
    return HandlerResult(reply, done=True, data=data)


HANDLERS: dict[str, Handler] = {
    "idea_discussion": idea_discussion,
    "profile_collection": profile_collection,
    "scheme_discovery": scheme_discovery,
    "b2b_matching": b2b_matching,
    "funding_assessment": funding_assessment,
}

__all__ = ["HANDLERS", "TurnContext", "HandlerResult"]
