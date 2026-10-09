"""Seats without a model: each reads its slice of the evidence and applies plain rules.

The council keeps working without an API key ("degrade, never break"). Rule
opinions carry lower confidence than model opinions and cite the same IDs, so
they pass the same validation and the same vote.
"""

from __future__ import annotations

from app.agents.council.evidence import EvidencePack

CONF = 0.5


def _cite(pack: EvidencePack, *prefixes: str, n: int = 2) -> list[str]:
    return [i for i in pack.items if i.startswith(prefixes)][:n]


def _health(pack: EvidencePack) -> bool:
    return any(i in pack.items for i in ("field:medicine", "field:nursing", "trials:total"))


def _num(pack: EvidencePack, id_: str) -> int:
    text = pack.items.get(id_, {}).get("text", "")
    head = text.split(" ", 1)[0]
    return int(head) if head.isdigit() else 0


def customer(pack: EvidencePack, slots: dict) -> dict:
    local = _cite(pack, "startup:")
    domain = _cite(pack, "domain:", n=1)
    if local:
        return {
            "stance": "support",
            "scores": {"need": 4, "differentiation": 2},
            "confidence": CONF,
            "claims": [{"text": "Tamil Nadu startups already sell into this space, so buyers"
                        " exist; the question is why they would switch.", "evidence": local}],
            "ask_founder": "What would make a buyer leave the startups already serving them?",
        }  # fmt: skip
    claims = []
    if domain:
        claims.append({"text": "The closest Vanigam domain names its usual buyers.",
                       "evidence": domain})  # fmt: skip
    if "local:none" in pack.items:
        claims.append({"text": "No Tamil Nadu startup does this yet, so demand is unproven"
                       " locally.", "evidence": ["local:none"]})  # fmt: skip
    return {
        "stance": "conditional",
        "scores": {"need": 3 if slots.get("beneficiary") else 2},
        "confidence": CONF,
        "claims": claims,
        "ask_founder": "Who exactly would pay for this, and what do they use today instead?",
    }


def technical(pack: EvidencePack, slots: dict) -> dict:
    repos = _cite(pack, "repo:")
    if repos:
        return {
            "stance": "support",
            "scores": {"feasibility": 4},
            "confidence": CONF,
            "claims": [{"text": "Open-source projects already do parts of this, so a first"
                        " version can build on them (check their licences).",
                        "evidence": repos}],  # fmt: skip
            "variant": "Build the first version on an existing open-source project",
        }
    papers = _cite(pack, "papers:total", "paper:")
    return {
        "stance": "conditional",
        "scores": {"feasibility": 3},
        "confidence": CONF,
        "claims": [{"text": "There is research to learn from but little open code to start"
                    " from.", "evidence": papers}] if papers else [],  # fmt: skip
        "ask_founder": "Which part have you already built or tested, even roughly?",
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
                        " validation study before sale.", "evidence": cites}],  # fmt: skip
            "ask_founder": "Which hospital or clinician would run your first validation study?",
            "variant": "Start as a communication aid without medical claims, then validate",
        }
    if regs:
        return {
            "stance": "conditional",
            "scores": {"compliance": 3},
            "confidence": CONF,
            "claims": [{"text": "Licences are needed before sale; they are routine but take"
                        " time.", "evidence": regs}],  # fmt: skip
        }
    return {"stance": "support", "scores": {"compliance": 4}, "confidence": CONF * 0.6,
            "claims": []}  # fmt: skip


def cost(pack: EvidencePack, slots: dict) -> dict:
    packs = _cite(pack, "pack:", n=1)
    risks = _cite(pack, "risk:supply", "risk:capital")
    if packs:
        return {
            "stance": "support",
            "scores": {"economics": 4},
            "confidence": CONF,
            "claims": [{"text": "A worked costing exists for this domain, with known cost"
                        " levers.", "evidence": packs}],  # fmt: skip
        }
    return {
        "stance": "conditional",
        "scores": {"economics": 3 if not risks else 2},
        "confidence": CONF,
        "claims": [{"text": "Supply or capital is a known risk in this domain.",
                    "evidence": risks}] if risks else [],  # fmt: skip
        "ask_founder": "What will one unit cost you to make, roughly, and what will it sell for?",
    }


def prior_art(pack: EvidencePack, slots: dict) -> dict:
    statement = pack.items.get("novelty:statement", {}).get("text", "")
    gap_pairs = [
        i for i, it in pack.items.items() if i.startswith("novelty:pair:") and "rare together"
        in it["text"]
    ]  # fmt: skip
    if gap_pairs or "(context)" in statement:
        cites = gap_pairs[:1] + _cite(pack, "novelty:context", "novelty:statement", n=1)
        lever = pack.items.get("novelty:lever:0", {}).get("text", "")
        lever_text = lever.split(": ", 1)[-1] if lever else None
        return {
            "stance": "support",
            "scores": {"differentiation": 4},
            "confidence": CONF,
            "claims": [{"text": "There is a gap in what exists: " + statement.split(": ", 1)[-1],
                        "evidence": cites}],  # fmt: skip
            "variant": lever_text,
        }
    crowded = "(crowded)" in statement
    cites = _cite(pack, "novelty:statement", "papers:total", "projects:total")
    return {
        "stance": "conditional",
        "scores": {"differentiation": 2 if crowded else 3},
        "confidence": CONF,
        "claims": [{"text": "Much already exists here; the edge has to come from users, cost"
                    " or delivery.", "evidence": cites}] if cites else [],  # fmt: skip
        "ask_founder": "What will yours do that the closest existing ones don't?",
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
                        "evidence": open_[:2]}],  # fmt: skip
        }
    return {
        "stance": "conditional",
        "scores": {"economics": 3 if any_scheme else 2},
        "confidence": CONF,
        "claims": [{"text": "Schemes fit, but none is open right now; plan around their next"
                    " call.", "evidence": any_scheme[:2]}] if any_scheme else [],  # fmt: skip
        "ask_founder": "How will you fund the first six months if no grant is open?",
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
                        " out of money before approval.", "evidence": cites}],  # fmt: skip
            "ask_founder": "What will you sell or earn while the validation runs?",
        }
    if "(crowded)" in pack.items.get("novelty:statement", {}).get("text", ""):
        return {
            "stance": "oppose",
            "scores": {"differentiation": 1},
            "confidence": CONF,
            "claims": [{"text": "Every part of this is crowded; a newcomer competes on price"
                        " against established players.",
                        "evidence": ["novelty:statement"]}],  # fmt: skip
        }
    cites = _cite(pack, "local:none", "coverage:")
    return {
        "stance": "conditional",
        "scores": {"need": 2},
        "confidence": CONF,
        "claims": [{"text": "Nothing here proves that anyone will pay yet.",
                    "evidence": cites}] if cites else [],  # fmt: skip
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
