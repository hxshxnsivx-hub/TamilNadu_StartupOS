"""Free local format/checksum validators (design §A · pre-filters).

These run before any paid vendor call, so obviously-malformed identifiers are
rejected for free (~10–20% of typos never hit the API). None of these confirm the
identifier is *real* — only that it is well-formed.
"""

from __future__ import annotations

import re

CIN_RE = re.compile(r"^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

_CODE_POINTS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cin_is_valid(cin: str) -> bool:
    return bool(CIN_RE.match(cin.strip().upper()))


def pan_is_valid(pan: str) -> bool:
    return bool(PAN_RE.match(pan.strip().upper()))


def gstin_checksum_ok(gstin: str) -> bool:
    """Validate the 15th GSTIN character (mod-36 check digit)."""
    g = gstin.strip().upper()
    if len(g) != 15 or not GSTIN_RE.match(g):
        return False
    total = 0
    factor = 1
    for ch in g[:14]:
        val = _CODE_POINTS.index(ch)
        product = val * factor
        total += product // 36 + product % 36
        factor = 2 if factor == 1 else 1
    check = (36 - (total % 36)) % 36
    return _CODE_POINTS[check] == g[14]


def gstin_is_valid(gstin: str) -> bool:
    return gstin_checksum_ok(gstin)


def dpiit_is_wellformed(number: str) -> bool:
    n = number.strip()
    return len(n) >= 5 and n.replace(" ", "").isalnum()
