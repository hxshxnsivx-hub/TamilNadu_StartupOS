"""Levers worded for the founder's domain and sector at narration time (task 1.2.2, R190)."""

from __future__ import annotations

from app.research import levers

SCOPE = "the 654 startups on the Tamil Nadu Startup Map in Chennai, Coimbatore and Madurai"
LOCALISE = {
    "kind": "localise",
    "facts": {"india_papers": 25, "world_papers": 2335, "tn_scope": SCOPE},
}
CROWDED = {"kind": "business model", "facts": {}}


def test_localise_is_worded_for_three_sectors():
    """1.2.2.2: a banana-chips unit, a t-shirt brand and a health device each hear their
    own routines; only the health product hears of hospitals."""
    food = levers.render(LOCALISE, domain_id="banana_value_added")["text"]
    textile = levers.render(LOCALISE, domain_id="knitwear_small_batch")["text"]
    health = levers.render(LOCALISE, sector="health")["text"]
    assert "local tastes and shop routines" in food
    assert "mills, job-work units and buyers" in textile
    assert "hospital and clinic routines" in health
    assert "hospital" not in food and "hospital" not in textile
    assert len({food, textile, health}) == 3
    for text in (food, textile, health):
        assert text.startswith("Make it fit Tamil Nadu, with the Tamil language")
        assert ":" not in text  # narration adds the sentence's one colon


def test_business_model_fits_the_sector():
    """A tea brand is not told to rent its tea; a machine still may be."""
    tea = levers.render(CROWDED, domain_id="tea_infusions")["text"]
    pump = levers.render(CROWDED, domain_id="pump_motor_controllers")["text"]
    assert "rental" not in tea and "subscriptions" in tea
    assert "rental" in pump


def test_the_founders_sector_rewords_without_a_new_search():
    """The same stored lever, said after the sector is answered and again after it is
    corrected: the words follow the sector, the facts stay."""
    before = levers.render(LOCALISE)
    food = levers.render(LOCALISE, sector="food")
    textile = levers.render(LOCALISE, sector="textile")
    assert "local routines" in before["text"]
    assert "local tastes" in food["text"] and "job-work units" in textile["text"]
    assert food["because"] == textile["because"] == before["because"]
    assert "25 of 2,335 papers are from India" in food["because"] and SCOPE in food["because"]


def test_the_founders_sector_comes_before_the_domain():
    """The founder's own answer wins over the registry's guess (the R035 rule)."""
    text = levers.render(LOCALISE, domain_id="banana_value_added", sector="agri")["text"]
    assert "farm seasons" in text and "local tastes" not in text


def test_cost_down_names_the_matched_domain():
    lever = {"kind": "cost-down", "facts": {"domain": "banana_value_added"}}
    r = levers.render(lever)
    assert r["text"] == (
        "Compete on cost, using Vanigam's costing for banana value-added products to see"
        " where to cut."
    )
    assert r["because"] == "a Vanigam cost pack exists for this domain"


def test_counts_come_only_from_the_facts():
    combine = {"kind": "combine", "facts": {"a": "brain waves", "b": "nurse call", "papers": 1}}
    r = levers.render(combine, sector="food")
    assert r["text"] == "Build your version around joining brain waves with nurse call."
    assert r["because"] == "only 1 paper covers both"
    reg = levers.render({"kind": "regulatory route", "facts": {"trials": 0}})
    assert "0" not in reg["because"] and "communication aid" not in reg["text"]
    assert (
        "1 clinical trial came"
        in levers.render({"kind": "regulatory route", "facts": {"trials": 1}})["because"]
    )


def test_a_lever_saved_before_facts_keeps_its_own_counts():
    """An older session's lever has text and because but no facts: its reasons stay, and
    the localise wording no longer says hospital to a food brand."""
    old = {
        "kind": "localise",
        "text": "Make it fit Tamil Nadu, with the Tamil language, local hospital or market"
        " routines, and a local price.",
        "because": "25 of 2,335 papers are from India",
    }
    r = levers.render(old, domain_id="knitwear_small_batch")
    assert "hospital" not in r["text"] and r["because"] == old["because"]
    combine = {"kind": "combine", "text": "Join a with b.", "because": "only 3 papers cover both"}
    # its words stay; it gains only its stable id, from its kind and words (R041)
    assert levers.render(combine, sector="food") == {**combine, "id": levers.lever_id(combine)}


def test_worded_leaves_the_stored_result_alone():
    nov = {"statement": {"type": "context"}, "levers": [LOCALISE]}
    out = levers.worded(nov, sector="food")
    assert "local tastes" in out["levers"][0]["text"]
    assert "text" not in nov["levers"][0]
    assert levers.worded(None) is None
