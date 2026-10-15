"""Unit tests for the funding pipeline stage machine, board and metrics."""

import pytest
from app.funding.pipeline import (
    LOST,
    WON,
    PipelineEntry,
    advance,
    can_advance,
    kanban,
    next_stages,
    pipeline_metrics,
)


def _entry(stage="initial_contact", amount=0, history=None, iid="inv1"):
    return PipelineEntry(iid, f"{iid} name", stage, amount, history or [])


# --- transitions ---------------------------------------------------------


def test_forward_one_step_is_allowed():
    ok, _ = can_advance("initial_contact", "pitch_scheduled")
    assert ok


def test_cannot_skip_stages():
    ok, reason = can_advance("initial_contact", "due_diligence")
    assert not ok
    assert "skip" in reason.lower()


def test_cannot_move_backwards():
    ok, reason = can_advance("due_diligence", "pitch_scheduled")
    assert not ok
    assert "forward" in reason.lower()


def test_lost_is_reachable_from_any_open_stage():
    for stage in ("initial_contact", "pitch_delivered", "negotiation"):
        assert can_advance(stage, LOST)[0]


def test_won_requires_real_commitment():
    assert can_advance("negotiation", WON)[0]
    assert can_advance("term_sheet", WON)[0]
    ok, reason = can_advance("initial_contact", WON)
    assert not ok
    assert "term sheet" in reason.lower()


def test_terminal_stages_are_final():
    for stage in (WON, LOST):
        ok, reason = can_advance(stage, "negotiation")
        assert not ok
        assert "final" in reason.lower()


def test_advance_appends_history_and_seeds_origin():
    moved = advance(_entry(), "pitch_scheduled", at="2026-02-01")
    assert moved.stage == "pitch_scheduled"
    # history seeded with the origin stage, then the new one
    assert [h["stage"] for h in moved.history] == ["initial_contact", "pitch_scheduled"]
    assert moved.history[-1]["at"] == "2026-02-01"


def test_advance_rejects_invalid_move():
    with pytest.raises(ValueError):
        advance(_entry(), "closed_won")


def test_next_stages_offers_only_legal_moves():
    assert next_stages("initial_contact") == ["pitch_scheduled", LOST]
    assert next_stages(WON) == []


# --- metrics -------------------------------------------------------------


def test_metrics_counts_and_win_rate():
    entries = [
        _entry("closed_won", iid="a"),
        _entry("closed_lost", iid="b"),
        _entry("due_diligence", iid="c"),
    ]
    m = pipeline_metrics(entries)
    assert m.total == 3
    assert m.won == 1 and m.lost == 1
    assert m.open_count == 1
    assert m.win_rate == 50  # 1 of 2 concluded


def test_metrics_empty_pipeline_is_safe():
    m = pipeline_metrics([])
    assert m.total == 0 and m.win_rate == 0
    assert m.pipeline_value == 0 and m.weighted_value == 0
    assert all(v == 0 for v in m.stage_conversion.values())


def test_stage_conversion_infers_reached_stages():
    # one entry at due_diligence has necessarily passed the earlier stages
    m = pipeline_metrics([_entry("due_diligence")])
    assert m.stage_conversion["initial_contact"] == 100
    assert m.stage_conversion["due_diligence"] == 100
    assert m.stage_conversion["term_sheet"] == 0


def test_weighted_value_discounts_early_stages():
    early = pipeline_metrics([_entry("initial_contact", amount=1_000_000)])
    late = pipeline_metrics([_entry("negotiation", amount=1_000_000)])
    assert early.pipeline_value == late.pipeline_value == 1_000_000
    assert early.weighted_value == 50_000  # 5%
    assert late.weighted_value == 800_000  # 80%
    assert early.weighted_value < late.weighted_value


def test_closed_entries_leave_the_pipeline_value():
    m = pipeline_metrics([_entry(WON, amount=5_000_000), _entry(LOST, amount=2_000_000)])
    assert m.pipeline_value == 0
    assert m.weighted_value == 0


def test_avg_days_in_stage_from_history():
    hist = [
        {"stage": "initial_contact", "at": "2026-01-01"},
        {"stage": "pitch_scheduled", "at": "2026-01-11"},  # 10 days in initial_contact
        {"stage": "pitch_delivered", "at": "2026-01-15"},  # 4 days in pitch_scheduled
    ]
    m = pipeline_metrics([_entry("pitch_delivered", history=hist)])
    assert m.avg_days_in_stage["initial_contact"] == 10.0
    assert m.avg_days_in_stage["pitch_scheduled"] == 4.0
    assert m.avg_days_in_stage["pitch_delivered"] == 0.0  # still in it


def test_malformed_dates_do_not_break_metrics():
    hist = [
        {"stage": "initial_contact", "at": "not-a-date"},
        {"stage": "pitch_scheduled", "at": "2026-01-11"},
    ]
    m = pipeline_metrics([_entry("pitch_scheduled", history=hist)])
    assert m.avg_days_in_stage["initial_contact"] == 0.0


# --- board ---------------------------------------------------------------


def test_kanban_groups_by_stage_in_order():
    board = kanban([_entry("negotiation", 100, iid="a"), _entry("negotiation", 50, iid="b")])
    by_stage = {c["stage"]: c for c in board}
    assert by_stage["negotiation"]["count"] == 2
    assert by_stage["negotiation"]["value"] == 150
    assert by_stage["initial_contact"]["count"] == 0
    assert [c["stage"] for c in board][0] == "initial_contact"


def test_from_dict_rejects_unknown_stage():
    with pytest.raises(ValueError):
        PipelineEntry.from_dict({"investor_id": "x", "stage": "coffee_chat"})
