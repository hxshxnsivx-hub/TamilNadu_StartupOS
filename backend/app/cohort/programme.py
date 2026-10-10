"""Programme cohort: what a group of founders has in common, for the programme.

An incubator or college cell sees aggregates of its founders' ideation
sessions, never a founder's idea or name:

    - only sessions whose founder agreed to share with the programme;
    - nothing at all when fewer than 5 founders agreed;
    - any group smaller than 5 is folded into "fewer than 5 each".

What it shows: where founders are (district, sector, stage, capital), how
their ideas sit in the research (novelty type, review-panel view), what they
most often have not worked out yet, and how far they have got.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

MIN_GROUP = 5
SMALL = "fewer than 5 each"


def _plain(v: Any) -> str:
    return str(getattr(v, "value", v))


def _grouped(values: list[str]) -> dict[str, int]:
    """Counts with every group under MIN_GROUP folded together."""
    counts = Counter(v for v in values if v)
    out = {k: n for k, n in counts.most_common() if n >= MIN_GROUP}
    small = sum(n for n in counts.values() if n < MIN_GROUP)
    if small:
        out[SMALL] = small
    return out


def programme_cohort(sessions: list) -> dict:
    """`sessions`: AgentSession objects for the programme's founders."""
    shared = [s for s in sessions if getattr(s, "cohort_consent", False)]
    base = {"founders_listed": len(sessions), "founders_sharing": len(shared)}
    if len(shared) < MIN_GROUP:
        return {
            **base,
            "shown": False,
            "reason": (
                f"Fewer than {MIN_GROUP} founders agreed to share their sessions, so nothing is"
                " shown: with so few, an aggregate could identify someone."
            ),
        }

    def slot(s, key: str) -> str:
        v = s.elicitation.slots.get(key)
        return _plain(v.value) if v else "not given"

    gaps = [g for s in shared for g in sorted(s.elicitation.missing)]
    asked_by_panel = [(s.council or {}).get("vote", {}).get("ask_about") or "" for s in shared]
    progress = [s.elicitation.progress() for s in shared]
    return {
        **base,
        "shown": True,
        "where_they_are": {
            "district": _grouped([slot(s, "district") for s in shared]),
            "sector": _grouped([slot(s, "sector") for s in shared]),
            "stage": _grouped([slot(s, "stage") for s in shared]),
            "starting_capital": _grouped([slot(s, "capital_band") for s in shared]),
        },
        "their_ideas": {
            "novelty": _grouped(
                [
                    ((s.novelty or {}).get("statement") or {}).get("type", "not checked")
                    for s in shared
                ]
            ),
            "review_panel": _grouped(
                [((s.council or {}).get("vote") or {}).get("band", "not reviewed") for s in shared]
            ),
            "panel_disagrees_most_on": _grouped([a for a in asked_by_panel if a]),
        },
        "not_worked_out_yet": _grouped([g.replace("_", " ") for g in gaps]),
        "progress": {
            "average_share_of_essentials_known": round(sum(progress) / len(progress), 2),
            "reached_a_roadmap": sum(1 for s in shared if s.roadmap),
        },
        "privacy": (
            f"Only founders who agreed are counted; groups under {MIN_GROUP} are folded"
            " together; no idea text or names are included."
        ),
    }
