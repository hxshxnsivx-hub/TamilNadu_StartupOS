"""The fact check before speech: what passes, what is dropped, what is replaced."""

from __future__ import annotations

from app.agents.grounding import NOVELTY_LINE, SentenceSplitter, check_reply, facts_from, gate

FACTS = facts_from(
    {"trials": {"total": 23, "items": [{"id": "NCT01234567"}]}, "papers": {"total": 1200}},
    {"schemes": [{"id": "pmegp"}]},
    "capital ₹2–10 lakh",
)


def test_backed_numbers_schemes_and_ids_pass():
    assert gate("I found 23 trials, such as NCT01234567.", FACTS)
    assert gate("There are about 1,200 papers.", FACTS)
    assert gate("PMEGP gives a subsidy on the project cost.", FACTS)
    assert gate("With ₹10 lakh you can start.", FACTS)


def test_unbacked_claims_are_dropped():
    assert gate("There are 4,500 papers.", FACTS) is None
    assert gate("Your budget of ₹50 lakh works.", FACTS) is None
    assert gate("TANSEED will fund you.", FACTS) is None
    assert gate("Trial NCT99999999 is close.", FACTS) is None
    assert gate("A 2019 review covers it.", FACTS) is None


def test_common_words_are_not_mistaken_for_schemes():
    assert gate("The founder needs a hospital partner.", FACTS)  # NEEDS is a scheme


def test_small_counts_pass_and_novelty_is_replaced():
    assert gate("Let us look at 3 questions.", FACTS)
    assert gate("This is a unique idea.", FACTS) == NOVELTY_LINE


def test_check_reply_says_the_caveat_once():
    kept, dropped = check_reply("It is unique. It is novel. Who pays? We have 99 papers.", FACTS)
    assert kept == [NOVELTY_LINE, "Who pays?"] and len(dropped) == 1


def test_splitter_keeps_abbreviations_and_decimals_whole():
    sp = SentenceSplitter()
    assert sp.feed("Dr. Ravi said 4.5 is fine. See NCT01234567. Next") == [
        "Dr. Ravi said 4.5 is fine.",
        "See NCT01234567.",
    ]
    assert sp.flush() == ["Next"]
