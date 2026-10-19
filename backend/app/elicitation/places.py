"""Tamil Nadu district names, as founders say them."""

from __future__ import annotations

import re

from app.elicitation.cues import negated

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


_NAME_PATTERNS = [
    (re.compile(rf"(?<![a-z]){re.escape(name)}(?![a-z])"), key) for name, key in _DISTRICT_NAMES
]

# Words that tie a place to where the founder is, rather than where they sell or
# where someone else lives: "I live in Salem but sell in Coimbatore".
_HOME = re.compile(
    r"\b(?:live|living|lives|based|located|from|operate|operating|unit|shop|factory|office"
    r"|i am|i'm|we are|we're|my place|native|home)\b"
)
_HOME_WINDOW = 4  # words before the place name


def find_districts(text: str) -> list[tuple[int, str]]:
    """(position, district) for each district named and not denied, in order.

    "Salem, not Erode" names Salem only (R063). Longer names are matched first,
    so "the nilgiris" is one mention, not two.
    """
    low = text.lower()
    taken: list[tuple[int, int]] = []
    found: list[tuple[int, str]] = []
    for pattern, key in _NAME_PATTERNS:
        for m in pattern.finditer(low):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            if not negated(low, m.start(), m.end(), window=2):
                found.append((m.start(), key))
    return sorted(found)


def find_district(text: str) -> str | None:
    """The district the founder is in: one tied to where they live or work
    ("I live in Salem"), else the first named. Used to be the longest name
    anywhere in the text, so a second place picked by string length won."""
    found = find_districts(text)
    if not found:
        return None
    low = text.lower()
    for start, key in found:
        before = " ".join(low[:start].split()[-_HOME_WINDOW:])
        if _HOME.search(before):
            return key
    return found[0][1]
