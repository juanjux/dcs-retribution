"""A single aircraft has no formation to form.

Calling its two package waypoints JOIN and SPLIT describes something that is not
happening, so for a lone AI ship they read as nav points -- and go back to being a join
and a split the moment a second aircraft is added.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from dcs import Point

from game.ato.flightplans.formation import FormationLayout
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.utils import feet

_NOWHERE = Point(0, 0, None)  # type: ignore[arg-type]


def _waypoint(name: str, kind: FlightWaypointType, pretty: str) -> FlightWaypoint:
    return FlightWaypoint(
        name,
        kind,
        _NOWHERE,
        feet(20000),
        description=f"{pretty} description",
        pretty_name=pretty,
    )


@dataclass
class _Layout(FormationLayout):
    def iter_waypoints(self) -> Iterator[FlightWaypoint]:
        yield from (self.join, self.split)


def _layout() -> _Layout:
    return _Layout(
        departure=_waypoint("TAKEOFF", FlightWaypointType.TAKEOFF, "Takeoff"),
        custom_waypoints=[],
        arrival=_waypoint("LANDING", FlightWaypointType.LANDING_POINT, "Landing"),
        divert=None,
        bullseye=_waypoint("BULLSEYE", FlightWaypointType.BULLSEYE, "Bullseye"),
        nav_to=[],
        nav_from=[],
        hold=None,
        join=_waypoint("JOIN", FlightWaypointType.JOIN, "Join"),
        split=_waypoint("SPLIT", FlightWaypointType.SPLIT, "Split"),
        refuel=None,
    )


def test_a_lone_ship_navigates_where_a_formation_would_join() -> None:
    layout = _layout()
    layout.label_formation_waypoints(lone_ship=True)
    assert layout.join.waypoint_type is FlightWaypointType.NAV
    assert layout.split.waypoint_type is FlightWaypointType.NAV
    assert layout.join.name == "NAV"
    assert layout.join.pretty_name == "Nav"


def test_adding_a_second_aircraft_gives_the_join_back() -> None:
    layout = _layout()
    layout.label_formation_waypoints(lone_ship=True)
    layout.label_formation_waypoints(lone_ship=False)
    assert layout.join.waypoint_type is FlightWaypointType.JOIN
    assert layout.split.waypoint_type is FlightWaypointType.SPLIT
    assert layout.join.pretty_name == "Join"
    assert layout.split.description == "Depart from package"


def test_the_waypoints_stay_put() -> None:
    """The label is all that moves: the package still meets and parts there, and every
    time in the plan is measured from these two points."""
    layout = _layout()
    join, split = layout.join, layout.split
    positions = (join.position, split.position, join.alt, split.alt)
    layout.label_formation_waypoints(lone_ship=True)
    assert layout.join is join
    assert layout.split is split
    assert (join.position, split.position, join.alt, split.alt) == positions


def test_a_name_the_player_typed_survives() -> None:
    layout = _layout()
    layout.join.custom_name = "PUSH"
    layout.label_formation_waypoints(lone_ship=True)
    assert layout.join.custom_name == "PUSH"
