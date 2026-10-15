"""Example B2B suppliers for tests and demos (Task 3.1).

The clusters are real (Tiruppur yarn, Sivakasi printing, Hosur electronics), but
these companies, prices, capacities and trust scores are invented examples. They
are never offered to founders as suppliers: real companies come from the MCA
directory (app/b2b/directory.py), and prices only from quotes the founder enters.
"""

from __future__ import annotations

from app.b2b.models import SupplyProfile, Tier

M = Tier.T1_MATERIALS

SEED_SUPPLY: list[SupplyProfile] = [
    # Tiruppur — knitwear / yarn
    SupplyProfile(
        "y1",
        "Tiruppur Cotton Mills",
        "yarn",
        M,
        "combed cotton yarn 40s count",
        180.0,
        10_000,
        500,
        "Tiruppur",
        "Tamil Nadu",
        trust_score=85,
    ),
    SupplyProfile(
        "y2",
        "Salem Spinners",
        "yarn",
        M,
        "combed cotton yarn 40s count",
        210.0,
        8_000,
        1_000,
        "Salem",
        "Tamil Nadu",
        trust_score=60,
    ),
    # Erode — dyes
    SupplyProfile(
        "d1",
        "Erode Natural Dyes",
        "dye",
        M,
        "natural indigo & turmeric dye",
        450.0,
        5_000,
        200,
        "Erode",
        "Tamil Nadu",
        trust_score=82,
        payment_mode="either",
    ),
    # Chennai / Coimbatore — food-grade packaging
    SupplyProfile(
        "p1",
        "Chennai FlexiPack",
        "packaging",
        M,
        "food-grade stand-up pouch 200ml",
        7.0,
        100_000,
        1_000,
        "Chennai",
        "Tamil Nadu",
        trust_score=78,
    ),
    SupplyProfile(
        "p2",
        "Coimbatore PackTech",
        "packaging",
        M,
        "food-grade stand-up pouch 200ml",
        9.0,
        50_000,
        2_000,
        "Coimbatore",
        "Tamil Nadu",
        trust_score=70,
    ),
    # Coimbatore — PCB & pumps
    SupplyProfile(
        "pcb1",
        "Kovai PCB Works",
        "pcb",
        M,
        "2-layer FR4 PCB fabrication",
        120.0,
        2_000,
        50,
        "Coimbatore",
        "Tamil Nadu",
        trust_score=88,
    ),
    SupplyProfile(
        "pu1",
        "Coimbatore Pumpsets",
        "pump",
        M,
        "5HP submersible pump motor",
        3_500.0,
        500,
        5,
        "Coimbatore",
        "Tamil Nadu",
        trust_score=90,
    ),
    # Hosur — electronics sensors
    SupplyProfile(
        "s1",
        "Hosur Sensor Systems",
        "sensor",
        M,
        "soil moisture & temperature sensor",
        240.0,
        3_000,
        100,
        "Hosur",
        "Tamil Nadu",
        trust_score=76,
    ),
    # Sivakasi — printing
    SupplyProfile(
        "pr1",
        "Sivakasi Print House",
        "printing",
        M,
        "offset carton & label printing",
        3.5,
        200_000,
        5_000,
        "Sivakasi",
        "Tamil Nadu",
        trust_score=80,
    ),
]
