"""Tamil Nadu district names, as founders say them.

Resolution is position-, role- and polarity-aware (arena flag F-A1-005): the
district the founder *corrects to* or *lives in* wins over one they negate or
name only as a selling market, and ties go to the earliest mention — not, as
before, to whichever name happened to be longest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.vocab import negated

# The 38 districts of Tamil Nadu, keyed by the id used across Vanigam
# (lower case, as in the planner registry), with common alternative names.
DISTRICTS: dict[str, tuple[str, ...]] = {
    "ariyalur": (),
    "chengalpattu": ("chengalpet",),
    "chennai": ("madras",),
    "coimbatore": ("kovai",),
    "cuddalore": (),
    "dharmapuri": (),
    "dindigul": (),
    "erode": (),
    "kallakurichi": (),
    "kancheepuram": ("kanchipuram", "kanchi"),
    "kanniyakumari": ("kanyakumari", "nagercoil"),
    "karur": (),
    "krishnagiri": ("hosur",),
    "madurai": (),
    "mayiladuthurai": ("mayavaram",),
    "nagapattinam": (),
    "namakkal": (),
    "nilgiris": ("the nilgiris", "ooty", "udhagamandalam"),
    "perambalur": (),
    "pudukkottai": ("pudukottai",),
    "ramanathapuram": ("ramnad",),
    "ranipet": (),
    "salem": (),
    "sivaganga": ("sivagangai",),
    "tenkasi": (),
    "thanjavur": ("tanjore",),
    "theni": (),
    "thoothukudi": ("tuticorin",),
    "tiruchirappalli": ("trichy", "tiruchi", "tiruchy", "trichirappalli"),
    "tirunelveli": ("nellai",),
    "tirupathur": ("tirupattur",),
    "tiruppur": ("tirupur",),
    "tiruvallur": ("thiruvallur",),
    "tiruvannamalai": ("thiruvannamalai",),
    "tiruvarur": ("thiruvarur",),
    "vellore": (),
    "viluppuram": ("villupuram",),
    "virudhunagar": ("sivakasi",),
}
_DISTRICT_NAMES = sorted(
    ((name, key) for key, alts in DISTRICTS.items() for name in (key, *alts)),
    key=lambda p: -len(p[0]),  # "the nilgiris" before "nilgiris"
)


# Phrases that mark a place as a selling market rather than where the founder is
# based, so "sell in Coimbatore" never fills the home district (F-A1-005).
_MARKET_CUE = re.compile(
    r"\b(?:sell|selling|sell to|market|markets|marketing|target|targeting|"
    r"supply|supplying|ship|shipping|expand|expanding|customers)\b\s+(?:in|to|into|across)\b",
    re.I,
)


@dataclass(frozen=True)
class PlaceMention:
    key: str  # the district id
    start: int  # where the name begins in the text
    negated: bool  # preceded by "not"/"illai" etc.
    market: bool  # named as a selling market, not a home base


def find_places(text: str) -> list[PlaceMention]:
    """Every district named, in order, each tagged with polarity and role."""
    low = f" {text.lower()} "
    seen: list[PlaceMention] = []
    taken: list[tuple[int, int]] = []  # spans already claimed by a longer name
    for name, key in _DISTRICT_NAMES:  # longest first, so "nilgiris" loses to "the nilgiris"
        for m in re.finditer(rf"(?<![a-z]){re.escape(name)}(?![a-z])", low):
            s, e = m.start(), m.end()
            if any(ts <= s < te or ts < e <= te for ts, te in taken):
                continue
            taken.append((s, e))
            # a market cue immediately before this place marks it as a market
            window = low[max(0, s - 24) : s]
            seen.append(
                PlaceMention(
                    key=key,
                    start=s,
                    negated=negated(low, s),
                    market=_MARKET_CUE.search(window) is not None,
                )
            )
    return sorted(seen, key=lambda p: p.start)


def resolve_district(text: str) -> str | None:
    """The one district to store: a corrected/home mention over a negated or
    market one, ties broken by position (F-A1-005)."""
    # a negated mention ("not Erode") and a market mention ("sell in Coimbatore")
    # never fill the home district; the earliest surviving mention wins.
    home = [m for m in find_places(text) if not m.negated and not m.market]
    return home[0].key if home else None


def find_district(text: str) -> str | None:
    return resolve_district(text)
