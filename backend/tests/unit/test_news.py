"""Unit tests for the news pipeline: dedupe, ranking, and the guardrails."""

from datetime import date, timedelta

import pytest
from app.news import fixtures
from app.news.fetch import FixtureNewsFetcher, HttpNewsFetcher, _clamp
from app.news.models import FounderContext, RawArticle
from app.news.pipeline import (
    MAX_EXTRACT_CHARS,
    MAX_SUMMARY_CHARS,
    item_id,
    rank,
    summarise,
)
from app.news.sources import BY_ID, SOURCES, fetchable_sources, is_allowlisted


def _art(sid="startuptn", title="A scheme opens", days=1, extract="", tags=()):
    return RawArticle(
        source_id=sid,
        title=title,
        url=f"https://{BY_ID[sid].domain}/x/{title[:8].replace(' ', '-')}",
        published=(date.today() - timedelta(days=days)).isoformat(),
        extract=extract,
        tags=tags,
    )


# --- copyright guardrails ------------------------------------------------


def test_summary_never_exceeds_cap():
    long = "word " * 500
    s = summarise(_art(extract=long))
    assert len(s) <= MAX_SUMMARY_CHARS


def test_extract_is_clamped_at_the_boundary():
    # a provider handing back a whole article body must be trimmed, not trusted
    art = _clamp(_art(extract="x" * 5000))
    assert len(art.extract) <= MAX_EXTRACT_CHARS


def test_every_fixture_respects_the_extract_cap():
    for a in fixtures.ARTICLES:
        assert len(a.extract) <= MAX_EXTRACT_CHARS, a.title


def test_items_are_always_attributed():
    items = rank(fixtures.ARTICLES)
    assert items
    for i in items:
        assert i.source_name and i.url.startswith("http")


def test_unattributable_article_is_dropped():
    orphan = RawArticle("no_such_source", "Ghost", "https://x/y", date.today().isoformat())
    assert rank([orphan]) == []


# --- allowlist -----------------------------------------------------------


def test_allowlist_accepts_known_domains_and_subdomains():
    assert is_allowlisted("https://startuptn.in/feed/")
    assert is_allowlisted("https://www.thehindubusinessline.com/economy/x")


def test_allowlist_refuses_everything_else():
    assert not is_allowlisted("https://evil.example.com/startuptn.in")
    assert not is_allowlisted("https://startuptn.in.attacker.net/feed")


def test_allowlist_is_not_fooled_by_www_lookalikes():
    """Regression: `lstrip("www.")` strips characters, not the prefix.

    It reduced the registrable, unrelated domain "wwwstartuptn.in" to
    "startuptn.in", which the allowlist then accepted.
    """
    assert not is_allowlisted("https://wwwstartuptn.in/feed")
    assert not is_allowlisted("https://wwwyourstory.com/x")
    assert not is_allowlisted("https://wired.com/x")
    # genuine www. prefixes must still pass
    assert is_allowlisted("https://www.startuptn.in/feed")


def test_live_fetch_guard_raises_off_allowlist():
    with pytest.raises(PermissionError):
        HttpNewsFetcher.guard("https://not-allowed.example.com/a")


def test_no_source_is_fetchable_until_verified():
    # every source ships unverified on purpose; flipping one is a human decision
    assert fetchable_sources() == []
    assert all(not s.fetchable for s in SOURCES)


async def test_live_fetcher_refuses_rather_than_guessing():
    with pytest.raises(RuntimeError):
        await HttpNewsFetcher().fetch()


# --- dedupe --------------------------------------------------------------


def test_near_duplicate_stories_collapse_to_one():
    items = rank(fixtures.ARTICLES)
    titles = [i.title.lower() for i in items]
    dpiit = [t for t in titles if "dpiit" in t]
    assert len(dpiit) == 1, "the DPIIT story appears twice in the corpus"


def test_dedupe_keeps_the_more_trustworthy_source():
    items = rank(fixtures.ARTICLES)
    dpiit = next(i for i in items if "dpiit" in i.title.lower())
    # startupindia (government) must win over inc42 (trade)
    assert dpiit.source_id == "startupindia"
    assert "inc42" in dpiit.duplicates


def test_distinct_stories_are_not_merged():
    a = _art(title="Cluster support for Coimbatore MSMEs")
    b = _art(sid="yourstory", title="Agritech startup raises seed round")
    assert len(rank([a, b])) == 2


# --- ranking -------------------------------------------------------------


def test_recent_beats_stale_all_else_equal():
    # titles must be genuinely distinct, or dedupe (correctly) collapses them
    fresh = _art(title="Grant applications open for solar units", days=0)
    stale = _art(title="Subsidy window opens for textile exporters", days=25)
    items = rank([fresh, stale])
    assert len(items) == 2, "these are different stories and must not merge"
    assert items[0].published > items[1].published


def test_government_source_outranks_trade_at_equal_actionability():
    # both carry two actionable cues, so only source trust separates them
    gov = _art("startupindia", title="Grant applications open for founders", days=5)
    trade = _art("entrackr", title="Subsidy window opens for exporters", days=5)
    by_id = {i.source_id: i.score for i in rank([gov, trade])}
    assert by_id["startupindia"] > by_id["entrackr"]


def test_actionability_can_outweigh_source_trust():
    """A trade story a founder can act on beats an official one they cannot.

    Deliberate: the board exists to surface things worth doing, so actionability
    is allowed to overcome a tier gap. Documented because it is easy to mistake
    for a trust-weighting bug.
    """
    gov_inert = _art("startupindia", title="Policy update for founders", days=5)
    trade_actionable = _art("entrackr", title="Cohort applications open", days=5)
    by_id = {i.source_id: i.score for i in rank([gov_inert, trade_actionable])}
    assert by_id["entrackr"] > by_id["startupindia"]


def test_sector_match_raises_relevance_and_is_explained():
    art = _art("yourstory", title="Agritech startup raises seed round", tags=("agritech",))
    plain = rank([art])[0]
    tuned = rank([art], FounderContext(sector="agritech"))[0]
    assert tuned.score > plain.score
    assert any("agritech" in w for w in tuned.why)


def test_actionable_items_are_surfaced():
    act = _art(
        title="Applications open, last date this month", extract="Apply before the deadline."
    )
    info = _art(title="Sector grew modestly", extract="Analysts noted steady expansion.")
    items = rank([act, info])
    assert items[0].title.startswith("Applications open")
    assert any("act on" in w for w in items[0].why)


def test_every_item_explains_its_ranking():
    for i in rank(fixtures.ARTICLES, FounderContext(sector="agritech", district="Coimbatore")):
        assert i.why, f"{i.title} ranked with no reason given"
        assert len(i.why) <= 3


def test_scores_are_bounded_and_sorted():
    items = rank(fixtures.ARTICLES)
    scores = [i.score for i in items]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s <= 100 for s in scores)


def test_item_ids_are_stable_across_processes():
    """Guards against `hash()`, which is per-process randomised.

    Unstable ids would break client caching, list keys and read-tracking, and
    the breakage is invisible in a single-process test run.
    """
    import subprocess
    import sys

    code = (
        "from app.news.pipeline import rank;"
        "from app.news import fixtures;"
        "print([i.id for i in rank(fixtures.ARTICLES)][:4])"
    )
    runs = {
        subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        ).stdout.strip()
        for _ in range(2)
    }
    assert len(runs) == 1, f"ids differ between processes: {runs}"


def test_item_id_is_a_pure_function_of_source_and_url():
    a = item_id("startuptn", "https://startuptn.in/a")
    b = item_id("startuptn", "https://startuptn.in/a")
    c = item_id("startuptn", "https://startuptn.in/b")
    assert a == b and a != c


def test_ranking_is_deterministic():
    a = rank(fixtures.ARTICLES, FounderContext(sector="agritech"))
    b = rank(fixtures.ARTICLES, FounderContext(sector="agritech"))
    assert [i.id for i in a] == [i.id for i in b]


def test_malformed_date_does_not_crash_ranking():
    bad = RawArticle("startuptn", "Undated", "https://startuptn.in/u", "not-a-date")
    assert len(rank([bad])) == 1


def test_tamil_article_survives_the_pipeline():
    items = rank(fixtures.ARTICLES)
    ta = [i for i in items if i.language == "ta"]
    assert ta and ta[0].summary


async def test_fixture_fetcher_returns_the_corpus():
    arts = await FixtureNewsFetcher().fetch()
    assert len(arts) == len(fixtures.ARTICLES)
