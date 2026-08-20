"""Timing inside a package.

Every flight carries its own offset from the package's time over target -- negative
means ahead of it, which is the whole point of an escort. The player sets it in the
Edit Flight dialog ("TOT Offset" plus an "Ahead of package" checkbox); the planner
could neither see it nor set it, so its escorts always arrived alongside the strikers.
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

from game.agent import planner, views


def _flight(offset_seconds: float | None = 0.0) -> Any:
    plan = SimpleNamespace()
    if offset_seconds is not None:
        plan.tot_offset = timedelta(seconds=offset_seconds)
    return SimpleNamespace(flight_plan=plan)


def test_an_escort_that_leads_reads_as_negative() -> None:
    assert views._tot_offset_minutes(_flight(-180)) == -3.0


def test_arriving_with_the_package_is_omitted() -> None:
    """Frugality: zero is the common case and the convention says absent means 0."""
    assert views._tot_offset_minutes(_flight(0)) is None


def test_a_flight_without_a_plan_does_not_break_the_turn() -> None:
    assert views._tot_offset_minutes(_flight(None)) is None


def test_setting_it_matches_the_dialog() -> None:
    """The dialog stores a signed timedelta; negative is 'ahead of package'."""
    flight = _flight(0)
    planner.apply_tot_offset(flight, -2.5)
    assert flight.flight_plan.tot_offset == timedelta(minutes=-2.5)
    assert views._tot_offset_minutes(flight) == -2.5

    planner.apply_tot_offset(flight, 4)
    assert flight.flight_plan.tot_offset == timedelta(minutes=4)


# --- when the flight has to start engines --------------------------------------


def _flight_with_startup(minutes_after_start: float) -> Any:
    from datetime import datetime

    start = datetime(2019, 12, 25, 11, 0)
    plan = SimpleNamespace(
        tot_offset=timedelta(0),
        startup_time=lambda: start + timedelta(minutes=minutes_after_start),
    )
    game = SimpleNamespace(conditions=SimpleNamespace(start_time=start))
    return SimpleNamespace(flight_plan=plan, coalition=SimpleNamespace(game=game))


def test_startup_is_reported_on_the_clock_the_planner_uses() -> None:
    """tot_minutes counts from mission start, so this must too."""
    assert views._startup_minutes(_flight_with_startup(23.4)) == 23


def test_a_flight_that_would_start_before_the_mission_reads_negative() -> None:
    """The signal that a TOT is unreachable, in the planner's own units."""
    assert views._startup_minutes(_flight_with_startup(-12)) == -12


def test_no_plan_no_startup() -> None:
    assert views._startup_minutes(SimpleNamespace()) is None
