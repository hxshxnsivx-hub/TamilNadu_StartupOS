"""The model circuit breaker."""

from app.services.breaker import Breaker


def test_three_failures_in_a_minute_open_it_for_five_minutes():
    b = Breaker("t")
    b.fail(now=0)
    b.fail(now=10)
    assert b.allow(now=11)
    b.fail(now=20)
    assert not b.allow(now=21) and not b.allow(now=319) and b.allow(now=321)


def test_old_failures_fall_out_of_the_window():
    b = Breaker("t")
    b.fail(now=0)
    b.fail(now=10)
    b.fail(now=100)  # the first two are over a minute old
    assert b.allow(now=101)


def test_success_closes_it():
    b = Breaker("t")
    for t in (0, 1, 2):
        b.fail(now=t)
    b.succeed()
    assert b.allow(now=3) and b.state == "closed"
