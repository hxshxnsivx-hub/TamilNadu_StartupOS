"""The council's shared evidence, one stable ID per fact.

Every seat judges the same pack, and every claim a seat makes must cite IDs from
it (build spec 7.2). IDs are readable so a founder can follow a claim back:

    paper:3  trial:NCT01234567  repo:lab/eeg-bci  startup:acme-health
    scheme:pmegp  reg:fssai  incubator:aic_au  risk:regulatory  pack:banana_value_added
    novelty:statement  novelty:pair:0  novelty:context  field:neuroscience
    coverage:patents  (a source that was not searched, so "nothing" is never claimed)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.planner import registry
from app.research.terms import is_health


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


@dataclass
class EvidencePack:
    items: dict[str, dict] = field(default_factory=dict)
    domain_id: str | None = None
    # A health idea by its own words, or trials actually found. Papers that merely touch
    # medicine do not count: "tea infusions" once read as a medical device.
    health: bool = False

    def add(self, id_: str, kind: str, text: str, **extra) -> None:
        self.items[id_] = {"kind": kind, "text": text, **extra}

    @property
    def ids(self) -> set[str]:
        return set(self.items)

    def lines(self, kinds: set[str] | None = None) -> str:
        """The pack as `id | text` lines; `kinds` limits it to one seat's slice."""
        return "\n".join(
            f"{i} | {it['text']}"
            for i, it in self.items.items()
            if kinds is None or it["kind"] in kinds
        )

    def of(self, *kinds: str) -> list[tuple[str, dict]]:
        return [(i, it) for i, it in self.items.items() if it["kind"] in kinds]


def build(idea: str, scan: dict | None, novelty: dict | None, district: str | None) -> EvidencePack:
    pack = EvidencePack()
    s = scan or {}
    pack.health = is_health(idea) or bool(s.get("trials", {}).get("total"))

    for f in s.get("associated_domains", {}).get("fields", [])[:6]:
        share = f" ({f['share_pct']}% of matching papers)" if f.get("share_pct") else ""
        pack.add(f"field:{_slug(f['name'])}", "field", f"Research field: {f['name']}{share}")

    papers = s.get("papers", {})
    if papers.get("total"):
        pack.add("papers:total", "papers", f"{papers['total']} research papers match the idea")
    for i, p in enumerate(papers.get("most_relevant", [])[:5]):
        pack.add(
            f"paper:{i}",
            "papers",
            f"Paper: {p.get('title')} ({p.get('year')}, cited {p.get('cited_by', 0)} times)",
            url=p.get("url"),
        )

    trials = s.get("trials", {})
    if trials.get("total"):
        pack.add("trials:total", "trials", f"{trials['total']} clinical trials match")
    for t in trials.get("items", [])[:5]:
        if t.get("id"):
            pack.add(
                f"trial:{t['id']}",
                "trials",
                f"Trial {t['id']}: {t.get('title')} ({t.get('status')},"
                f" sponsor {t.get('sponsor')})",
                url=t.get("url"),
            )

    projects = s.get("projects", {})
    if projects.get("total"):
        pack.add("projects:total", "projects", f"{projects['total']} open-source projects match")
    for g in projects.get("items", [])[:5]:
        if g.get("name"):
            pack.add(
                f"repo:{g['name']}",
                "projects",
                f"Open project {g['name']}: {g.get('description') or ''} ({g.get('stars', 0)}"
                " stars)",
                url=g.get("url"),
            )

    for p in s.get("patents", {}).get("items", [])[:5]:
        pack.add(f"patent:{p.get('id')}", "patents", f"Patent: {p.get('title')} ({p.get('date')})")

    for st in s.get("local", {}).get("startups", [])[:5]:
        pack.add(
            f"startup:{_slug(st['name'])}",
            "local",
            f"Tamil Nadu startup {st['name']} ({st.get('district')}):"
            f" {st.get('description') or ''}",
        )
    if s and not s.get("local", {}).get("startups"):
        pack.add("local:none", "local", "No Tamil Nadu startup matching the idea was found")

    for c in s.get("coverage", []):
        if c["status"] != "ok":
            pack.add(
                f"coverage:{c['source']}",
                "coverage",
                f"{c['source']} not searched ({c['status']}): {c.get('note', '')}",
            )

    _add_novelty(pack, novelty)
    _add_registry(pack, idea, s, district)
    return pack


def _add_novelty(pack: EvidencePack, novelty: dict | None) -> None:
    if not novelty:
        return
    st = novelty.get("statement", {})
    if st:
        pack.add("novelty:statement", "novelty", f"Novelty ({st.get('type')}): {st.get('text')}")
    for i, p in enumerate(novelty.get("pairs", [])[:6]):
        rare = "rare together" if p["gap"] else "studied together"
        pack.add(
            f"novelty:pair:{i}",
            "novelty",
            f"{p['a']} ({p['a_papers']} papers) with {p['b']} ({p['b_papers']}): {p['papers']}"
            f" papers cover both, {rare}",
        )
    ctx = novelty.get("context", {})
    if ctx.get("searched") and ctx.get("world_papers") is not None:
        share = ctx.get("india_share_pct")
        pack.add(
            "novelty:context",
            "novelty",
            f"{ctx.get('india_papers')} of {ctx['world_papers']} matching papers are"
            f" India-affiliated"
            + (f" ({share}%)" if share is not None else "")
            + f"; Tamil Nadu startups found: {ctx.get('tn_startups', 0)}",
        )
    for i, lv in enumerate(novelty.get("levers", [])[:4]):
        pack.add(f"novelty:lever:{i}", "novelty", f"Way to stand out ({lv['kind']}): {lv['text']}")


def _add_registry(pack: EvidencePack, idea: str, scan: dict, district: str | None) -> None:
    doms = registry.load()["domains"]
    ids = [registry.detect_domain(idea)] + [
        d["id"] for d in scan.get("local", {}).get("registry_domains", [])
    ]
    domain_id = next((i for i in ids if i and i in doms), None)
    if domain_id is None:
        return
    pack.domain_id = domain_id
    card = registry.card(doms[domain_id], district)
    buyers = ", ".join(card.get("buyers") or [])
    pack.add(
        f"domain:{domain_id}",
        "domain",
        f"Closest Vanigam domain: {card['label']} ({card['category_label']}). {card['summary']}"
        + (f" Buyers: {buyers}." if buyers else ""),
    )
    for r in card.get("regulatory_items", []):
        pack.add(f"reg:{r['id']}", "regulatory", f"Licence: {r['title']}. {r['text']}")
    for sc in card.get("schemes", []):
        pack.add(
            f"scheme:{sc['id']}",
            "funding",
            f"Scheme {sc['name']} ({sc['status']}): {sc['benefit']}",
        )
    for inc in card.get("incubators", [])[:3]:
        where = " (another district)" if inc.get("elsewhere") else ""
        pack.add(f"incubator:{inc['id']}", "funding", f"Incubator {inc['name']}{where}")
    for kind, level in (card.get("risk") or {}).items():
        if level >= 2:
            pack.add(f"risk:{kind}", "risk", f"Registry risk level for {kind}: {level} of 3")
    if card.get("pack"):
        pack.add(
            f"pack:{card['pack']}",
            "cost",
            "A Vanigam cost pack exists for this domain: recipes, unit costs and cost levers",
        )
