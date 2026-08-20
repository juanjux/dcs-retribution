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
