"""Whole-word keyword cues (task 1.1.8.2, arena R027).

A sector read at 0.90 is never asked again, so a cue that fires inside another
word ('app' in Tiruchirappalli, 'crop' in microprocessor) silently routes the
founder to the wrong schemes. These are the traps the arena run found, plus the
plain cases that must keep working.
"""

from __future__ import annotations

import pytest
from app.elicitation.answers import validate
from app.elicitation.cues import compile_cues, matches
from app.elicitation.extract import extract
from app.elicitation.slots import FundingRoute, ProductForm, Sector


def _slot(text: str, key: str):
    return next((e.value for e in extract(text) if e.key == key), None)


@pytest.mark.parametrize(
    "text, wrong",
    [
        ("Of course I want to sell jasmine garlands", Sector.EDUCATION),
        ("A microprocessor trainer kit for colleges", Sector.AGRI),
        ("A workshop that repairs looms", Sector.RETAIL),
        ("Carbon credit tracking for solar rooftops", Sector.FINANCE),
        ("A banana fibre unit in Tiruchirappalli", Sector.IT_SERVICES),
        ("We will happily serve customers", Sector.IT_SERVICES),
        ("Home automation kits for flats", Sector.AUTO),
        ("A community kitchen", Sector.IT_SERVICES),
        ("I am an educated woman from Madurai who makes pickles", Sector.EDUCATION),
        ("I am a well educated engineer starting a tailoring unit", Sector.EDUCATION),
    ],
)
def test_a_cue_inside_another_word_is_not_a_sector(text, wrong):
    assert _slot(text, "sector") != wrong


@pytest.mark.parametrize(
    "text",
    [
        "A banana fibre unit in Tiruchirappalli",
        "We will happily serve customers",
        "a soap unit for apparel stores",
    ],
)
def test_app_inside_a_word_is_not_software(text):
    assert _slot(text, "product_form") != ProductForm.SOFTWARE


def test_carbon_credit_is_not_a_loan():
    assert _slot("Carbon credit tracking for solar rooftops", "funding_route") != FundingRoute.DEBT


@pytest.mark.parametrize(
    "text, sector",
    [
        ("We run small farms near Thanjavur", Sector.AGRI),
        ("Organic farming kits for farmers", Sector.AGRI),
        ("agritech advisory for paddy", Sector.AGRI),
        ("a weaving cluster in Erode", Sector.TEXTILE),
        ("garments for export", Sector.TEXTILE),
        ("small bakeries in Madurai", Sector.FOOD),
        ("a manufacturing unit for brackets", Sector.MANUFACTURING),
        ("spare parts for two wheelers", Sector.AUTO),
        ("an app for tailors", Sector.IT_SERVICES),
        ("healthcare at home for elders", Sector.HEALTH),
        ("online courses for nurses", Sector.EDUCATION),
        ("credit for small shops", Sector.FINANCE),
        ("a chain of shops", Sector.RETAIL),
        # compounds and longer forms the substring matcher reached, listed explicitly
        ("automotive components", Sector.AUTO),
        ("autoparts dealer", Sector.AUTO),
        ("a mobile application for tailors", Sector.IT_SERVICES),
        ("seafood export from Thoothukudi", Sector.FOOD),
        ("foodtech for canteens", Sector.FOOD),
        ("agricultural machinery rental", Sector.AGRI),
        ("farmland leasing", Sector.AGRI),
        ("clinical trial logistics", Sector.HEALTH),
        ("educational toys", Sector.EDUCATION),
        ("a preschool in Salem", Sector.EDUCATION),
        ("online shopping for villages", Sector.RETAIL),
        ("a supply van for shopkeepers", Sector.RETAIL),
        ("telehealth for villages", Sector.HEALTH),
        ("biomedical waste pickup", Sector.HEALTH),
        ("insurtech for gig workers", Sector.FINANCE),
    ],
)
def test_whole_words_and_their_plain_forms_still_match(text, sector):
    assert _slot(text, "sector") == sector


@pytest.mark.parametrize(
    "text, form",
    [
        ("a mobile application for tailors", ProductForm.SOFTWARE),
        ("web application for clinics", ProductForm.SOFTWARE),
        ("agricultural machinery rental", ProductForm.PHYSICAL),
        ("a production line for brackets", ProductForm.PHYSICAL),
        ("servicing tractors in villages", ProductForm.SERVICE),
    ],
)
def test_product_form_compounds_still_match(text, form):
    assert _slot(text, "product_form") == form


def test_seed_funded_still_reads_as_grant():
    assert _slot("We were seed funded by the state", "funding_route") == FundingRoute.GRANT


def test_loan_still_reads_as_debt():
    assert _slot("I will take a bank loan of 5 lakh", "funding_route") == FundingRoute.DEBT


def test_stage_cues_are_whole_words():
    # 'revenue' cue must not fire inside another word; 'we sell' not inside 'we sellotape'
    assert _slot("we sellotape boxes for a living", "stage") is None
    assert _slot("We are already selling to 40 shops", "stage") == "revenue"


def test_direct_stage_answer_is_whole_word():
    assert validate("stage", "we have a prototype") == "prototype"
    assert validate("stage", "ideally soon") is None  # 'idea' inside 'ideally'


def test_compile_cues_prefix_and_word_forms():
    pats = compile_cues(("weav*", "shop", "factory"))
    assert matches("handloom weavers", pats)
    assert matches("two shops", pats)
    assert matches("three factories", pats)
    assert not matches("a workshop", pats)
    assert not matches("shopify", pats)
