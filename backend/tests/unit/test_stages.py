"""One stage vocabulary (task 1.1.8.1, arena R008).

Every module that reads a founder's stage must know every stage, so a founder
who has started selling is never scored as having nothing or matched to no one.
A module that meets a stage it has no mapping for fails here, not in front of a
founder.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from app.core.stages import (
    ORDER,
    ROUND_FITS,
    ROUND_FOR_STAGE,
    Stage,
    parse_stage,
    stages_funded_by,
)

ROOT = Path(__file__).parents[3]


def test_order_is_every_stage_once():
    assert list(ORDER) == list(Stage)
    assert [s.value for s in Stage] == [
        "idea",
        "poc",
        "prototype",
        "mvp",
        "revenue",
        "growth",
        "scale",
    ]


def test_parse_accepts_canonical_values_and_named_aliases_only():
    assert parse_stage("revenue") is Stage.REVENUE
    assert parse_stage(" MVP ") is Stage.MVP
    assert parse_stage(Stage.GROWTH) is Stage.GROWTH
    # the words readiness used before the shared vocabulary
    assert parse_stage("launched") is Stage.MVP
    assert parse_stage("scaling") is Stage.GROWTH
    assert parse_stage("seed") is None  # a funding round, not a stage
    assert parse_stage("") is None
    assert parse_stage(None) is None


# ---------------------------------------------------------------- coverage


def test_every_stage_raises_a_known_round():
    assert set(ROUND_FOR_STAGE) == set(Stage)
    assert set(ROUND_FOR_STAGE.values()) <= set(ROUND_FITS)


def test_every_published_investor_round_is_mapped():
    from app.ecosystem.index import DATA

    rows = json.loads(DATA.read_text(encoding="utf8")).get("investors", [])
    published = {s for r in rows for s in r.get("stages") or []}
    known = set().union(*ROUND_FITS.values())
    assert published and published <= known


def test_ecosystem_round_vocabulary_is_the_shared_one():
    from typing import get_args

    from app.ecosystem.incubators import STAGE_TO_INCUBATOR
    from app.ecosystem.match import STAGE_OK
    from app.models.ecosystem_schemas import Round as RoundLiteral

    assert STAGE_OK is ROUND_FITS
    assert set(get_args(RoundLiteral)) == set(ROUND_FITS)
    assert set(STAGE_TO_INCUBATOR) == set(ROUND_FITS)


def test_readiness_scores_every_stage_in_order():
    from app.funding.readiness import STAGE_SCORE

    assert set(STAGE_SCORE) == set(Stage)
    scores = [STAGE_SCORE[s] for s in ORDER]
    assert scores == sorted(scores) and scores[0] > 0


def test_investor_stages_are_all_canonical():
    from app.funding.investors import SEED_INVESTORS, real_investors

    canon = {s.value for s in Stage}
    for inv in [*SEED_INVESTORS, *real_investors()]:
        assert set(inv.stages) <= canon, inv.id


def test_every_stage_has_some_real_investor():
    from app.funding.investors import real_investors

    covered = {s for inv in real_investors() for s in inv.stages}
    assert covered == {s.value for s in Stage}


def test_stages_funded_by_inverts_round_fits():
    assert stages_funded_by(["pre_series_a"]) == ["revenue"]
    assert "revenue" in stages_funded_by(["seed"])
    assert stages_funded_by(["no_such_round"]) == []


def test_scheme_and_planner_stage_words_are_canonical():
    from app.planner.packs import load_packs
    from app.planner.roadmap import STAGES
    from app.schemes.annotate import PHASE_STAGES
    from app.schemes.seed import SEED_SCHEMES

    canon = {s.value for s in Stage}
    assert [s.value for s in ORDER] == STAGES
    assert set().union(*PHASE_STAGES.values()) == canon
    for scheme in SEED_SCHEMES:
        assert set(scheme.target_stages) <= canon, scheme.id
    for pack in load_packs().values():
        for t in pack.templates:
            assert t.done_from_stage is None or t.done_from_stage in canon, t.id


def test_elicitation_stage_words_are_canonical():
    from app.elicitation import answers, extract

    canon = set(Stage)
    assert set(extract._STAGE_STATE) <= canon
    assert set(extract._STAGE_STATE_PATTERNS) <= canon
    assert set(answers._STAGE_WORDS) <= canon


@pytest.mark.parametrize(
    "page", ["Funding.tsx", "Profile.tsx", "Schemes.tsx"], ids=lambda p: p.removesuffix(".tsx")
)
def test_frontend_pages_use_the_shared_stage_list(page):
    src = (ROOT / "frontend" / "src" / "pages" / page).read_text(encoding="utf8")
    assert 'from "../lib/stages"' in src
    assert "const STAGE =" not in src


def test_frontend_stage_list_matches_backend():
    src = (ROOT / "frontend" / "src" / "lib" / "stages.ts").read_text(encoding="utf8")
    m = re.search(r"STAGES\s*=\s*\[([^\]]*)\]", src)
    assert m, "STAGES list not found"
    assert re.findall(r'"([a-z_]+)"', m.group(1)) == [s.value for s in ORDER]


# ---------------------------------------------------------------- behaviour


FULL = {
    "founder_experience_years": 4,
    "team_size": 3,
    "feature_completeness": 80,
    "has_ip": True,
    "users": 5000,
    "monthly_revenue": 500_000,
}


def test_a_selling_founder_scores_above_a_prototype():
    from app.funding.readiness import score_readiness

    product = {s: score_readiness({**FULL, "stage": s.value}).dimensions["product"] for s in ORDER}
    assert product["revenue"] > product["mvp"] > product["prototype"]
    assert product["growth"] >= product["revenue"]
    assert all(v > 0 for v in product.values())


def test_a_selling_founder_is_shown_investors():
    from app.funding.investor_match import match_investors

    startup = {"sector": "agritech", "stage": "revenue", "users": 5000,
               "monthly_revenue": 500_000, "state": "Tamil Nadu"}  # fmt: skip
    res = match_investors(startup, funding_need=5_000_000, readiness_overall=80)
    assert res.eligible
    assert not any("not revenue" in r for i in res.ineligible for r in i.reasons
                   if i.investor.stages and "revenue" in i.investor.stages)  # fmt: skip


def test_legacy_stage_word_still_scores():
    from app.funding.readiness import score_readiness

    old = score_readiness({**FULL, "stage": "launched"}).dimensions["product"]
    new = score_readiness({**FULL, "stage": "mvp"}).dimensions["product"]
    assert old == new
