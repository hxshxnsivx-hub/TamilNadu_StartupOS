"""Unit tests for the Roadmap Swarm — milestones, topo sort, critical path."""

import pytest
from app.swarms.roadmap import RoadmapSwarm
from app.swarms.roadmap.feasibility import score_feasibility
from app.swarms.roadmap.idea import extract_idea
from app.swarms.roadmap.milestones import (
    Milestone,
    Phase,
    Timeline,
    critical_path,
    generate_milestones,
    topological_order,
)
from app.swarms.roadmap.models import StartupIdea


def _idea() -> StartupIdea:
    return extract_idea(
        "An affordable agriculture IoT device to help farmers solve irrigation, "
        "unlike existing tools."
    )


def test_milestone_count_and_phases():
    ms = generate_milestones(_idea())
    assert 5 <= len(ms) <= 15
    assert {m.id for m in ms}.__len__() == len(ms)  # unique ids
    phases = {m.phase for m in ms}
    assert Phase.IDEATION in phases and Phase.SCALE in phases  # spans the journey


def test_topological_order_respects_dependencies():
    ms = generate_milestones(_idea())
    order = topological_order(ms)
    pos = {mid: i for i, mid in enumerate(order)}
    for m in ms:
        for d in m.depends_on:
            assert pos[d] < pos[m.id]  # dependency comes first


def test_cycle_is_rejected():
    a = Milestone("a", Phase.IDEATION, "A", [], Timeline(1, 1, 1), ["b"])
    b = Milestone("b", Phase.IDEATION, "B", [], Timeline(1, 1, 1), ["a"])
    with pytest.raises(ValueError):
        topological_order([a, b])


def test_critical_path_is_the_longest():
    ms = generate_milestones(_idea())
    cp = critical_path(ms)
    assert cp[0] == "m1" and cp[-1] == "m9"
    by_id = {m.id: m for m in ms}
    cp_len = sum(by_id[i].timeline.realistic for i in cp)
    assert cp_len == 19  # m1+m2+m4+m6+m8+m9 = 1+2+4+2+4+6
    assert cp == ["m1", "m2", "m4", "m6", "m8", "m9"]


def test_feasibility_bounds_and_completeness():
    full = _idea()
    sparse = StartupIdea(raw_text="an app", problem="an app")
    fs, ss = score_feasibility(full), score_feasibility(sparse)
    assert 0 <= ss.score <= 100 and 0 <= fs.score <= 100
    assert fs.score > ss.score  # a fuller concept scores higher


def test_hardware_domain_lowers_technical():
    hw = score_feasibility(extract_idea("a hardware robotics device for farms"))
    soft = score_feasibility(extract_idea("a simple marketplace app for students"))
    assert hw.breakdown["technical"] < soft.breakdown["technical"]


def test_swarm_marks_critical_and_asks_clarifications():
    rm = RoadmapSwarm().generate("A device to help farmers")  # missing several elements
    crit = [m.id for m in rm.milestones if m.critical]
    assert crit == rm.critical_path
    assert rm.idea.domain == "agritech"
    assert len(rm.clarifications) >= 1  # asks about missing concept elements
