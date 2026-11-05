"""Canonical vocabulary (arena theme T01): stage, sector and Tamil-safe cues."""

from __future__ import annotations

import pytest
from app.core.vocab import (
    CATEGORY_OF,
    ELICITATION_TO_SECTOR,
    LEGACY_STAGE,
    ROUND_STAGES,
    SPOKEN_CHOICES,
    Cues,
    Round,
    Sector,
    Stage,
    boundary_hits,
    to_round,
    to_sector,
    to_stage,
)

# ---- stage (F-A4-015) -------------------------------------------------------


@pytest.mark.parametrize("word", list(LEGACY_STAGE))
def test_every_legacy_stage_word_maps(word: str) -> None:
    assert isinstance(to_stage(word), Stage)


def test_readiness_and_investor_spellings_converge() -> None:
    assert to_stage("launched") is Stage.REVENUE  # readiness spelling
    assert to_stage("scaling") is Stage.GROWTH
    assert to_stage("scale") is Stage.GROWTH  # investors spelling


def test_stage_is_ordered_so_revenue_outranks_mvp() -> None:
    assert Stage.REVENUE >= Stage.MVP
    assert Stage.REVENUE > Stage.MVP
    assert Stage.IDEA < Stage.GROWTH


def test_unknown_stage_raises_under_tests() -> None:
    with pytest.raises(ValueError):
        to_stage("unicorn")


def test_round_is_separate_from_stage() -> None:
    assert to_round("series_a") is Round.SERIES_A
    # a Series A investor expects an MVP/revenue company, not the word "series_a"
    assert Stage.REVENUE in ROUND_STAGES[Round.SERIES_A]
    assert Stage.IDEA in ROUND_STAGES[Round.PRE_SEED]


# ---- sector (F-B4-022) ------------------------------------------------------


def test_twenty_canonical_sectors_all_have_labels() -> None:
    assert len(Sector) == 20
    assert set(CATEGORY_OF) == set(Sector)


@pytest.mark.parametrize("name", ["food", "education", "retail", "manufacturing"])
def test_common_categories_have_a_home(name: str) -> None:
    # the old 12-category registry list dropped these; the founder-facing list keeps them
    assert to_sector(name) is not None
    labels = {label.lower() for label in CATEGORY_OF.values()}
    assert any(name in label for label in labels)


def test_every_legacy_elicitation_sector_maps() -> None:
    for legacy, sector in ELICITATION_TO_SECTOR.items():
        assert to_sector(legacy) is sector


def test_spoken_choices_cover_the_common_sectors() -> None:
    sectors = {s for _, s in SPOKEN_CHOICES}
    assert {Sector.FOOD, Sector.EDTECH, Sector.CONSUMER, Sector.MANUFACTURING} <= sectors


def test_sector_display_label_round_trips() -> None:
    assert to_sector("Agriculture & allied") is Sector.AGRITECH


# ---- Tamil-safe cues (F-B4-003) ---------------------------------------------


def test_cue_does_not_match_inside_a_longer_latin_word() -> None:
    assert boundary_hits("a saas app", "app") is True
    assert boundary_hits("vendors in Tiruchirappalli", "app") is False
    assert boundary_hits("a garment and apparel unit", "app") is False


def test_cue_is_safe_inside_tamil_text() -> None:
    # "app" must not match inside a Tamil word; a real token still matches
    assert boundary_hits("சென்னையில் ஒரு app", "app") is True
    assert boundary_hits("தமிழ்நாட்டில் விவசாயம்", "app") is False


def test_cues_returns_every_matching_value() -> None:
    table = {
        Sector.FINTECH: ("loan", "payment", "credit"),
        Sector.AGRITECH: ("farm", "dairy", "crop"),
        Sector.SAAS: ("app", "software", "platform"),
    }
    cues = Cues(table)
    hits = set(cues.hits("a loan app for dairy farmers"))
    assert Sector.FINTECH in hits  # loan
    assert Sector.AGRITECH in hits  # dairy
    assert Sector.SAAS in hits  # app (whole word here)


def test_cues_first_is_deterministic() -> None:
    cues = Cues({Sector.FOOD: ("snack",), Sector.TEXTILES: ("yarn",)})
    assert cues.first("a yarn and snack shop") in {Sector.FOOD, Sector.TEXTILES}
    assert cues.first("nothing here") is None
