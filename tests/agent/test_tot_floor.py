"""A package cannot be over its target before its flights can get there.

GeneraLLM set a DEAD package to TOT +5 min from a base ~29 minutes away. The API took
it, `validate` returned within_window:true, and the mission generator turned the
resulting negative push time into a hold release scheduled for -865 s. Nothing in the
loop said no.

The floor is the slowest flight's ``minimum_duration_from_start_to_tot`` — startup,
taxi, takeoff and transit.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from game.agent import planner

_NOW = datetime(2030, 6, 2, 9, 0, 0)


def _package(*minutes: float, target: str = "FAWN") -> Any:
    flights = [
        SimpleNamespace(
            flight_plan=SimpleNamespace(
                minimum_duration_from_start_to_tot=lambda m=m: timedelta(minutes=m)
            ),
            departure=SimpleNamespace(name="Ramat David"),
        )
        for m in minutes
    ]
    return SimpleNamespace(
        flights=flights, target=SimpleNamespace(name=target), time_over_target=None
    )


def test_the_floor_is_the_slowest_flight() -> None:
    floor = planner.earliest_tot_minutes(_package(12.0, 28.7, 9.0), _NOW)
    assert floor == (29, "Ramat David")


def test_a_package_with_nothing_measurable_has_no_floor() -> None:
    assert planner.earliest_tot_minutes(_package(), _NOW) is None


def test_an_unreachable_tot_is_raised_to_the_floor() -> None:
    pkg = _package(28.7)
    spec = SimpleNamespace(tot_minutes=5)
    planner._apply_tot(pkg, spec, _NOW)
    assert pkg.time_over_target == _NOW + timedelta(minutes=29)


def test_a_reachable_tot_is_left_alone() -> None:
    pkg = _package(28.7)
    planner._apply_tot(pkg, SimpleNamespace(tot_minutes=45), _NOW)
    assert pkg.time_over_target == _NOW + timedelta(minutes=45)


def test_the_clamp_is_reported_not_silent() -> None:
    """The planner must be able to tell that it did not get the TOT it asked for."""
    game: Any = SimpleNamespace()
    pkg = _package(28.7)

    class FakeAto:
        packages = [pkg]

    def fake_coalition(_game: Any, _side: str) -> Any:
        return SimpleNamespace(ato=FakeAto())

    original = planner.views.coalition_for_side
    planner.views.coalition_for_side = fake_coalition  # type: ignore[assignment]
    try:
        game.conditions = SimpleNamespace(start_time=_NOW)
        result = planner.set_package_tot(game, "red", 0, 5)
    finally:
        planner.views.coalition_for_side = original
    assert result.ok
    assert "unreachable" in (result.detail or "")
    assert "+29" in (result.detail or "")
    assert "Ramat David" in (result.detail or "")
    assert pkg.time_over_target == _NOW + timedelta(minutes=29)
