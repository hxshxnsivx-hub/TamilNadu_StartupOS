"""Tools the ideation agent's language model can call.

Each tool wraps a deterministic Vanigam engine and returns a compact result:
small enough to keep in the model's context, with sources and coverage kept so
the agent can cite what it says and admit what was not searched.

    scan_prior_art    domains, papers, trials, open projects, patents, local players
    find_domains      Vanigam registry domains for an idea, with fit per district
    support_for       schemes and incubators for a registry domain and district
    build_roadmap     the domain-aware plan: variants, costs, licences, milestones, risks
    note_fact         store a fact the founder stated (district, stage, capital...)
"""

from __future__ import annotations

from typing import Any

from app.elicitation.session import ElicitationSession, Source
from app.elicitation.slots import BY_KEY, SLOTS
from app.planner import registry
from app.planner.plan import build_plan
from app.research import novelty
from app.research import scan as research

_FACT_KEYS = [s.key for s in SLOTS if not s.sensitive]

TOOLS: list[dict] = [
    {
        "name": "scan_prior_art",
        "description": (
            "Search what already exists for an idea: the research fields it touches, papers,"
            " clinical trials (health ideas), open-source projects, patents and Tamil Nadu"
            " startups, plus a crowded/active/sparse check for each part of the idea. Call it"
            " once the idea is clear enough to search, and again when the founder changes it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "idea": {"type": "string", "description": "The idea in one or two sentences."},
                "elements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 6,
                    "description": "Parts of the idea to check one by one.",
                },
                "queries": {
                    "type": "object",
                    "description": (
                        "Optional technical search terms per source (papers, trials, projects,"
                        " patents), when the founder's words are too everyday to search."
                    ),
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["idea"],
        },
    },
    {
        "name": "check_novelty",
        "description": (
            "Check novelty after scan_prior_art: whether each part of the idea exists, which"
            " pairs of parts rarely appear together, whether it exists in India and Tamil Nadu,"
            " and the ways to stand out that those gaps support. Pass the idea's parts as"
            " elements (2 to 6 short phrases)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "idea": {"type": "string"},
                "elements": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            },
            "required": ["idea"],
        },
    },
    {
        "name": "find_domains",
        "description": "Vanigam registry domains closest to the idea, with district fit.",
        "input_schema": {
            "type": "object",
            "properties": {"idea": {"type": "string"}},
            "required": ["idea"],
        },
    },
    {
        "name": "support_for",
        "description": (
            "Government schemes (with live open/closed status) and incubators for a registry"
            " domain, nearest to the founder's district first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain_id": {"type": "string"},
                "district": {"type": "string", "enum": list(registry.DISTRICTS)},
            },
            "required": ["domain_id"],
        },
    },
    {
        "name": "ask_council",
        "description": (
            "Ask the review panel: seven advisers (customer, technical, regulatory, cost, prior"
            " art, funding, devil's advocate) judge the idea from the evidence, and a vote gives"
            " an overall view, the main concern, alternatives and one question. Use it when the"
            " founder asks what you think, or before building the roadmap. Share its brief"
            " in your own words; do not list all seven opinions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"idea": {"type": "string"}},
            "required": ["idea"],
        },
    },
    {
        "name": "build_roadmap",
        "description": (
            "Build the roadmap from what is known: product variants, cost per unit and"
            " cost-cutting levers (when a deep pack exists), licences, milestones with months,"
            " and risks per phase. Use it after the founder confirms the objective."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "idea": {"type": "string"},
                "domain_id": {"type": "string"},
            },
            "required": ["idea"],
        },
    },
    {
        "name": "note_fact",
        "description": (
            "Record a fact the founder stated, so it is never asked again. Use the founder's"
            " own words for text facts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "enum": _FACT_KEYS},
                "value": {},
            },
            "required": ["key", "value"],
        },
    },
]


def _paper(p: dict) -> dict:
    return {k: p.get(k) for k in ("title", "year", "cited_by", "url")}


def compact_scan(r: dict) -> dict:
    """The scan without the bulk: enough to discuss and cite, small enough for context."""
    dom = r["associated_domains"]
    return {
        "fields": dom.get("fields", [])[:6],
        "subfields": dom.get("subfields", [])[:6],
        "domain_basis": dom["basis"],
        "vanigam_categories": r["vanigam_categories"],
        "papers": {
            "total": r["papers"]["total"],
            "recent_years": dict(sorted(r["papers"]["by_year"].items())[-5:]),
            "most_relevant": [_paper(p) for p in r["papers"]["most_relevant"][:5]],
            "most_cited": [_paper(p) for p in r["papers"]["most_cited"][:3]],
        },
        "trials": {
            "total": r["trials"]["total"],
            "items": [
                {k: t.get(k) for k in ("id", "title", "status", "sponsor", "url")}
                for t in r["trials"]["items"][:5]
            ],
        },
        "projects": {
            "total": r["projects"]["total"],
            "items": [
                {k: g.get(k) for k in ("name", "description", "stars", "url")}
                for g in r["projects"]["items"][:5]
            ],
        },
        "patents": {"total": r["patents"]["total"], "items": r["patents"]["items"][:5]},
        "local": r["local"],
        "elements": [{k: e[k] for k in ("element", "label", "papers")} for e in r["elements"]],
        "discuss": r["discuss"],
        "coverage": r["coverage"],
        "caveat": r["caveat"],
    }


def _domain_row(d: dict) -> dict:
    return {
        "id": d["id"],
        "label": d["label"],
        "category": d["category"],
        "summary": d["summary"],
        "district_fit": {k: registry.fit(d, k) for k in registry.DISTRICTS},
        "has_deep_pack": bool(d.get("pack")),
    }


def _find_domains(idea: str) -> dict:
    doms = registry.load()["domains"]
    rows = []
    if best := registry.detect_domain(idea):
        rows.append(_domain_row(doms[best]))
    rows += [
        _domain_row(doms[x["id"]])
        for x in research._local(idea)["registry_domains"]
        if x["id"] != best
    ][:4]
    return {"domains": rows, "note": "" if rows else "No registry domain matches this idea yet."}


def _support_for(domain_id: str, district: str | None) -> dict:
    d = registry.load()["domains"].get(domain_id)
    if d is None:
        return {"error": f"unknown domain {domain_id}"}
    return {
        "domain": d["label"],
        "schemes": registry.schemes_for(d),
        "incubators": registry.incubators_for(d, district)[:6],
    }


def _roadmap(
    idea: str, domain_id: str | None, session: ElicitationSession, council: dict | None = None
) -> dict:
    slots = {k: getattr(v.value, "value", v.value) for k, v in session.slots.items()}
    p = build_plan(idea, slots, domain=domain_id, council=council)
    costs, road = p.get("costs") or {}, p.get("roadmap") or {}
    return {
        "domain": p.get("domain"),
        "domain_note": p.get("domain_note"),
        "variants": [v["label"] for v in p.get("variants", [])],
        "costs": {k: costs.get(k) for k in ("unit", "rows", "levers", "note") if costs.get(k)},
        "regulatory": [
            {k: r.get(k) for k in ("title", "text", "confidence", "source")}
            for r in p.get("regulatory") or []
        ],
        "milestones": [
            {k: m.get(k) for k in ("title", "phase", "months", "risks")}
            for m in road.get("milestones", [])
        ],
        "months_realistic": road.get("months_realistic"),
        "gates": p.get("gates", []),
        "risks_by_phase": {
            ph: [{k: r[k] for k in ("label", "level", "why")} for r in rows]
            for ph, rows in (p.get("risks_by_phase") or {}).items()
        },
        "next_questions": p.get("next_questions"),
    }


def council_brief(r: dict) -> dict:
    """The council result as the model needs it: the brief, not the bulk."""
    v = r["vote"]
    return {
        "band": v["band"],
        "brief": r["synthesis"]["voice_brief"],
        "question": r["synthesis"]["question"],
        "blockers": v["blockers"],
        "variants": [x["text"] for x in v["variants"]],
        "stances": v["stances"],
        "basis": r["basis"],
    }


def _note_fact(key: str, value: Any, session: ElicitationSession) -> dict:
    if key not in BY_KEY or BY_KEY[key].sensitive:
        return {"error": f"{key} is not a fact the agent may record"}
    session.put(key, value, 0.8, Source.EXTRACTED)
    return {"recorded": key}


async def run_tool(name: str, args: dict, session: ElicitationSession, state: dict) -> dict:
    """Dispatch one tool call. `state` keeps the latest scan for the response."""
    try:
        if name == "scan_prior_art" and "search" in state:
            # the conversation's job board: the turn waits briefly, never 20 s
            done = await state["search"](args)
            if done is None:
                return {
                    "status": "searching",
                    "note": "The search is still running; its results reach you on a later"
                    " turn. Tell the founder you are looking it up, then ask your question.",
                }
            state["scan"] = state["last_scan"] = done["scan"]
            state["novelty"] = done["novelty"]
            return compact_scan(done["scan"])
        if name == "scan_prior_art":
            r = await research.scan(
                args["idea"],
                elements=args.get("elements"),
                queries=args.get("queries"),
                private=state.get("private", False),
            )
            state["scan"] = state["last_scan"] = r
            return compact_scan(r)
        if name == "check_novelty":
            beneficiary = session.slots.get("beneficiary")
            r = await novelty.check(
                args["idea"],
                elements=args.get("elements"),
                scan=state.get("last_scan"),
                beneficiary=(
                    str(getattr(beneficiary.value, "value", beneficiary.value))
                    if beneficiary
                    else None
                ),
                private=state.get("private", False),
            )
            state["novelty"] = r
            return r
        if name == "find_domains":
            return _find_domains(args["idea"])
        if name == "support_for":
            return _support_for(args["domain_id"], args.get("district"))
        if name == "ask_council":
            r = await state["convene"](args["idea"])
            if r is None:  # the panel runs on in the background
                return {
                    "status": "still deliberating",
                    "note": "Tell the founder the review panel is still looking at the idea and"
                    " that you will share its view next; then ask your question.",
                }
            return council_brief(r)
        if name == "build_roadmap":
            r = _roadmap(args["idea"], args.get("domain_id"), session, state.get("council"))
            state["roadmap"] = r
            return r
        if name == "note_fact":
            return _note_fact(args["key"], args["value"], session)
    except (KeyError, ValueError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {"error": f"unknown tool {name}"}
