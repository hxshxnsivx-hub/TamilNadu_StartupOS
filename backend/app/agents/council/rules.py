"""Seats without a model: each reads its slice of the evidence and applies plain rules.

The council keeps working without an API key ("degrade, never break"). Rule
opinions carry lower confidence than model opinions and cite the same IDs, so
they pass the same validation and the same vote.

Every claim names its criterion (R106). Every question names the slot it would ask
again, if any (R056). The ways to stand out are scored from the facts each one
carries (task 1.3.1): the prior-art seat by how rare the gap is, the customer seat by
how directly it reaches who pays, and the technical, regulatory and cost seats only
the levers that are their own question. The devil's objections to levers are 1.3.2.
"""

from __future__ import annotations

from collections.abc import Callable

from app.agents.council.evidence import EvidencePack

CONF = 0.5


def _cite(pack: EvidencePack, *prefixes: str, n: int = 2) -> list[str]:
    return [i for i in pack.items if i.startswith(prefixes)][:n]


def _health(pack: EvidencePack) -> bool:
    return pack.health


def _num(pack: EvidencePack, id_: str) -> int:
    text = pack.items.get(id_, {}).get("text", "")
    head = text.split(" ", 1)[0]
    return int(head) if head.isdigit() else 0


def _score_levers(pack: EvidencePack, score: Callable[[dict], int | None]) -> dict[str, int]:
    """lever id -> 1..5 for the levers this seat can judge (None for the rest)."""
    return {lv["id"]: n for lv in pack.levers if (n := score(lv)) is not None}


def _top_lever(pack: EvidencePack, scores: dict[str, int]) -> dict | None:
    """The seat's best-scored lever; the novelty check's order breaks ties."""
    rows = [lv for lv in pack.levers if lv["id"] in scores]
    return max(rows, key=lambda lv: scores[lv["id"]]) if rows else None


def _only(kind: str, n: int) -> Callable[[dict], int | None]:
    """Score one kind of lever, the one that is this seat's own question."""
    return lambda lv: n if lv["kind"] == kind else None


def _customer_lever(pack: EvidencePack, slots: dict) -> Callable[[dict], int | None]:
    """How directly a lever reaches the people who pay: a group the founder named first."""
    rivals = bool(_cite(pack, "startup:"))
    table = {
        "re-target": 5 if slots.get("beneficiary") else 4,
        "localise": 4,
        "business model": 4,
        "cost-down": 4 if rivals else 3,  # buyers who already have a choice compare prices
        "combine": 3,
    }
    return lambda lv: table.get(lv["kind"])


def _prior_art_lever(lv: dict) -> int | None:
    """How rare the gap behind a lever is: no paper at all on a pair or a group is rarest."""
    kind, n = lv["kind"], (lv.get("facts") or {}).get("papers")
    if kind in ("combine", "re-target"):
        return 5 if n == 0 else 4
    return {"localise": 4, "business model": 3, "cost-down": 3}.get(kind)


def customer(pack: EvidencePack, slots: dict) -> dict:
    local = _cite(pack, "startup:")
    domain = _cite(pack, "domain:", n=1)
    levers = _score_levers(pack, _customer_lever(pack, slots))
    if local:
        return {
            "stance": "support",
            "scores": {"need": 4, "differentiation": 2},
            "confidence": CONF,
            "claims": [{"text": "Tamil Nadu startups already sell into this space, so buyers"
                        " exist; the question is why they would switch.", "evidence": local,
                        "criterion": "need"}],
            "ask_founder": "What would make a buyer leave the startups already serving them?",
            "levers": levers,
        }  # fmt: skip
    claims = []
    if domain:  # context, not a judgement: never quoted as the reason for a score
        claims.append({"text": "The closest Vanigam domain names its usual buyers.",
                       "evidence": domain})  # fmt: skip
    if "local:none" in pack.items:
        claims.append({"text": "None of the Tamil Nadu startups searched does this, so"
                       " demand is unproven locally.", "evidence": ["local:none"],
                       "criterion": "need"})  # fmt: skip
    return {
        "stance": "conditional",
        "scores": {"need": 3 if slots.get("beneficiary") else 2},
        "confidence": CONF,
        "claims": claims,
        "ask_founder": "Who exactly would pay for this, and what do they use today instead?",
        "ask_covers": "beneficiary",
        "levers": levers,
    }


def technical(pack: EvidencePack, slots: dict) -> dict:
    repos = _cite(pack, "repo:")
    # joining two parts is easier to build when open code already covers some of it
    levers = _score_levers(pack, _only("combine", 4 if repos else 3))
    if repos:
        return {
            "stance": "support",
            "scores": {"feasibility": 4},
            "confidence": CONF,
            "claims": [{"text": "Open-source projects already do parts of this, so a first"
                        " version can build on them (check their licences).",
                        "evidence": repos, "criterion": "feasibility"}],  # fmt: skip
            "variant": "Build the first version on an existing open-source project",
            "levers": levers,
        }
    papers = _cite(pack, "papers:total", "paper:")
    return {
        "stance": "conditional",
        "scores": {"feasibility": 3},
        "confidence": CONF,
        "claims": [{"text": "There is research to learn from but little open code to start"
                    " from.", "evidence": papers, "criterion": "feasibility"}]
        if papers else [],  # fmt: skip
        "ask_founder": "Which part have you already built or tested, even roughly?",
        "ask_covers": "stage",
        "levers": levers,
    }


def regulatory(pack: EvidencePack, slots: dict) -> dict:
    regs = _cite(pack, "reg:", n=3)
    if _health(pack):
        cites = _cite(pack, "trials:total", "trial:", "field:medicine")
        return {
            "stance": "conditional",
            "scores": {"compliance": 2},
            "confidence": CONF,
            "claims": [{"text": "This sits in medicine, where similar products went through"
                        " clinical trials; expect a medical-device classification check and a"
                        " validation study before sale.", "evidence": cites,
                        "criterion": "compliance"}],  # fmt: skip
            "ask_founder": "Which hospital or clinician would run your first validation study?",
            "variant": "Start with a version that makes no medical claims, then validate",
            "levers": _score_levers(pack, _only("regulatory route", 5)),
        }
    if regs:
        return {
            "stance": "conditional",
            "scores": {"compliance": 3},
            "confidence": CONF,
            "claims": [{"text": "Licences are needed before sale; they are routine but take"
                        " time.", "evidence": regs, "criterion": "compliance"}],  # fmt: skip
        }
    return {"stance": "support", "scores": {"compliance": 4}, "confidence": CONF * 0.6,
            "claims": []}  # fmt: skip


def cost(pack: EvidencePack, slots: dict) -> dict:
    packs = _cite(pack, "pack:", n=1)
    risks = _cite(pack, "risk:supply", "risk:capital")
    # cutting cost is this seat's own question; a worked costing shows where to cut
    levers = _score_levers(pack, _only("cost-down", 5 if packs else 3))
    if packs:
        return {
            "stance": "support",
            "scores": {"economics": 4},
            "confidence": CONF,
            "claims": [{"text": "A worked costing exists for this domain, with known cost"
                        " levers.", "evidence": packs, "criterion": "economics"}],  # fmt: skip
            "levers": levers,
        }
    return {
        "stance": "conditional",
        "scores": {"economics": 3 if not risks else 2},
        "confidence": CONF,
        "claims": [{"text": "Supply or capital is a known risk in this domain.",
                    "evidence": risks, "criterion": "economics"}] if risks else [],  # fmt: skip
        "ask_founder": "What will one unit cost you to make, roughly, and what will it sell for?",
        "levers": levers,
    }


def prior_art(pack: EvidencePack, slots: dict) -> dict:
    statement = pack.items.get("novelty:statement", {}).get("text", "")
    gap_pairs = [
        i for i, it in pack.items.items() if i.startswith("novelty:pair:") and "rare together"
        in it["text"]
    ]  # fmt: skip
    levers = _score_levers(pack, _prior_art_lever)
    if gap_pairs or "(context)" in statement:
        cites = gap_pairs[:1] + _cite(pack, "novelty:context", "novelty:statement", n=1)
        top = _top_lever(pack, levers)  # chosen by its score, not by its place (R110)
        found = statement.split(": ", 1)[-1]  # a full stop, not a second colon, before it
        return {
            "stance": "support",
            "scores": {"differentiation": 4},
            "confidence": CONF,
            "claims": [{"text": f"There is a gap in what exists. {found[:1].upper()}{found[1:]}",
                        "evidence": cites, "criterion": "differentiation"}],  # fmt: skip
            "variant": top["text"] if top else None,
            "levers": levers,
        }
    crowded = "(crowded)" in statement
    cites = _cite(pack, "novelty:statement", "papers:total", "projects:total")
    return {
        "stance": "conditional",
        "scores": {"differentiation": 2 if crowded else 3},
        "confidence": CONF,
        "claims": [{"text": "Much already exists here; the edge has to come from users, cost"
                    " or delivery.", "evidence": cites, "criterion": "differentiation"}]
        if cites else [],  # fmt: skip
        "ask_founder": "What will yours do that the closest existing ones don't?",
        "levers": levers,
    }


def funding(pack: EvidencePack, slots: dict) -> dict:
    schemes = pack.of("funding")
    open_ = [i for i, it in schemes if i.startswith("scheme:") and "(active)" in it["text"]]
    any_scheme = [i for i, _ in schemes if i.startswith("scheme:")]
    if open_:
        return {
            "stance": "support",
            "scores": {"economics": 4},
            "confidence": CONF,
            "claims": [{"text": "At least one scheme that fits is open now.",
                        "evidence": open_[:2], "criterion": "economics"}],  # fmt: skip
        }
    return {
        "stance": "conditional",
        "scores": {"economics": 3 if any_scheme else 2},
        "confidence": CONF,
        "claims": [{"text": "Schemes fit, but none is open right now; plan around their next"
                    " call.", "evidence": any_scheme[:2], "criterion": "economics"}]
        if any_scheme else [],  # fmt: skip
        "ask_founder": "How will you fund the first six months if no grant is open?",
        "ask_covers": "funding_route",
    }


def devil(pack: EvidencePack, slots: dict) -> dict:
    """The strongest objection the evidence supports. Never support."""
    if _health(pack):
        cites = _cite(pack, "trials:total", "field:medicine")
        return {
            "stance": "oppose" if not slots.get("beneficiary") else "conditional",
            "scores": {"compliance": 2, "need": 3},
            "confidence": CONF,
            "claims": [{"text": "Medical products take years of validation; many founders run"
                        " out of money before approval.", "evidence": cites,
                        "criterion": "compliance"}],  # fmt: skip
            "ask_founder": "What will you sell or earn while the validation runs?",
        }
    if "(crowded)" in pack.items.get("novelty:statement", {}).get("text", ""):
        return {
            "stance": "oppose",
            "scores": {"differentiation": 1},
            "confidence": CONF,
            "claims": [{"text": "Every part of this is crowded; a newcomer competes on price"
                        " against established players.",
                        "evidence": ["novelty:statement"],
                        "criterion": "differentiation"}],  # fmt: skip
        }
    cites = _cite(pack, "local:none", "coverage:")
    return {
        "stance": "conditional",
        "scores": {"need": 2},
        "confidence": CONF,
        "claims": [{"text": "Nothing here proves that anyone will pay yet.",
                    "evidence": cites, "criterion": "need"}] if cites else [],  # fmt: skip
        "ask_founder": "Has anyone told you they would pay for this?",
    }


RULES = {
    "customer": customer,
    "technical": technical,
    "regulatory": regulatory,
    "cost": cost,
    "prior_art": prior_art,
    "funding": funding,
    "devil": devil,
}
