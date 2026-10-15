"""One sector vocabulary for companies, startups and investors.

Companies come from the MCA register, classified by NIC 2004 industry code.
Startups come from a directory, classified by its category label. Investors are
classified from the words of their own thesis. All three map to the sector ids
below, so a founder in edtech can be matched to edtech investors, edtech peers
and the companies that buy from or supply edtech.
"""

from __future__ import annotations

import re

SECTORS: dict[str, str] = {
    "edtech": "Education & learning",
    "healthtech": "Health & medical",
    "biotech_pharma": "Biotech & pharma",
    "fintech": "Finance & insurance",
    "agritech": "Agriculture & allied",
    "food": "Food & beverages",
    "saas": "Software & IT",
    "deeptech": "Deep tech, AI & R&D",
    "mobility": "Automotive, EV & mobility",
    "aerospace_defence": "Aerospace & defence",
    "cleantech": "Energy, climate & recycling",
    "logistics": "Logistics & transport",
    "media": "Media, telecom & content",
    "consumer": "Consumer, retail & D2C",
    "proptech": "Real estate & construction",
    "textiles": "Textiles, apparel & leather",
    "manufacturing": "Industrial manufacturing",
    "electronics": "Electronics & hardware",
    "hospitality": "Travel & hospitality",
    "services": "Business services & HR",
}

# NIC 2004 division (first two digits) -> sector. Finer codes override below.
NIC_DIVISION = {
    "01": "agritech", "02": "agritech", "05": "agritech",
    "10": "manufacturing", "11": "manufacturing", "13": "manufacturing", "14": "manufacturing",
    "15": "food", "16": "food",
    "17": "textiles", "18": "textiles", "19": "textiles",
    "20": "manufacturing", "21": "manufacturing", "22": "media", "23": "manufacturing",
    "24": "manufacturing", "25": "manufacturing", "26": "manufacturing",
    "27": "manufacturing", "28": "manufacturing", "29": "manufacturing",
    "30": "electronics", "31": "electronics", "32": "electronics", "33": "electronics",
    "34": "mobility", "35": "mobility", "36": "consumer", "37": "cleantech",
    "40": "cleantech", "41": "cleantech",
    "45": "proptech", "50": "mobility", "51": "consumer", "52": "consumer", "55": "hospitality",
    "60": "logistics", "61": "logistics", "62": "logistics", "63": "logistics", "64": "media",
    "65": "fintech", "66": "fintech", "67": "fintech", "70": "proptech", "71": "services",
    "72": "saas", "73": "deeptech", "74": "services", "80": "edtech", "85": "healthtech",
    "90": "cleantech", "92": "media", "93": "services",
}  # fmt: skip
NIC_CLASS = {
    "2423": "biotech_pharma",  # pharmaceuticals, medicinal chemicals
    "3311": "healthtech",  # medical and surgical equipment
    "3530": "aerospace_defence",  # aircraft and spacecraft
    "2927": "aerospace_defence",  # weapons and ammunition
    "6303": "hospitality",  # travel agencies and tour operators
    "7430": "media",  # advertising
    "7491": "services",  # labour recruitment
}


def sector_of_nic(code: str) -> str | None:
    code = (code or "").strip()
    if not code[:2].isdigit():
        return None
    return NIC_CLASS.get(code[:4]) or NIC_DIVISION.get(code[:2])


# Directory categories and investor thesis words -> sector. Checked in order;
# a text can carry several sectors.
KEYWORDS: list[tuple[str, re.Pattern]] = [
    (s, re.compile(p, re.I))
    for s, p in [
        ("edtech", r"\bed[- ]?tech|education|learning|edutech|skilling|school|k-?12\b"),
        ("healthtech", r"health|medtech|medical|hospital|diagnost|wellness|care\b"),
        ("biotech_pharma", r"biotech|pharma|life ?science|drug|genomic"),
        ("fintech", r"fin[- ]?tech|financial (?:services|inclusion)|inclusive finance|"
                    r"microfinance|lending|payments?\b|insur|banking|wealth ?tech"),
        ("agritech", r"agri|farm|dairy|aquacult|fisher|livestock"),
        ("food", r"food|beverage|restaurant|nutrition|bakery"),
        ("saas", r"\bsaas\b|software|enterprise tech|b2b tech|cloud|developer tools|it services"),
        ("deeptech", r"deep[- ]?tech|\bai\b|artificial intelligence|machine learning|robot|"
                     r"quantum|semiconductor|\biot\b|computer vision"),
        ("mobility", r"\bev\b|electric vehicle|mobility|automotive|auto ?components?"),
        ("aerospace_defence", r"aero|defen[cs]e|drone|\bspace ?tech|\bspace\b|satellite"),
        ("cleantech", r"clean ?tech|climate|energy|solar|renewable|recycl|waste|sustainab"),
        ("logistics", r"logistic|supply chain|transport|freight|shipping|warehous"),
        ("media", r"media|content|gaming|entertainment|telecom|marketing tech|adtech"),
        ("consumer", r"consumer|d2c|retail|e-?commerce|brand|marketplace|fashion"),
        ("proptech", r"prop[- ]?tech|real estate|construction|housing|built environment"),
        ("textiles", r"textile|apparel|garment|knit|yarn|leather"),
        ("manufacturing", r"manufactur|industrial|industry 4|engineering|machin|foundry|pump"),
        ("electronics", r"electronic|hardware|\besdm\b|embedded|pcb|device"),
        ("hospitality", r"travel|tourism|hospitality|hotel"),
        ("services", r"\bhr ?tech|recruit|staffing|legal ?tech|consult"),
    ]
]  # fmt: skip

# Thesis phrases that mean "any sector".
AGNOSTIC = re.compile(r"sector[- ]agnostic|agnostic|all sectors|multi[- ]sector|generalist", re.I)


def sectors_in(text: str) -> list[str]:
    """Sectors named in free text, in taxonomy order; [] when none."""
    text = text or ""
    return [s for s, pat in KEYWORDS if pat.search(text)]
