"""A tanker and a refuelling waypoint only for a package that needs the fuel.

Two things were wrong at once. The refuelling WAYPOINT went onto every
non-helicopter flight of any faction that owned a tanker, whether it could fly the
plan twice over or not. And the tanker FLIGHT the auto-planner proposed for Strike,
OCA and DEAD was pruned every time, because check_needed_escorts never set
EscortType.Refuel -- so the three settings that asked for it did nothing at all.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

import pytest

from game.ato.flightplans import refuelneed
from game.ato.flightplans.refuelneed import (
    needs_refuelling,
    package_needs_tanker,
    planned_route_nm,
)
from game.ato.fuelestimate import fuel_for_route
from game.dcs.aircrafttype import FuelConsumption

METRES_PER_NM = 1852.0


class _Point:
    def __init__(self, x: float) -> None:
        self.x, self.y = x, 0.0

    def distance_to_point(self, other: Any) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


def _flight(
    *, internal_lb: float = 10000.0, helo: bool = False, tankers: bool = True
) -> Any:
    consumption = FuelConsumption(
        taxi=200, climb=48, cruise=20, combat=36, min_safe=1500
    )
    member = SimpleNamespace(loadout=SimpleNamespace(pylons={}))
    return SimpleNamespace(
        unit_type=SimpleNamespace(fuel_consumption=consumption, helicopter=helo),
        roster=SimpleNamespace(members=[member]),
        fuel=internal_lb / 2.20462,  # kg, the unit Flight.fuel uses
        is_helo=helo,
        departure=SimpleNamespace(position=_Point(0)),
        arrival=SimpleNamespace(position=_Point(0)),
        coalition=SimpleNamespace(
            air_wing=SimpleNamespace(can_auto_plan=lambda _task: tankers),
            game=SimpleNamespace(settings=SimpleNamespace()),
        ),
    )


def _package(target_nm: float) -> Any:
    far = _Point(target_nm * METRES_PER_NM)
    return SimpleNamespace(
        target=SimpleNamespace(position=far),
        waypoints=SimpleNamespace(join=_Point(0), ingress=far, split=far),
        flights=[],
    )


def _settings(on: bool = True) -> Any:
    return SimpleNamespace(plan_refuelling_when_needed=on)


def test_the_route_is_out_and_back_not_a_straight_line() -> None:
    """Out through join and ingress, back through split to where it lands."""
    assert planned_route_nm(_flight(), _package(100)) == pytest.approx(200, rel=0.01)


def test_a_short_hop_does_not_need_a_tanker() -> None:
    assert fuel_for_route(_flight(), 50).enough


def test_a_long_route_asks_for_more_than_the_aircraft_holds() -> None:
    assert not fuel_for_route(_flight(), 900).enough


def test_the_waypoint_is_only_for_a_flight_that_runs_short() -> None:
    assert not needs_refuelling(_flight(), _package(60), _settings())
    assert needs_refuelling(_flight(), _package(400), _settings())


def test_the_campaign_can_switch_the_whole_idea_off() -> None:
    assert not needs_refuelling(_flight(), _package(400), _settings(on=False))


def test_a_helicopter_is_never_given_one() -> None:
    """It cannot use the boom, and the tanker's track is not where it flies."""
    assert not needs_refuelling(_flight(helo=True), _package(400), _settings())


def test_a_faction_with_no_tanker_is_not_offered_one() -> None:
    assert not needs_refuelling(_flight(tankers=False), _package(400), _settings())


def test_a_package_needs_a_tanker_when_any_flight_does(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The half that decides whether the tanker FLIGHT survives pruning."""
    thirsty, comfortable = _flight(), _flight()
    monkeypatch.setattr(
        refuelneed, "flight_is_short_of_fuel", lambda flight: flight is thirsty
    )
    package = _package(400)
    package.flights = [comfortable]
    assert not package_needs_tanker(package, _settings())
    package.flights = [comfortable, thirsty]
    assert package_needs_tanker(package, _settings())


def test_a_helicopter_does_not_make_the_package_ask_for_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(refuelneed, "flight_is_short_of_fuel", lambda _f: True)
    package = _package(400)
    package.flights = [_flight(helo=True)]
    assert not package_needs_tanker(package, _settings())


def test_a_flight_whose_plan_cannot_answer_is_not_a_reason_to_send_one() -> None:
    """Called before every plan is built, it must not scrub or over-plan."""
    flight = _flight()
    flight.flight_plan = None
    assert not refuelneed.flight_is_short_of_fuel(flight)
