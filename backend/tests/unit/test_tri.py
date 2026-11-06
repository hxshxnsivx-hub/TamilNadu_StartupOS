"""Truth tables for the Kleene three-valued logic (arena theme T04, F-A4-001)."""

from app.core.tri import Tri, Verdict, and_, not_, of, or_

T, F, U = Tri.TRUE, Tri.FALSE, Tri.UNKNOWN


def test_of_maps_bool():
    assert of(True) is T
    assert of(False) is F


def test_not_table():
    assert not_(T) is F
    assert not_(F) is T
    assert not_(U) is U


def test_and_table():
    # FALSE dominates; UNKNOWN only when no FALSE present
    assert and_([T, T]) is T
    assert and_([T, F]) is F
    assert and_([F, U]) is F  # a definite no, even with an unknown alongside
    assert and_([T, U]) is U
    assert and_([U, U]) is U
    assert and_([]) is T  # empty AND is vacuously true


def test_or_table():
    # TRUE dominates; UNKNOWN only when no TRUE present
    assert or_([F, F]) is F
    assert or_([T, F]) is T
    assert or_([T, U]) is T  # a definite yes, even with an unknown alongside
    assert or_([F, U]) is U
    assert or_([U, U]) is U
    assert or_([]) is F  # empty OR is vacuously false


def test_verdict_ok_is_true_only():
    assert Verdict(T).ok is True
    assert Verdict(F).ok is False
    assert Verdict(U).ok is False  # unknown is not eligible
