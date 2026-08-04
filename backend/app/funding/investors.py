"""Investor database seed (Task 4.1) — angels / VCs with preferences."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Investor:
    id: str
    name: str
    type: str  # angel | micro_vc | vc | corporate
    min_ticket: int  # ₹
    max_ticket: int  # ₹
    stages: list[str]
    sectors: list[str]
    geographies: list[str]
    min_users: int = 0
    min_revenue: int = 0  # ₹/month
    availability: str = "actively_investing"  # actively_investing | selective | not_investing
    exclusions: list[str] = field(default_factory=list)
    track_record_score: int = 60  # 0–100
    thesis: str = ""


SEED_INVESTORS: list[Investor] = [
    Investor(
        "angel_ravi",
        "Ravi (Angel)",
        "angel",
        500_000,
        3_000_000,
        ["idea", "poc", "prototype", "mvp", "seed"],
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
        ["mvp", "seed"],
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
        ["series_a", "growth"],
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
        ["mvp", "seed", "series_a"],
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
        ["mvp", "seed"],
        ["agritech", "saas"],
        ["India"],
        availability="not_investing",
        track_record_score=75,
        thesis="Currently not deploying.",
    ),
]
