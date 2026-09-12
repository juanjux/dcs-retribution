"""The package TOT must leave room for a flight that is asked to arrive AHEAD.

A flight is over the target at the package TOT plus its own offset, so a flight
three minutes ahead needs the package scheduled three minutes later than its own
transit demands. Without that, its plan is built backwards from a time it cannot
reach, its takeoff lands before the mission starts, and the clamp makes it arrive
LATE -- the exact opposite of what the offset asked for.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any

from game.ato.traveltime import TotEstimator

NOW = datetime.datetime(2020, 1, 1, 8, 0, 0)


def _flight(minutes_to_tot: int, offset_minutes: float) -> Any:
    plan = SimpleNamespace(
        tot_offset=datetime.timedelta(minutes=offset_minutes),
        minimum_duration_from_start_to_tot=lambda: datetime.timedelta(
            minutes=minutes_to_tot
        ),
    )
    return SimpleNamespace(flight_plan=plan)


def _package(*flights: Any) -> Any:
    return SimpleNamespace(flights=list(flights))


def test_flight_with_no_offset_is_unchanged() -> None:
    package = _package(_flight(30, 0))
    assert TotEstimator(package).earliest_tot(NOW) == NOW + datetime.timedelta(
        minutes=30
    )


def test_ahead_flight_pushes_the_package_later() -> None:
    """30 minutes of transit, wanted 3 minutes early -> package TOT at +33."""
    package = _package(_flight(30, -3))
    assert TotEstimator(package).earliest_tot(NOW) == NOW + datetime.timedelta(
        minutes=33
    )


def test_behind_flight_does_not_hold_the_package_back() -> None:
    """A flight arriving 3 minutes late has 3 more minutes to get there."""
    package = _package(_flight(30, 3))
    assert TotEstimator(package).earliest_tot(NOW) == NOW + datetime.timedelta(
        minutes=27
    )


def test_the_ahead_flight_can_set_the_package_time() -> None:
    """The escort is quicker but wants to be early; it, not the slowest flight
    without an offset, is what the package has to wait for."""
    strikers = _flight(30, 0)
    escort_ahead = _flight(29, -5)
    package = _package(strikers, escort_ahead)

    assert TotEstimator(package).earliest_tot(NOW) == NOW + datetime.timedelta(
        minutes=34
    )


def test_every_flight_can_reach_its_own_tot_at_the_earliest_package_tot() -> None:
    """The property that matters: nobody is given a takeoff before mission start."""
    flights = [_flight(30, 0), _flight(22, -3), _flight(35, 2)]
    package = _package(*flights)
    tot = TotEstimator(package).earliest_tot(NOW)

    for flight in flights:
        own_tot = tot + flight.flight_plan.tot_offset
        needed = flight.flight_plan.minimum_duration_from_start_to_tot()
        assert own_tot - needed >= NOW
