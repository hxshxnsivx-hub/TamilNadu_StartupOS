"""Investors for matching (Task 4.1).

real_investors(): the Tamil Nadu investors from the ecosystem layer (TN Startup
Map), translated to the matcher's terms. What the source does not say stays
unknown: most do not publish a ticket size, so the ticket is not checked for
them and the match says so. These are the investors founders see.

SEED_INVESTORS: invented examples with complete figures, used only as test
fixtures for the matching rules. They are never shown to founders.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache

from app.core.stages import stages_funded_by


@dataclass
class Investor:
    id: str
    name: str
    type: str  # angel | micro_vc | vc | corporate
    min_ticket: int  # ₹
    max_ticket: int  # ₹
    stages: list[str]  # founder stages (app.core.stages.Stage values) it funds
    sectors: list[str]
    geographies: list[str]
    min_users: int = 0
    min_revenue: int = 0  # ₹/month
    availability: str = "actively_investing"  # actively_investing | selective | not_investing
    exclusions: list[str] = field(default_factory=list)
    track_record_score: int = 60  # 0–100
    thesis: str = ""
    ticket_known: bool = True
    # no source rates investors: 60 is a neutral value for ranking, never shown
    track_record_known: bool = True
    not_investing_reason: str = ""
    source_url: str | None = None


SEED_INVESTORS: list[Investor] = [
    Investor(
        "angel_ravi",
        "Ravi (Angel)",
        "angel",
        500_000,
        3_000_000,
        ["idea", "poc", "prototype", "mvp"],
        ["agritech", "foodtech"],
        ["Tamil Nadu"],
        availability="actively_investing",
        track_record_score=70,
        thesis="Early Tamil Nadu agri & food founders.",
    ),
    Investor(
        "greenshoot_vc",
        "Greenshoot Ventures",
        "micro_vc",
        2_000_000,
        15_000_000,
        ["mvp", "revenue"],
        ["agritech", "cleantech", "healthtech"],
        ["Tamil Nadu", "Karnataka"],
        min_users=500,
        min_revenue=50_000,
        availability="selective",
        track_record_score=80,
        thesis="Seed-stage climate & agri tech in South India.",
    ),
    Investor(
        "meridian_vc",
        "Meridian Capital",
        "vc",
        20_000_000,
        100_000_000,
        ["growth", "scale"],
        ["fintech", "saas"],
        ["India"],
        min_users=10_000,
        min_revenue=500_000,
        availability="actively_investing",
        track_record_score=90,
        thesis="Series A fintech & SaaS.",
    ),
    Investor(
        "lakshmi_angel",
        "Lakshmi (Angel)",
        "angel",
        300_000,
        2_000_000,
        ["idea", "mvp"],
        ["edtech", "healthtech"],
        ["Tamil Nadu"],
        availability="actively_investing",
        track_record_score=65,
        thesis="Early edtech & healthtech.",
    ),
    Investor(
        "agri_corp_vc",
        "AgriCorp Ventures",
        "corporate",
        5_000_000,
        40_000_000,
        ["mvp", "revenue", "growth"],
        ["agritech"],
        ["India"],
        min_users=1_000,
        min_revenue=100_000,
        availability="selective",
        track_record_score=85,
        thesis="Agri supply-chain & inputs.",
    ),
    Investor(
        "dormant_fund",
        "Dormant Fund",
        "vc",
        1_000_000,
        20_000_000,
        ["mvp", "revenue"],
        ["agritech", "saas"],
        ["India"],
        availability="not_investing",
        track_record_score=75,
        thesis="Currently not deploying.",
    ),
]


_TYPE = {"venture": "vc", "angel": "angel", "growth": "vc", "private_credit": "lender"}
ALL_SECTORS = "__all__"


@lru_cache
def real_investors() -> tuple[Investor, ...]:
    from app.ecosystem.index import DATA

    if not DATA.exists():
        return ()
    rows = json.loads(DATA.read_text(encoding="utf8")).get("investors", [])
    out = []
    for r in rows:
        # the source publishes rounds; the matcher compares founder stages
        stages = stages_funded_by(r.get("stages") or [])
        ticket = r.get("ticket_lakh")
        lo, hi = (int(ticket[0] * 100_000), int(ticket[1] * 100_000)) if ticket else (0, 0)
        reason = ""
        if not r.get("serves_founders"):
            reason = r.get("not_for_founders_reason") or "does not invest in startups"
        elif r.get("instrument") == "debt":
            reason = "lends money; does not buy shares"
        out.append(
            Investor(
                id=r["slug"],
                name=r["name"],
                type=_TYPE.get(r.get("asset_class") or "", r.get("asset_class") or "other"),
                min_ticket=lo,
                max_ticket=hi,
                stages=stages,
                sectors=[ALL_SECTORS] if r.get("generalist") else list(r.get("sectors") or []),
                geographies=["Tamil Nadu"],
                availability="not_investing" if reason else "actively_investing",
                thesis=r.get("summary") or "",
                ticket_known=bool(ticket),
                track_record_known=False,
                not_investing_reason=reason,
                source_url=r.get("source_url"),
            )
        )
    return tuple(out)
