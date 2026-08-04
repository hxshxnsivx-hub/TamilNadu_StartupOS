"""Unit tests for milestone scheme annotation."""

from app.schemes.annotate import annotate_roadmap
from app.swarms.roadmap import RoadmapSwarm

SELVI = {
    "founder": {
        "state": "Tamil Nadu",
        "gender": "female",
        "caste_category": "sc",
        "first_graduate": True,
        "age": 30,
    },
    "startup": {
        "entity_type": "private_limited",
        "stage": "idea",
        "dpiit_recognized": True,
        "incorporation_age_years": 1,
        "annual_revenue": 500_000,
    },
}


def _roadmap():
    return RoadmapSwarm().generate("An agri IoT device to help farmers with irrigation.")


def test_schemes_are_annotated_onto_milestones():
    rm = _roadmap()
    ann = annotate_roadmap(SELVI, rm)
    # at least some milestones carry schemes
    assert sum(len(v) for v in ann.values()) > 0


def test_each_scheme_placed_at_most_once():
    rm = _roadmap()
    ann = annotate_roadmap(SELVI, rm)
    all_ids = [s.id for schemes in ann.values() for s in schemes]
    assert len(all_ids) == len(set(all_ids))  # no duplicates across milestones


def test_scheme_matches_its_phase_stage():
    rm = _roadmap()
    ann = annotate_roadmap(SELVI, rm)
    from app.schemes.annotate import PHASE_STAGES

    by_id = {m.id: m for m in rm.milestones}
    for mid, schemes in ann.items():
        phase_stages = PHASE_STAGES.get(by_id[mid].phase.value, set())
        for s in schemes:
            assert set(s.target_stages) & phase_stages, f"{s.id} misplaced on {mid}"


def test_cap_per_milestone_respected():
    rm = _roadmap()
    ann = annotate_roadmap(SELVI, rm, cap=2)
    assert all(len(v) <= 2 for v in ann.values())
