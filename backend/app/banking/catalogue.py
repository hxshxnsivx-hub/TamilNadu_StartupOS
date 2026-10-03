"""Bank scheme catalogue loader (data/bank_schemes.json)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.banking.models import BankScheme, Requirements

DATA = Path(__file__).parent / "data"


def parse_scheme(d: dict) -> BankScheme:
    r = d.get("requires") or {}
    return BankScheme(
        id=d["id"],
        bank=d.get("bank"),
        name=d["name"],
        category=d["category"],
        min_lakh=d.get("min_lakh"),
        max_lakh=d.get("max_lakh"),
        purposes=tuple(d.get("purposes") or ()),
        collateral=d["collateral"],
        pricing=d.get("pricing", ""),
        for_whom=d.get("for_whom", ""),
        requires=Requirements(
            gst=bool(r.get("gst")),
            years_in_business=int(r.get("years_in_business") or 0),
            women_owned=bool(r.get("women_owned")),
            dpiit=bool(r.get("dpiit")),
            self_help_group=bool(r.get("self_help_group")),
        ),
        sector=d.get("sector"),
        status=d.get("status", "active"),
        offered_by_types=tuple(d["offered_by_types"]) if d.get("offered_by_types") else None,
        digital=bool(d.get("digital")),
        details=tuple(d.get("details") or ()),
        source_url=d.get("source_url", ""),
        confidence=d.get("confidence", "secondary"),
    )


@lru_cache
def load_schemes() -> tuple[BankScheme, ...]:
    raw = json.loads((DATA / "bank_schemes.json").read_text(encoding="utf8"))
    return tuple(parse_scheme(s) for s in raw["schemes"])
