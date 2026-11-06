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
    assert m.pipeline_value == 0 and all(v == 0 for v in m.value_by_stage.values())
    assert all(v == 0 for v in m.stage_conversion.values())


def test_stage_conversion_infers_reached_stages():
    # one entry at due_diligence has necessarily passed the earlier stages
    m = pipeline_metrics([_entry("due_diligence")])
    assert m.stage_conversion["initial_contact"] == 100
    assert m.stage_conversion["due_diligence"] == 100
    assert m.stage_conversion["term_sheet"] == 0


def test_value_by_stage_splits_open_pipeline(F=1_000_000):
    # value is reported per the stage the deal sits in, not weighted by an
    # invented probability (F-A4-020)
    m = pipeline_metrics(
        [_entry("initial_contact", amount=F, iid="a"), _entry("negotiation", amount=2 * F, iid="b")]
    )
    assert m.pipeline_value == 3 * F
    assert m.value_by_stage["initial_contact"] == F
    assert m.value_by_stage["negotiation"] == 2 * F
    assert m.value_by_stage["term_sheet"] == 0
    assert not hasattr(m, "weighted_value")


def test_closed_entries_leave_the_pipeline_value():
    m = pipeline_metrics([_entry(WON, amount=5_000_000), _entry(LOST, amount=2_000_000)])
    assert m.pipeline_value == 0
    assert sum(m.value_by_stage.values()) == 0


def test_terminal_entries_without_history_do_not_inflate_conversion():
    # a lost deal with no trail reached only the first contact, not negotiation
    # (F-A4-020): [closed_lost no history, initial_contact] => 0% negotiation
    m = pipeline_metrics([_entry(LOST), _entry("initial_contact", iid="b")])
    assert m.stage_conversion["initial_contact"] == 100
    assert m.stage_conversion["negotiation"] == 0
    assert m.stage_conversion["due_diligence"] == 0
    # a won deal with no trail is credited up to the term sheet, not negotiation
    won = pipeline_metrics([_entry(WON)])
    assert won.stage_conversion["term_sheet"] == 100
    assert won.stage_conversion["negotiation"] == 0
    assert won.stage_conversion["closed_won"] == 100


def test_avg_days_parses_iso_datetime_stamps():
    # the frontend stamps Date.toISOString() ('...T..:..Z'); first-stage time
    # must survive the parse on Python 3.10 and 3.11 (F-A4-020)
    hist = [
        {"stage": "initial_contact", "at": "2026-01-01T09:30:00.000Z"},
        {"stage": "pitch_scheduled", "at": "2026-01-10T12:00:00+05:30"},
    ]
    m = pipeline_metrics([_entry("pitch_scheduled", history=hist)])
    assert m.avg_days_in_stage["initial_contact"] == 9.0


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
