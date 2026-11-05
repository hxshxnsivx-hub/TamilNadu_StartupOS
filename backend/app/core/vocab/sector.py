"""Sector as one join key, with a founder-facing layer (arena flag F-B4-022).

Two sector vocabularies existed: the elicitation ``Sector`` (12 values, with the
``"app"``-inside-a-word cues) and the ecosystem ``SECTORS`` (20 ids used by investor
and cohort matching). The 12-value list had no clean home for several ideas, and a
value from one never matched the other. Here the 20 ecosystem ids are the canonical
join key; the 12 founder-facing options map onto them (``ELICITATION_TO_SECTOR`` and
``SPOKEN_CHOICES``), and ``CATEGORY_OF`` gives the display label.
"""

from __future__ import annotations

import os
from enum import Enum

import structlog

log = structlog.get_logger(__name__)


class Sector(str, Enum):
    """The 20 ecosystem sectors — the join key for matching and aggregation."""

    EDTECH = "edtech"
    HEALTHTECH = "healthtech"
    BIOTECH_PHARMA = "biotech_pharma"
    FINTECH = "fintech"
    AGRITECH = "agritech"
    FOOD = "food"
    SAAS = "saas"
    DEEPTECH = "deeptech"
    MOBILITY = "mobility"
    AEROSPACE_DEFENCE = "aerospace_defence"
    CLEANTECH = "cleantech"
    LOGISTICS = "logistics"
    MEDIA = "media"
    CONSUMER = "consumer"
    PROPTECH = "proptech"
    TEXTILES = "textiles"
    MANUFACTURING = "manufacturing"
    ELECTRONICS = "electronics"
    HOSPITALITY = "hospitality"
    SERVICES = "services"


# Display label per sector (mirrors ecosystem/taxonomy.py SECTORS).
CATEGORY_OF: dict[Sector, str] = {
    Sector.EDTECH: "Education & learning",
    Sector.HEALTHTECH: "Health & medical",
    Sector.BIOTECH_PHARMA: "Biotech & pharma",
    Sector.FINTECH: "Finance & insurance",
    Sector.AGRITECH: "Agriculture & allied",
    Sector.FOOD: "Food & beverages",
    Sector.SAAS: "Software & IT",
    Sector.DEEPTECH: "Deep tech, AI & R&D",
    Sector.MOBILITY: "Automotive, EV & mobility",
    Sector.AEROSPACE_DEFENCE: "Aerospace & defence",
    Sector.CLEANTECH: "Energy, climate & recycling",
    Sector.LOGISTICS: "Logistics & transport",
    Sector.MEDIA: "Media, telecom & content",
    Sector.CONSUMER: "Consumer, retail & D2C",
    Sector.PROPTECH: "Real estate & construction",
    Sector.TEXTILES: "Textiles, apparel & leather",
    Sector.MANUFACTURING: "Industrial manufacturing",
    Sector.ELECTRONICS: "Electronics & hardware",
    Sector.HOSPITALITY: "Travel & hospitality",
    Sector.SERVICES: "Business services & HR",
}

# The old 12-value elicitation Sector enum, mapped onto the canonical sectors.
ELICITATION_TO_SECTOR: dict[str, Sector] = {
    "agri": Sector.AGRITECH,
    "textile": Sector.TEXTILES,
    "food": Sector.FOOD,
    "manufacturing": Sector.MANUFACTURING,
    "auto": Sector.MOBILITY,
    "electronics": Sector.ELECTRONICS,
    "it_services": Sector.SAAS,
    "health": Sector.HEALTHTECH,
    "education": Sector.EDTECH,
    "finance": Sector.FINTECH,
    "retail": Sector.CONSUMER,
    "other": Sector.SERVICES,
}

# The founder-facing choices shown by the sector question: (label, canonical sector).
# Every common Tamil Nadu idea has a home — food, education, retail and manufacturing
# included, which the old 12-category registry list lacked.
SPOKEN_CHOICES: list[tuple[str, Sector]] = [
    ("Agriculture & allied", Sector.AGRITECH),
    ("Food & beverages", Sector.FOOD),
    ("Textiles & apparel", Sector.TEXTILES),
    ("Manufacturing", Sector.MANUFACTURING),
    ("Automotive & EV", Sector.MOBILITY),
    ("Electronics & hardware", Sector.ELECTRONICS),
    ("Software & IT", Sector.SAAS),
    ("Health & medical", Sector.HEALTHTECH),
    ("Education & learning", Sector.EDTECH),
    ("Finance & insurance", Sector.FINTECH),
    ("Retail & consumer", Sector.CONSUMER),
    ("Something else", Sector.SERVICES),
]

_BY_VALUE = {s.value: s for s in Sector}


def _strict() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ


def to_sector(value: object) -> Sector | None:
    """Normalise a sector id, a legacy 12-enum value or a display label to a Sector."""
    if isinstance(value, Sector):
        return value
    if value is None:
        return None
    key = str(value).strip().lower()
    if not key:
        return None
    if key in _BY_VALUE:
        return _BY_VALUE[key]
    if key in ELICITATION_TO_SECTOR:
        return ELICITATION_TO_SECTOR[key]
    for sector, label in CATEGORY_OF.items():
        if label.lower() == key:
            return sector
    if _strict():
        raise ValueError(f"unknown sector {value!r}; add it to the mapping tables")
    log.warning("vocab.unknown_sector", value=str(value))
    return None
