"""Tamil Nadu district names, as founders say them."""

from __future__ import annotations

import re

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


def find_district(text: str) -> str | None:
    low = f" {text.lower()} "
    for name, key in _DISTRICT_NAMES:
        if re.search(rf"(?<![a-z]){re.escape(name)}(?![a-z])", low):
            return key
    return None
