"""Prior-art scan for any idea: which domains it touches and what already exists.

    idea text (+ optional elements and queries from the agent's language model)
      -> search terms (terms.py)
      -> papers, trials, open projects, patents, local startups (sources.py), in parallel
      -> associated domains: the OpenAlex topic hierarchy (domain > field >
         subfield > topic) counted across the matching papers, weighted by each
         topic's score — the fields the idea really sits in, found from evidence
      -> element check: each part of the idea searched alone and labelled
         crowded / active / sparse / nothing found
      -> what to discuss: the questions each discovered field raises
      -> coverage: what was searched, what was not and why

The labels are heuristics on counts, stated as such. "Nothing found" means
nothing in the sources searched, not that the idea is new; a patent attorney's
search is still needed before filing.
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter

import httpx

from app.core.config import get_settings
from app.research import sources
from app.research.terms import SPECIFIC, build_queries, expand, fields_from_terms, is_health

# OpenAlex fields -> Vanigam registry categories (for schemes, incubators, packs).
FIELD_TO_CATEGORY = {
    "Medicine": "health_bio",
    "Neuroscience": "health_bio",
    "Health Professions": "health_bio",
    "Nursing": "health_bio",
    "Psychology": "health_bio",
    "Biochemistry, Genetics and Molecular Biology": "health_bio",
    "Pharmacology, Toxicology and Pharmaceutics": "health_bio",
    "Computer Science": "ai_ml",
    "Engineering": "electrical",
    "Agricultural and Biological Sciences": "agriculture",
    "Environmental Science": "climate",
    "Energy": "renewable",
    "Materials Science": "electrical",
    "Economics, Econometrics and Finance": "fintech",
    "Business, Management and Accounting": "saas",
}
# What a founder should be ready to discuss when the idea touches a field.
FIELD_QUESTIONS = {
    "Medicine": [
        "Which patients exactly, and which hospital or clinician will run a validation study?",
        "What medical device class would this be under CDSCO, and what testing does that need?",
        "Who pays: hospital, insurer, government scheme or family?",
    ],
    "Neuroscience": [
        "Which signal do you rely on (EEG, EMG, eye movement), and how reliable is it at the"
        " bedside?",
        "How long does a patient need to train or calibrate, and who supervises it?",
    ],
    "Health Professions": [
        "How does it fit the nurse's or caregiver's routine without adding work?",
    ],
    "Nursing": [
        "Who answers the alert at night, and how fast must they respond?",
        "Does it plug into the hospital's existing nurse-call system or replace it?",
    ],
    "Psychology": ["How do you measure that users can and will use it day to day?"],
    "Computer Science": [
        "What data trains the model, who owns it, and what accuracy is good enough to act on?",
        "Does it run on the device or in the cloud, and what happens offline?",
    ],
    "Engineering": [
        "Which sensors and hardware, at what unit cost, and how durable in Indian conditions?",
        "What certification does the hardware need before sale?",
    ],
    "Agricultural and Biological Sciences": [
        "Which crop or animal, which season, and which FPO or farmers will pilot it?",
    ],
    "Environmental Science": ["What is measured, by whom, and who pays for the improvement?"],
    "Energy": ["What does it cost per unit of energy saved or produced, and who finances it?"],
    "Economics, Econometrics and Finance": [
        "Which regulated entity (bank, NBFC, insurer) do you partner with?"
    ],
}
# Words too common to count as a match on their own.
GENERIC = {
    "based",
    "care",
    "communication",
    "company",
    "digital",
    "health",
    "india",
    "management",
    "patient",
    "patients",
    "people",
    "platform",
    "product",
    "products",
    "services",
    "solutions",
    "system",
    "systems",
    "technologies",
    "technology",
}
GENERAL_QUESTIONS = [
    "Who is the first buyer, and what do they use today instead?",
    "What exactly is new compared with the closest prior art found?",
    "Which part could be protected (patent, design, trademark), and which is already public?",
]


def associated_domains(works: list[dict], top: int = 8) -> dict:
    fields, subfields, topics, domains = Counter(), Counter(), Counter(), Counter()
    for w in works:
        for t in w["topics"]:
            s = float(t.get("score") or 0) or 0.5
            if t["field"]:
                fields[t["field"]] += s
            if t["subfield"]:
                subfields[t["subfield"]] += s
            if t["topic"]:
                topics[t["topic"]] += s
            if t["domain"]:
                domains[t["domain"]] += s
    total = sum(fields.values()) or 1

    def ranked(c: Counter) -> list[dict]:
        return [{"name": k, "share_pct": round(100 * v / total)} for k, v in c.most_common(top)]

    return {
        "domains": ranked(domains),
        "fields": ranked(fields),
        "subfields": ranked(subfields),
        "topics": ranked(topics),
    }


def _local(text: str) -> dict:
    """Tamil Nadu startups and Vanigam registry domains that share the idea's words."""
    technical, content = expand(text)
    anchors = {
        w for t in technical if t in SPECIFIC for w in re.findall(r"[a-z]{3,}", t.lower())
    } - GENERIC
    words = ({w for w in content if len(w) > 3} | anchors) - GENERIC
    out: dict = {"startups": [], "registry_domains": []}
    try:
        from app.ecosystem.index import get_ecosystem
        from app.planner import registry

        eco = get_ecosystem()
        if eco:
            scored = []
            for s in eco.startups:
                vocab = set(
                    re.findall(r"[a-z]{4,}", f"{s.get('name')} {s.get('description')}".lower())
                )
                hit = len(words & vocab)
                if hit >= 2 and (not anchors or anchors & vocab):
                    scored.append((hit, s))
            scored.sort(key=lambda t: -t[0])
            out["startups"] = [
                {"name": s["name"], "district": s["district"], "description": s.get("description"),
                 "url": s.get("website") or s.get("source_url")}
                for _, s in scored[:5]
            ]  # fmt: skip
        for d in registry.load()["domains"].values():
            vocab = set(re.findall(r"[a-z]{4,}", f"{d['label']} {d['summary']}".lower()))
            if len(words & vocab) >= 2 and (not anchors or anchors & vocab):
                out["registry_domains"].append({"id": d["id"], "label": d["label"]})
    except Exception:  # local data is a bonus; never fail the scan over it
        pass
    return out


def _label(papers_total: int | None, projects_total: int | None) -> str:
    """Papers are the main evidence; open projects only support it (GitHub matches loosely)."""
    if papers_total is None:
        return "not enough evidence (papers not searched)"
    if papers_total >= 5000 or (papers_total >= 1000 and (projects_total or 0) >= 50):
        return "crowded"
    if papers_total >= 300:
        return "active"
    if papers_total > 0 or (projects_total or 0) > 0:
        return "sparse"
    return "nothing found"


async def scan(
    text: str,
    *,
    elements: list[str] | None = None,
    queries: dict[str, str] | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict:
    settings = get_settings()
    q = {**build_queries(text), **(queries or {})}
    cache = sources.Cache(settings.research_cache_dir, settings.research_cache_days)
    own = client is None
    client = client or httpx.AsyncClient(timeout=60, headers={"User-Agent": sources.UA})
    try:
        health = is_health(f"{text} {q['papers']}")
        tasks = [
            sources.papers(client, q["papers"], cache),
            sources.projects(client, q["projects"], cache),
            sources.patents(client, q["patents"], cache),
        ]
        if health:
            tasks.append(sources.trials(client, q["trials"], cache))
        results = {r.source: r for r in await asyncio.gather(*tasks)}
        if not health:
            results["trials"] = sources.SourceResult(
                "trials", "skipped", note="Not a health idea, so clinical trials were not searched"
            )

        element_rows = []
        for el in elements or []:
            eq = build_queries(el)
            p, g = await asyncio.gather(
                sources.papers(client, eq["papers"], cache),
                sources.projects(client, eq["projects"], cache),
            )
            pt = p.total if p.status == "ok" else None
            gt = g.total if g.status == "ok" else None
            element_rows.append({
                "element": el,
                "query": eq["papers"],
                "papers": pt,
                "projects": gt,
                "label": _label(pt, gt),
                "closest": (p.items[:1] or g.items[:1] or [None])[0],
            })  # fmt: skip
    finally:
        if own:
            await client.aclose()

    paper = results["papers"]
    if paper.status == "ok" and paper.items:
        domains = {"basis": "papers", **associated_domains(paper.items)}
    else:  # lower confidence: the fields the technical terms belong to
        guess = fields_from_terms(f"{text} {q['papers']}")
        domains = {
            "basis": "terms (papers not searched — lower confidence)",
            "fields": [{"name": f, "share_pct": None} for f in guess],
        }
    fields = [f["name"] for f in domains.get("fields", [])]
    categories = sorted({FIELD_TO_CATEGORY[f] for f in fields if f in FIELD_TO_CATEGORY})
    questions = [
        {"field": f, "questions": FIELD_QUESTIONS[f]} for f in fields if f in FIELD_QUESTIONS
    ]
    coverage = [
        {"source": r.source, "status": r.status, "found": r.total, "note": r.note}
        for r in results.values()
    ]
    return {
        "idea": text,
        "queries": q,
        "associated_domains": domains,
        "vanigam_categories": categories,
        "papers": {
            "total": paper.total,
            "by_year": paper.extra.get("by_year", {}),
            "most_relevant": paper.items[:8],
            "most_cited": paper.extra.get("most_cited", []),
        },
        "trials": {"total": results["trials"].total, "items": results["trials"].items},
        "projects": {"total": results["projects"].total, "items": results["projects"].items},
        "patents": {"total": results["patents"].total, "items": results["patents"].items},
        "local": _local(text),
        "elements": element_rows,
        "discuss": questions + [{"field": "Any idea", "questions": GENERAL_QUESTIONS}],
        "coverage": coverage,
        "caveat": (
            "Counts come from the sources listed in coverage. 'Nothing found' means nothing in"
            " those sources, not that the idea is new; have a patent attorney search before"
            " filing."
        ),
    }
