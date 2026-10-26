"""The weighted vote: plain code, milliseconds, same input gives same output.

    criterion score = Σ seat weight × confidence × score / Σ seat weight × confidence
    spread          = the weighted standard deviation of those scores
    band            = strong (≥ 3.8) · mixed (≥ 2.8) · weak; any cited blocker → weak

The criterion the seats disagree on most (spread > 1.0) becomes the next
question for the founder; when nobody disagrees, the question comes from the
weakest criterion's low seat (R056). A question that would ask a slot the founder
already answered is never chosen. Weights come from council_weights.json by idea
type, adjusted for the founder, and every verdict records the weights version.

The ways to stand out are ranked the same way (task 1.3.1):

    lever score = Σ seat weight × confidence × score / Σ seat weight × confidence

over the seats that scored it; levers no seat scored come last, and the novelty
check's order breaks ties. The narrator speaks the top three of `lever_order`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.agents.council.seats import BY_ID, CRITERIA, Opinion

WEIGHTS_FILE = Path(__file__).parent / "data" / "council_weights.json"
STRONG, MIXED = 3.8, 2.8
DISAGREE = 1.0
SMALL_CAPITAL = {"under_2L", "2L_10L"}
# Substrings of a stated skill that make it technical; the list grows by review (R156).
TECH_SKILLS = (
    "software", "engineer", "electronic", "electric", "hardware", "coding", "programming",
    "programmer", "developer", "python", "java", "embedded", "tech",
)  # fmt: skip


@lru_cache
def weights_table() -> dict:
    return json.loads(WEIGHTS_FILE.read_text(encoding="utf8"))


SECTOR_TYPE = {"health": "health_device", "food": "food", "agri": "agri"}
SOFTWARE_CATEGORIES = {"ai_ml", "saas", "fintech", "it"}
# Sectors of physical goods; others (education, retail) fall through to form, then categories.
PHYSICAL_SECTORS = {"textile", "manufacturing", "auto", "electronics"}


def idea_type(categories: list[str], slots: dict) -> str:
    """The founder's sector and product form first; categories inferred from papers only
    fill what the founder has not said (R035): a tea brand whose papers touch medicine
    is still food, and a physical textile product is not software."""
    sector = str(slots.get("sector") or "")
    sector = "" if sector == "other" else sector
    form = str(slots.get("product_form") or "")
    if sector in SECTOR_TYPE:
        return SECTOR_TYPE[sector]
    if form == "service":
        return "service"
    if form == "software" or sector in ("it_services", "finance"):
        return "software"
    if sector in PHYSICAL_SECTORS:
        return "hardware"
    if "health_bio" in categories:
        return "health_device"
    if "agriculture" in categories:
        return "agri"
    if form not in ("physical", "hybrid") and SOFTWARE_CATEGORIES & set(categories):
        return "software"
    return "hardware"


def weights_for(kind: str, slots: dict) -> tuple[dict[str, float], list[str]]:
    """Seat weights for this idea and founder, with the reasons for each adjustment."""
    t = weights_table()
    w = dict(zip(t["seats"], t["types"][kind], strict=True))
    why = []
    # Three states (R156): skills not recorded say nothing, so only skills the founder
    # named, none of them technical, raise the technical seat.
    skills = " ".join(map(str, slots.get("founder_skills") or [])).lower().strip()
    if (
        kind in ("health_device", "hardware", "software")
        and skills
        and not any(k in skills for k in TECH_SKILLS)
    ):
        w["technical"] += 5
        why.append("none of the founder's stated skills is technical: technical +5")
    if str(slots.get("capital_band") or "") in SMALL_CAPITAL:
        w["funding"] += 5
        w["cost"] += 5
        why.append("starting capital under ₹10 lakh: funding and cost +5")
    lo, hi = t["bounds"]
    w = {k: min(hi, max(lo, v)) for k, v in w.items()}
    total = sum(w.values())
    return {k: round(100 * v / total, 1) for k, v in w.items()}, why


def vote(
    opinions: list[Opinion], kind: str, slots: dict, lever_ids: list[str] | tuple = ()
) -> dict:
    """`lever_ids`: every way to stand out in the pack, in the novelty check's order."""
    w, why = weights_for(kind, slots)
    per: dict[str, dict] = {}
    for c in CRITERIA:
        pts = [(w[o.seat] * o.confidence, o.scores[c], o.seat) for o in opinions if c in o.scores]
        total = sum(k for k, _, _ in pts)
        if not total:
            continue
        mean = sum(k * s for k, s, _ in pts) / total
        spread = (sum(k * (s - mean) ** 2 for k, s, _ in pts) / total) ** 0.5
        low = min(pts, key=lambda p: p[1])[2]
        high = max(pts, key=lambda p: p[1])[2]
        per[c] = {"score": round(mean, 2), "spread": round(spread, 2), "low": low, "high": high}
    overall = sum(v["score"] for v in per.values()) / len(per) if per else 0.0
    blockers = [
        {"seat": o.seat, "text": o.blocker.text, "evidence": o.blocker.evidence}
        for o in opinions
        if o.blocker is not None
    ]
    if blockers:
        band = "weak"
    else:
        band = "strong" if overall >= STRONG else "mixed" if overall >= MIXED else "weak"

    ask_about = max(per, key=lambda c: per[c]["spread"]) if per else None
    if ask_about and per[ask_about]["spread"] <= DISAGREE:
        ask_about = None
    # a question whose slot the founder already answered is not asked again (R056)
    askers = [
        o for o in opinions if o.ask_founder and not (o.ask_covers and slots.get(o.ask_covers))
    ]
    weakest = min(per, key=lambda c: per[c]["score"]) if per else None
    focus = ask_about or weakest
    asker = (
        next(
            (o for o in askers if focus and o.seat == per[focus]["low"]),
            None,
        )
        or next((o for o in askers if focus and focus in o.scores), None)
        or (askers[0] if askers else None)
    )
    order, scores = _rank_levers(opinions, w, list(lever_ids))

    return {
        "band": band,
        "overall": round(overall, 2),
        "criteria": per,
        "blockers": blockers,
        "ask_about": ask_about,
        "question": asker.ask_founder if asker else None,
        "question_from": asker.seat if asker else None,
        "question_covers": asker.ask_covers if asker else None,
        "variants": _variants(opinions, w),
        "lever_order": order,
        "lever_scores": scores,
        "weights": w,
        "weights_why": why,
        "weights_version": weights_table()["version"],
        "idea_type": kind,
        "stances": {o.seat: o.stance for o in opinions},
        "missing_seats": sorted(set(BY_ID) - {o.seat for o in opinions}),
    }


def _rank_levers(
    opinions: list[Opinion], w: dict[str, float], ids: list[str]
) -> tuple[list[str], dict[str, dict]]:
    """Every lever in the pack, best first, with its weighted score and who scored it."""
    scores: dict[str, dict] = {}
    for lid in ids:
        pts = [(w[o.seat] * o.confidence, o.levers[lid], o.seat) for o in opinions
               if lid in o.levers]  # fmt: skip
        total = sum(k for k, _, _ in pts)
        if total:
            mean = sum(k * s for k, s, _ in pts) / total
            scores[lid] = {"score": round(mean, 2), "seats": [p[2] for p in pts]}
    order = sorted(ids, key=lambda i: (-scores[i]["score"] if i in scores else 0, ids.index(i)))
    return order, scores


def _variants(opinions: list[Opinion], w: dict[str, float]) -> list[dict]:
    """The idea as described, plus up to two alternatives, ranked by seat weight."""
    support = sum(w[o.seat] for o in opinions if o.stance == "support")
    rows: dict[str, dict] = {}
    for o in opinions:
        if o.variant:
            key = o.variant.strip().rstrip(".").lower()
            row = rows.setdefault(key, {"text": o.variant.strip(), "weight": 0.0, "seats": []})
            row["weight"] += w[o.seat]
            row["seats"].append(o.seat)
    alts = sorted(rows.values(), key=lambda r: -r["weight"])[:2]
    described = {"text": "The idea as you described it", "weight": support, "seats": [],
                 "as_described": True}  # fmt: skip
    return [described, *[{**a, "as_described": False} for a in alts]]
