"""The weighted vote: plain code, milliseconds, same input gives same output.

    criterion score = Σ seat weight × confidence × score / Σ seat weight × confidence
    spread          = the weighted standard deviation of those scores
    band            = strong (≥ 3.8) · mixed (≥ 2.8) · weak; any cited blocker → weak

The criterion the seats disagree on most (spread > 1.0) becomes the next
question for the founder. Weights come from council_weights.json by idea
type, adjusted for the founder, and every verdict records the weights version.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.agents.council.seats import BY_ID, CRITERIA, Opinion
from app.core.vocab import boundary_hits

WEIGHTS_FILE = Path(__file__).parent / "data" / "council_weights.json"
STRONG, MIXED = 3.8, 2.8
DISAGREE = 1.0
SMALL_CAPITAL = {"under_2L", "2L_10L"}

# A reviewed vocabulary of building skills, matched on word boundaries so a
# "python developer" reads as technical and "tailoring" does not (F-A1-021).
TECH_SKILLS = (
    "software", "hardware", "engineer", "engineering", "developer", "development",
    "programmer", "programming", "coder", "coding", "code",
    "python", "java", "javascript", "typescript", "golang", "rust", "c++",
    "electronics", "electronic", "mechanical", "mechatronics", "embedded", "firmware",
    "robotics", "iot", "data science", "machine learning", "ml", "ai",
    "backend", "frontend", "full stack", "fullstack", "devops", "cloud", "technical",
)  # fmt: skip


def technical_skill(slots: dict) -> bool | None:
    """Three-valued read of the founder's building skill: None when the skill is
    not known (the slot is unanswered), True when a reviewed technical term is
    present, False when answered with no technical skill (F-A1-021)."""
    raw = slots.get("founder_skills")
    if raw is None:
        return None
    text = " ".join(map(str, raw)) if isinstance(raw, (list, tuple)) else str(raw)
    if not text.strip():
        return None
    return any(boundary_hits(text, term) for term in TECH_SKILLS)


@lru_cache
def weights_table() -> dict:
    return json.loads(WEIGHTS_FILE.read_text(encoding="utf8"))


def idea_type(categories: list[str], slots: dict) -> str:
    # The founder's own sector/form decides first; research-derived categories are
    # only a fallback. A tea or food idea whose papers merely touch "Medicine" is no
    # longer cast as a health device (F-A5-001, F-B4-020).
    sector = str(slots.get("sector") or "")
    form = str(slots.get("product_form") or "")
    if sector == "health":
        return "health_device"
    if sector == "food":
        return "food"
    if sector == "agri":
        return "agri"
    if form == "service":
        return "service"
    if (
        form == "software"
        or sector == "it_services"
        or {"ai_ml", "saas", "fintech", "it"} & set(categories)
    ):
        return "software"
    # category fallbacks, only when the founder gave no decisive sector/form
    if "agriculture" in categories:
        return "agri"
    if "health_bio" in categories:
        return "health_device"
    return "hardware"


def weights_for(kind: str, slots: dict) -> tuple[dict[str, float], list[str]]:
    """Seat weights for this idea and founder, with the reasons for each adjustment."""
    t = weights_table()
    w = dict(zip(t["seats"], t["types"][kind], strict=True))
    why = []
    tech = technical_skill(slots)
    if kind in ("health_device", "hardware", "software"):
        if tech is False:
            # answered, and no building skill: the panel leans harder on feasibility
            w["technical"] += 5
            why.append("founder reports no technical skill: technical +5")
        elif tech is None:
            # unknown, not absent — do not bump on a guess
            why.append("founder's technical skill not known: no technical adjustment")
    if str(slots.get("capital_band") or "") in SMALL_CAPITAL:
        w["funding"] += 5
        w["cost"] += 5
        why.append("starting capital under ₹10 lakh: funding and cost +5")
    lo, hi = t["bounds"]
    w = {k: min(hi, max(lo, v)) for k, v in w.items()}
    total = sum(w.values())
    return {k: round(100 * v / total, 1) for k, v in w.items()}, why


def vote(opinions: list[Opinion], kind: str, slots: dict) -> dict:
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
    asker = next(
        (o for o in opinions if ask_about and o.seat == per[ask_about]["low"] and o.ask_founder),
        None,
    ) or next((o for o in opinions if o.ask_founder), None)

    return {
        "band": band,
        "overall": round(overall, 2),
        "criteria": per,
        "blockers": blockers,
        "ask_about": ask_about,
        "question": asker.ask_founder if asker else None,
        "question_from": asker.seat if asker else None,
        "variants": _variants(opinions, w),
        "weights": w,
        "weights_why": why,
        "weights_version": weights_table()["version"],
        "idea_type": kind,
        "stances": {o.seat: o.stance for o in opinions},
        "missing_seats": sorted(set(BY_ID) - {o.seat for o in opinions}),
    }


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
