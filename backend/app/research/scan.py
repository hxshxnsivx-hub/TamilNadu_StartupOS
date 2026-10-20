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
from app.research.terms import (
    BENEFICIARY,
    STOP,
    build_queries,
    expand,
    fields_from_terms,
    filler,
    is_health,
    is_place,
    scrub,
    term_groups,
)

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
CLINICAL_FIELDS = {"Medicine", "Nursing", "Health Professions"}
# Words inside lexicon terms ("augmentative and alternative communication", "water use
# efficiency") and company names that say nothing about a product: never an anchor.
FUNCTION_WORDS = {"and", "the", "for", "with", "use", "via", "pvt", "ltd"}
# The research fields that fit each registry category: once the idea matches a registry
# domain, only these fields raise discussion points ("which sensors and hardware?" is
# no question for a banana-chips unit, though its papers touch Engineering).
CATEGORY_FIELDS = {
    "agriculture": {"Agricultural and Biological Sciences"},
    "textile": {"Materials Science"},
    "health_bio": {
        "Medicine",
        "Neuroscience",
        "Health Professions",
        "Nursing",
        "Psychology",
        "Pharmacology, Toxicology and Pharmaceutics",
        "Biochemistry, Genetics and Molecular Biology",
    },
    "logistics": {"Engineering", "Computer Science"},
    "electrical": {"Engineering", "Energy", "Computer Science"},
    "renewable": {"Energy", "Engineering"},
    "climate": {"Environmental Science", "Energy"},
    "fintech": {"Economics, Econometrics and Finance"},
    "it": {"Computer Science"},
    "iot": {"Engineering", "Computer Science"},
    "ai_ml": {"Computer Science"},
    "saas": {"Computer Science", "Business, Management and Accounting"},
}
# Startup-map sectors that sit next to a domain's own: a banana-chips brand may be
# listed as food, agritech or consumer.
RELATED_SECTORS = {
    "food": {"consumer", "agritech"},
    "agritech": {"food"},
    "textiles": {"consumer", "manufacturing"},
}
LOCAL_SOURCE = "Tamil Nadu Startup Map"
# A paper is named as the closest only when its title shares this share of the query's
# words (and at least two of them, one naming the product).
CLOSEST_SHARE = 1 / 3
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


def matched_domain(text: str) -> dict | None:
    """The registry card the roadmap would use for these words: a deep pack's cue
    words first, then word overlap (the same order as build_plan)."""
    from app.planner import registry
    from app.planner.packs import detect_pack

    doms = registry.load()["domains"]
    pack = detect_pack(text)
    card = next((d for d in doms.values() if pack and d.get("pack") == pack), None)
    if card is None and (found := registry.detect_domain(text)):
        card = doms.get(found)
    return card


def domain_id(idea: str, found: dict | None) -> str | None:
    """The idea's one registry domain (R044): the one a scan matched, or matched now the
    same way when there is no scan. The related domains a scan also lists are never
    taken as the idea's own."""
    if found and "matched_domain" in found:
        return found["matched_domain"]
    card = matched_domain(idea)
    return card["id"] if card else None


def _sectors(domain: dict | None) -> set[str]:
    """Startup-map sectors that fit the matched domain; empty means no sector filter."""
    if not domain:
        return set()
    from app.planner import registry

    cat = registry.load()["categories"].get(domain["category"], {})
    own = {domain.get("sector"), cat.get("sector")} - {None}
    return own | {r for s in own for r in RELATED_SECTORS.get(s, set())}


def _anchors(text: str) -> set[str]:
    """Words of the lexicon terms for what is built (not for who is served)."""
    return {
        w
        for phrase, terms in term_groups(text)
        if phrase not in BENEFICIARY
        for t in terms
        for w in re.findall(r"[a-z]{3,}", t.lower())
    } - (GENERIC | STOP | FUNCTION_WORDS | filler())


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _local(text: str, domain: dict | None = None) -> dict:
    """Tamil Nadu startups and Vanigam registry domains that share the idea's words.

    A startup must share two of the idea's words (places and filler do not count), one
    of them naming the product when the lexicon knows it, and sit in a sector that fits
    the matched domain (1.2.1.3): a wrong name costs more trust than a missed one. The
    result says what was searched, so "none found" never reads as "none exist" (R023).
    """
    _, content = expand(text)
    anchors = _anchors(text)
    words = {w for w in content if len(w) > 3 and not is_place(w)} | anchors
    words -= GENERIC | STOP | FUNCTION_WORDS | filler()
    sectors = _sectors(domain)
    out: dict = {"status": "ok", "startups": [], "registry_domains": []}
    try:
        from app.ecosystem.index import get_ecosystem
        from app.planner import registry

        eco = get_ecosystem()
        if eco is None:
            out.update(status="error", note="Tamil Nadu startup data is not installed")
        else:
            districts = [d.title() for d in eco.meta.get("districts", [])]
            out.update(
                searched=len(eco.startups),
                districts=districts,
                scope=(
                    f"the {len(eco.startups):,} startups on the {LOCAL_SOURCE} in"
                    f" {_join(districts)}"
                ),
                sectors=sorted(sectors),
            )
            scored = []
            for s in eco.startups:
                if sectors and not sectors & set(s.get("sectors") or []):
                    continue
                vocab = set(
                    re.findall(r"[a-z]{3,}", f"{s.get('name')} {s.get('description')}".lower())
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
        if domain:
            out["registry_domains"].append({"id": domain["id"], "label": domain["label"]})
        for d in registry.load()["domains"].values():
            if domain and d["id"] == domain["id"]:
                continue
            vocab = set(re.findall(r"[a-z]{3,}", f"{d['label']} {d['summary']}".lower()))
            if len(words & vocab) >= 2 and (not anchors or anchors & vocab):
                out["registry_domains"].append({"id": d["id"], "label": d["label"]})
    except Exception as e:  # local data is a bonus; never fail the scan over it
        out.update(status="error", note=f"Tamil Nadu startup data could not be read ({e})")
    return out


def _stem(w: str) -> str:
    """Light ending match for titles: interfaces/interface, inverters/inverter/invert."""
    if w.endswith("s") and not w.endswith("ss") and len(w) > 4:
        w = w[:-1]
    for suffix in ("ing", "er"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            return w[: -len(suffix)]
    return w


def _query_words(text: str) -> set[str]:
    """Words of a query or title; hyphens and dashes split ("brain–computer", "EEG-based")."""
    return {_stem(w) for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in STOP | filler()}


def closest_paper(items: list[dict], query: str, idea: str) -> dict | None:
    """The paper to name as the closest, or None when none is close enough (1.2.1.2).

    The title must share at least two of the query's words and a third of them, one
    of them naming the product; among those, the one sharing most wins, search rank
    breaking ties. "Solomon Islands Smallholder Agriculture Study" is not the closest
    paper to a banana-chips unit, however the search ranked it.
    """
    want = _query_words(query)
    if not want:
        return None
    anchors = ({_stem(w) for w in _anchors(idea)} & want) or want
    best, best_n = None, 0
    for p in items:
        title = _query_words(p.get("title") or "")
        n = len(want & title)
        if n >= 2 and n >= CLOSEST_SHARE * len(want) and anchors & title and n > best_n:
            best, best_n = p, n
    return best


def _discuss(fields: list[str], domain: dict | None, clinical_ok: bool) -> list[dict]:
    """What to think through: the matched domain's own points first, then the questions
    of the research fields that fit it (every field when no domain matched)."""
    out: list[dict] = []
    allowed = CATEGORY_FIELDS.get(domain["category"]) if domain else None
    if domain:
        from app.planner import registry

        regs = registry.load()["regulatory"]
        points = []
        if buyers := domain.get("buyers"):
            points.append(f"Which buyer comes first ({_join(buyers)}), and what do they use today?")
        if titles := [regs[r]["title"] for r in domain.get("regulatory", []) if r in regs]:
            points.append(f"Which of these do you need before the first sale: {_join(titles)}?")
        if points:
            out.append({"field": domain["label"], "questions": points})
    out += [
        {"field": f, "questions": FIELD_QUESTIONS[f]}
        for f in fields
        if f in FIELD_QUESTIONS
        and (allowed is None or f in allowed)
        and (clinical_ok or f not in CLINICAL_FIELDS)
    ]
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
    private: bool = False,
) -> dict:
    """`private`: search nothing outside Vanigam; only local data is used."""
    settings = get_settings()
    own_q = {k: scrub(v, text) for k, v in (queries or {}).items()}  # model-written: cleaned
    q = {**build_queries(text), **{k: v for k, v in own_q.items() if v}}
    cache = sources.Cache(settings.research_cache_dir, settings.research_cache_days)
    own = client is None
    client = client or httpx.AsyncClient(timeout=60, headers={"User-Agent": sources.UA})
    try:
        health = is_health(f"{text} {q['papers']}")

        async def search(name: str, fn, query: str) -> sources.SourceResult:
            if private:
                return sources.SourceResult(name, "private", note="Private mode: not searched")
            if not query.strip():
                return sources.SourceResult(
                    name, "skipped", note="Not searched: no technical terms safe to send"
                )
            return await fn(client, query, cache)

        tasks = [
            search("papers", sources.papers, q["papers"]),
            search("projects", sources.projects, q["projects"]),
            search("patents", sources.patents, q["patents"]),
        ]
        if health:
            tasks.append(search("trials", sources.trials, q["trials"]))
        results = {r.source: r for r in await asyncio.gather(*tasks)}
        if not health:
            results["trials"] = sources.SourceResult(
                "trials", "skipped", note="Not a health idea, so clinical trials were not searched"
            )

        element_rows = []
        for el in elements or []:
            eq = build_queries(el)
            p, g = await asyncio.gather(
                search("papers", sources.papers, eq["papers"]),
                search("projects", sources.projects, eq["projects"]),
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
    domain = matched_domain(text)
    # One clinical gate for questions and categories alike (R035): herbal-tea papers list
    # Medicine as a field, but "which patients?" is no question for a tea brand, and the
    # tea brand is no health product.
    clinical_ok = health or results["trials"].total > 0
    categories = {FIELD_TO_CATEGORY[f] for f in fields if f in FIELD_TO_CATEGORY}
    if not clinical_ok:
        categories.discard("health_bio")
    if domain:
        categories.add(domain["category"])
    local = _local(text, domain)
    coverage = [
        {"source": r.source, "status": r.status, "found": r.total, "note": r.note}
        for r in results.values()
    ] + [
        {
            "source": "local startups",
            "status": local["status"],
            "found": len(local["startups"]),
            "note": f"Only {local['scope']}" if local["status"] == "ok" else local["note"],
        }
    ]
    return {
        "idea": text,
        "queries": q,
        "associated_domains": domains,
        "vanigam_categories": sorted(categories),
        "matched_domain": domain["id"] if domain else None,
        "papers": {
            "total": paper.total,
            "closest": closest_paper(paper.items[:8], q["papers"], text),
            "by_year": paper.extra.get("by_year", {}),
            "most_relevant": paper.items[:8],
            "most_cited": paper.extra.get("most_cited", []),
        },
        "trials": {"total": results["trials"].total, "items": results["trials"].items},
        "projects": {"total": results["projects"].total, "items": results["projects"].items},
        "patents": {
            "total": results["patents"].total,
            "items": results["patents"].items,
            # Indian filings among them, when the source can tell (EPO)
            "india": results["patents"].extra.get("india"),
        },
        "local": local,
        "elements": element_rows,
        "discuss": _discuss(fields, domain, clinical_ok)
        + [{"field": "Any idea", "questions": GENERAL_QUESTIONS}],
        "coverage": coverage,
        "caveat": (
            "Counts come from the sources listed in coverage. 'Nothing found' means nothing in"
            " those sources, not that the idea is new; have a patent attorney search before"
            " filing."
        ),
    }
