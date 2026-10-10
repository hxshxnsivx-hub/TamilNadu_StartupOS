"""The domain registry: product domains under StartupTN's categories, and hybrids.

A domain card (data/registry/domains.json) says what the product is, who buys
it, how well it fits each pilot district, which capabilities it needs and
offers, its typical risks, and which regulatory items apply (by id, from the
shared library, each with a confidence and a source). Schemes are NOT written
into cards: they follow from rules over the card, and each scheme's live
status comes from the funding catalogue, so a closed scheme shows as closed.

Hybrids ("cross-breeding"): domain A paired with domain B from a neighbouring
category, where B is a product A's kind of business uses (B "serves" A's
category) and B offers a capability A needs. The hybrid inherits both
domains' scheme routes — often a route neither had alone — and both domains'
risks plus an integration risk.

Adding domains is a data change: add a domains_batch<N>.json file. Cards
carry their batch and a review state ("base", "draft", "approved").
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data" / "registry"
CATALOGUE = Path(__file__).parents[1] / "schemes" / "data" / "funding_catalogue.json"
INCUBATORS = Path(__file__).parents[1] / "ecosystem" / "data" / "incubators.json"
DISTRICTS = ("chennai", "coimbatore", "tiruppur", "madurai", "tiruchirappalli")
SMALL_CAPITAL = {"under_2L", "2L_10L", "10L_50L"}
# Routes nearly every small business qualifies for; a hybrid does not "gain" them.
UNIVERSAL_ROUTES = {"cgtmse", "needs", "pmegp", "mse_cdp"}
GOVT_BUYERS = (
    "government",
    "local bodies",
    "municipal",
    "panchayat",
    "primary health",
    "state departments",
)


@lru_cache
def load() -> dict:
    cats = json.loads((DATA / "categories.json").read_text(encoding="utf8"))
    regs = json.loads((DATA / "regulatory.json").read_text(encoding="utf8"))["items"]
    # domains.json is batch 1; later batches live in domains_batch<N>.json and are merged.
    doms = json.loads((DATA / "domains.json").read_text(encoding="utf8"))
    batches = {1: doms["_meta"]}
    for extra in sorted(DATA.glob("domains_batch*.json")):
        more = json.loads(extra.read_text(encoding="utf8"))
        batches[more["_meta"]["batch"]] = more["_meta"]
        doms["domains"] += more["domains"]
    signals_path = DATA / "signals.json"
    signals = json.loads(signals_path.read_text(encoding="utf8")) if signals_path.exists() else {}
    return {
        "categories": {c["id"]: c for c in cats["categories"]},
        "capabilities": cats["capabilities"],
        "themes": cats["tanseed_themes"],
        "category_source": cats["_meta"],
        "regulatory": regs,
        "domains": {d["id"]: d for d in doms["domains"]},
        "risk_types": doms["_meta"]["risk_types"],
        "signals": signals,
        "batches": batches,
    }


@lru_cache
def _catalogue() -> dict[str, dict]:
    rows = json.loads(CATALOGUE.read_text(encoding="utf8"))["schemes"]
    return {r["id"]: r for r in rows}


@dataclass(frozen=True)
class SchemeRoute:
    id: str
    why: str


def _scheme_rules(d: dict) -> list[SchemeRoute]:
    forms = set(d.get("forms", []))
    cat, sector = d["category"], d.get("sector")
    buyers = " ".join(d.get("buyers", [])).lower()
    out: list[SchemeRoute] = []

    def add(sid: str, why: str) -> None:
        out.append(SchemeRoute(sid, why))

    if d.get("theme"):
        add("tanseed", f"matches the TANSEED theme '{d['theme']}'")
    if d.get("theme") and cat in ("agriculture", "climate"):
        add("gramam_thorum_puthozhil", "a rural livelihood venture")
    if cat == "health_bio" or sector == "biotech_pharma":
        add("birac_big", "life-science product to proof of concept")
    if forms & {"physical", "hybrid"} and sector in (
        "electronics",
        "deeptech",
        "cleantech",
        "healthtech",
        "agritech",
        "biotech_pharma",
    ):
        add("nidhi_prayas", "technology prototype")
        add("tiic_proto", "prototype loan for a recognised startup")
    if forms & {"software", "hybrid"} and (
        cat in ("it", "iot", "ai_ml", "saas") or sector in ("saas", "deeptech")
    ):
        add("meity_samridh", "software or connected product")
        add("meity_genesis_investment", "tech startup outside the metros (matching equity)")
    if cat in ("ai_ml", "iot") or sector in ("deeptech", "biotech_pharma"):
        add("tn_deeptech_policy", "deep-tech product")
    if sector == "food":
        add("pmfme", "micro food processing")
    if forms & {"physical", "service"} and d.get("capital_band") in SMALL_CAPITAL:
        add("needs", "a first-generation manufacturing or service enterprise")
        add("pmegp", "a micro enterprise project")
    if d.get("theme") == "Art and Craft":
        add("kkt", "artisan venture")
        add("sfurti", "traditional-industry cluster")
    # MSE-CDP funds common facilities for manufacturing clusters: a physical product made
    # where the founder's industry clusters (a temple town or migration hub does not count).
    if "physical" in forms and any(f >= 3 for f, _ in d.get("districts", {}).values()):
        add("mse_cdp", "made in an established manufacturing cluster")
    if any(g in buyers for g in GOVT_BUYERS):
        add("gem_runway", "sells to government buyers")
    if "local bodies" in buyers or "municipal" in buyers:
        add("tanii", "solves a government department's problem")
    if d.get("capital_band") in SMALL_CAPITAL and forms & {"physical", "service", "hybrid"}:
        add("cgtmse", "collateral-free credit guarantee")
    seen, uniq = set(), []
    for r in out:
        if r.id not in seen:
            seen.add(r.id)
            uniq.append(r)
    return uniq


def schemes_for(d: dict) -> list[dict]:
    cat = _catalogue()
    rows = []
    for r in _scheme_rules(d):
        s = cat.get(r.id)
        if not s:
            continue
        rows.append(
            {
                "id": r.id,
                "name": s["name"],
                "why": r.why,
                "status": s["status"],
                "benefit": s["benefit"],
                "source_url": s.get("source_url"),
            }
        )
    return rows


@lru_cache
def _incubators() -> tuple[dict, ...]:
    if not INCUBATORS.exists():
        return ()
    return tuple(json.loads(INCUBATORS.read_text(encoding="utf8"))["incubators"])


def incubators_for(d: dict, district: str | None = None) -> list[dict]:
    want = {d.get("sector"), load()["categories"][d["category"]]["sector"]}
    rows = []
    for i in _incubators():
        if district and i["district"] != district:
            continue
        hit = want & set(i["sectors"])
        if hit or "general" in i["sectors"]:
            rows.append(
                {
                    "id": i["id"],
                    "name": i["name"],
                    "district": i["district"],
                    "focused": bool(hit),
                    "programmes": i["programmes"],
                }
            )
    rows.sort(key=lambda r: (not r["focused"], r["district"], r["name"]))
    if district and not rows:  # none in the founder's district: show the options elsewhere
        return [{**r, "elsewhere": True} for r in incubators_for(d)]
    return rows


def fit(d: dict, district: str) -> int:
    return d.get("districts", {}).get(district, [1, ""])[0]


def card(d: dict, district: str | None = None) -> dict:
    reg = load()["regulatory"]
    return {
        **d,
        "category_label": load()["categories"][d["category"]]["label"],
        "district_fit": {k: fit(d, k) for k in DISTRICTS},
        "regulatory_items": [{"id": r, **reg[r]} for r in d.get("regulatory", [])],
        "schemes": schemes_for(d),
        "incubators": incubators_for(d, district),
        "signals": load()["signals"].get("domains", {}).get(d["id"]),
    }


def domains(category: str | None = None, district: str | None = None) -> list[dict]:
    rows = [d for d in load()["domains"].values() if not category or d["category"] == category]
    if district:
        rows.sort(key=lambda d: (-fit(d, district), d["label"]))
    return rows


# Words too common to say anything about a domain ("a tea brand with mint" once matched a
# honey card on "with" and "brand").
_DETECT_STOP = frozenset(
    {
        "with", "from", "that", "this", "into", "than", "them", "they", "their", "there", "these",
        "those", "what", "when", "where", "which", "while", "your", "have", "will", "would",
        "about", "after", "under", "over", "sold", "sell", "sells", "selling", "brand", "brands",
        "make", "makes", "made", "using", "used", "small", "local", "based", "near", "more", "most",
        "also", "only",
    }
)  # fmt: skip


def _stem(w: str) -> str:
    """Light ending match: prices/price, knitters/knitting, units/unit."""
    for suffix in ("ings", "ing", "ers", "er", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            return w[: -len(suffix)]
    return w


def _terms(text: str) -> set[str]:
    return {
        _stem(w)
        for w in "".join(c if c.isalpha() else " " for c in (text or "").lower()).split()
        if len(w) > 3 and w not in _DETECT_STOP
    }


def detect_domain(text: str) -> str | None:
    """Best registry domain for free text, by overlapping words in label and summary."""
    words = _terms(text)
    best, score = None, 0
    for d in load()["domains"].values():
        vocab = _terms(f"{d['label']} {d['summary']}")
        s = len(words & vocab)
        if s > score:
            best, score = d["id"], s
    return best if score >= 2 else None


# ---- Hybrids -------------------------------------------------------------------


def hybrids(
    domain_id: str | None = None,
    district: str | None = None,
    neighbours_only: bool = True,
    limit: int = 20,
) -> list[dict]:
    reg = load()
    cats = reg["categories"]
    pool = list(reg["domains"].values())
    anchors = [reg["domains"][domain_id]] if domain_id else pool
    out = []
    for a in anchors:
        a_schemes = {s["id"] for s in schemes_for(a)}
        for b in pool:
            if b["id"] == a["id"] or b["category"] == a["category"]:
                continue
            if neighbours_only and b["category"] not in cats[a["category"]]["neighbours"]:
                continue
            if a["category"] not in b.get("serves", []):
                continue  # B must be a product that A's kind of business actually uses
            if a["id"] in b.get("not_partner_for", []):
                continue
            supplies = sorted(set(a.get("needs", [])) & set(b.get("offers", [])))
            if not supplies:
                continue  # B must bring something A needs
            returns = sorted(set(b.get("needs", [])) & set(a.get("offers", [])))
            b_schemes = schemes_for(b)
            new = [
                s for s in b_schemes if s["id"] not in a_schemes and s["id"] not in UNIVERSAL_ROUTES
            ]
            fits = {k: min(fit(a, k), fit(b, k)) for k in DISTRICTS}
            where = fits[district] if district else max(fits.values())
            score = 3 * len(supplies) + len(returns) + min(len(new), 3) + 2 * where
            risk = {t: max(a["risk"].get(t, 1), b["risk"].get(t, 1)) for t in reg["risk_types"]}
            out.append(
                {
                    "id": f"{a['id']}+{b['id']}",
                    "title": f"{a['label']}, with {b['label'][0].lower()}{b['label'][1:]}",
                    "anchor": {
                        "id": a["id"],
                        "label": a["label"],
                        "category": cats[a["category"]]["label"],
                    },
                    "partner": {
                        "id": b["id"],
                        "label": b["label"],
                        "category": cats[b["category"]]["label"],
                    },
                    "partner_supplies": [reg["capabilities"][c] for c in supplies],
                    "anchor_supplies": [reg["capabilities"][c] for c in returns],
                    "new_scheme_routes": [
                        {"id": s["id"], "name": s["name"], "status": s["status"], "why": s["why"]}
                        for s in new
                    ],
                    "scheme_routes_total": len(a_schemes | {s["id"] for s in b_schemes}),
                    "district_fit": fits,
                    "risk": risk,
                    "integration_risk": (
                        "two kinds of expertise in one team; integrate one capability at a time"
                    ),
                    "score": score,
                }
            )
    out.sort(key=lambda h: (-h["score"], h["id"]))
    return out[:limit]
