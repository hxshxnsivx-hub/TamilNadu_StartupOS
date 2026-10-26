"""Ways to stand out, worded for the founder's domain at the time they are said (R190).

The novelty check decides which levers the evidence supports and keeps each one as
its kind and the facts behind it: the pair and its count, the India share, who is
served, the trials found, the domain with a cost pack. The words are chosen here,
from the matched registry domain and the founder's sector, so a sector answered or
corrected after the search rewords a lever with no new search:

    localise         "local hospital and clinic routines" for a health product,
                     "local tastes and shop routines" for a food brand
    business model   a service or rental for a machine; subscriptions or gift orders
                     for a tea brand; made-to-order runs for a t-shirt brand

Only the facts are numbers or names, and they come from the novelty result and the
registry, so a worded lever says nothing the evidence does not hold (decision 0005).

Each lever has a stable `id`, a hash of its kind and facts (R041): the panel scores it
by that id, the narrator remembers it by that id, and neither moves when the panel
reorders the list or the words change with the founder's sector.
"""

from __future__ import annotations

import hashlib
import json

# The founder's sector (elicitation Sector) -> phrase key.
SECTOR_KEY = {
    "agri": "agri",
    "textile": "textile",
    "food": "food",
    "manufacturing": "hardware",
    "auto": "hardware",
    "electronics": "hardware",
    "it_services": "software",
    "health": "health",
    "education": "education",
    "finance": "finance",
    "retail": "retail",
}
# A registry domain's startup-map sector -> phrase key, when the founder has not said.
DOMAIN_SECTOR_KEY = {
    "agritech": "agri",
    "food": "food",
    "consumer": "retail",
    "textiles": "textile",
    "healthtech": "health",
    "biotech_pharma": "health",
    "electronics": "hardware",
    "cleantech": "hardware",
    "mobility": "hardware",
    "manufacturing": "hardware",
    "saas": "software",
    "deeptech": "software",
    "proptech": "software",
    "fintech": "finance",
    "edtech": "education",
    "logistics": "services",
    "services": "services",
    "hospitality": "services",
}
# What "fit Tamil Nadu" means besides the language and the price.
LOCAL_ROUTINES = {
    "health": "local hospital and clinic routines",
    "agri": "local farm seasons and market routines",
    "food": "local tastes and shop routines",
    "textile": "the way local mills, job-work units and buyers work",
    "hardware": "local site conditions and repair routines",
    "software": "the way local businesses already work",
    "finance": "local lending and payment habits",
    "education": "local school and college routines",
    "retail": "local shop and buying routines",
    "services": "your local customers' routines",
}
DEFAULT_ROUTINES = "local routines"
# How it could reach people other than a plain product sale.
DELIVERY = {
    "health": "through hospitals or clinics as a service, or a scheme-backed rollout, rather"
    " than a product sale",
    "agri": "through farmer groups, contract buying, or a shared processing service rather"
    " than one-off sales",
    "food": "through subscriptions, gift and bulk orders, or supplying cafés and hotels,"
    " rather than shelf sales alone",
    "textile": "through made-to-order runs, private-label work for brands, or direct online"
    " sales rather than stock sold through shops",
    "hardware": "as a service, a rental, or a scheme-backed rollout rather than a product sale",
    "software": "as a subscription, pay per use, or through a partner who already reaches your"
    " users, rather than a one-time sale",
    "finance": "through a regulated partner, earning per transaction, rather than lending"
    " your own money",
    "education": "through schools or colleges, or a subscription, rather than one-off sales",
    "retail": "through subscriptions or repeat orders rather than one-off sales",
    "services": "as a yearly contract rather than one job at a time",
}
DEFAULT_DELIVERY = DELIVERY["hardware"]


def lever_id(lever: dict) -> str:
    """The lever's stable id: its own, else a hash of its kind and facts (a lever saved
    before levers carried facts hashes its search-time words instead)."""
    if lever.get("id"):
        return str(lever["id"])
    basis = lever.get("facts")
    if basis is None:
        basis = lever.get("text", "")
    raw = json.dumps({"kind": lever.get("kind"), "facts": basis}, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def phrase_key(domain_id: str | None = None, sector: str | None = None) -> str | None:
    """The founder's own sector first (the rule idea_type follows, R035), then the sector
    of the matched registry domain; None when neither says."""
    sector = str(getattr(sector, "value", sector) or "")
    if sector in SECTOR_KEY:
        return SECTOR_KEY[sector]
    card = _card(domain_id)
    return DOMAIN_SECTOR_KEY.get(card.get("sector") or "") if card else None


def _card(domain_id: str | None) -> dict | None:
    if not domain_id:
        return None
    from app.planner import registry

    return registry.load()["domains"].get(domain_id)


def _count(n: int, noun: str) -> str:
    return f"{n:,} {noun}" + ("" if n == 1 else "s")


def _few(n: int, one: str, many: str) -> str:
    """'only 3 papers cover', 'only 1 paper covers', and 'no papers cover'."""
    if n == 0:
        return f"no {many}"
    return f"only 1 {one}" if n == 1 else f"only {n:,} {many}"


def render(lever: dict, *, domain_id: str | None = None, sector: str | None = None) -> dict:
    """The lever with its `text` and `because` worded for this domain and sector.

    A lever saved before levers carried facts (an older session) keeps its own words
    wherever they depend on facts it no longer has; the domain-worded kinds are
    reworded all the same, since their wording needs no count.
    """
    kind, facts = lever["kind"], lever.get("facts")
    key = phrase_key(domain_id or (facts or {}).get("domain"), sector)
    text, because = lever.get("text", ""), lever.get("because", "")
    if facts is not None:
        because = _because(kind, facts) or because
    if kind == "combine" and facts:
        text = f"Build your version around joining {facts['a']} with {facts['b']}."
    elif kind == "re-target" and facts:
        text = f"Design it specifically for {facts['who']}."
    elif kind == "localise":
        routines = LOCAL_ROUTINES.get(key or "", DEFAULT_ROUTINES)
        text = f"Make it fit Tamil Nadu, with the Tamil language, {routines}, and a local price."
    elif kind == "regulatory route":
        text = (
            "Check whether a first version can be sold without medical-device claims, and add"
            " clinical claims after a validation study."
        )
    elif kind == "cost-down":
        card = _card((facts or {}).get("domain") or domain_id)
        what = (
            f"Vanigam's costing for {_lower(card['label'])}"
            if card
            else "the costing for this domain"
        )
        text = f"Compete on cost, using {what} to see where to cut."
    elif kind == "business model":
        text = f"Compete on how it is delivered, {DELIVERY.get(key or '', DEFAULT_DELIVERY)}."
    return {**lever, "id": lever_id(lever), "text": text, "because": because}


def _lower(label: str) -> str:
    """'Banana value-added products' -> 'banana value-added products'; 'D2C kits' stays."""
    return label[:1].lower() + label[1:] if label[1:2].islower() else label


def _because(kind: str, f: dict) -> str | None:
    if kind == "combine":
        return f"{_few(f['papers'], 'paper covers', 'papers cover')} both"
    if kind == "localise":
        return (
            f"{f['india_papers']:,} of {f['world_papers']:,} papers are from India, and none"
            f" of {f['tn_scope']} does it"
        )
    if kind == "re-target":
        return f"{_few(f['papers'], 'paper focuses', 'papers focus')} on them"
    if kind == "regulatory route":
        if f.get("trials"):
            return f"it is a health product, and {_count(f['trials'], 'clinical trial')} came up"
        return "it is a health product by its own description"
    if kind == "cost-down":
        return "a Vanigam cost pack exists for this domain"
    if kind == "business model":
        return "every part and combination is crowded"
    return None


def worded(novelty: dict | None, *, domain_id: str | None = None, sector=None) -> dict | None:
    """A copy of the novelty result with every lever worded for this domain and sector."""
    if not novelty or not novelty.get("levers"):
        return novelty
    levers = [render(lv, domain_id=domain_id, sector=sector) for lv in novelty["levers"]]
    return {**novelty, "levers": levers}
