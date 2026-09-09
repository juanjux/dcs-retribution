"""Leg distances down the waypoint table, and what the route total leaves out.

Target points and the bullseye are in the list but not on the ground track: a strike
with six aimpoints a few hundred metres apart would otherwise pile six meaningless
hops into the total, and the bullseye is a map reference the flight never goes near.
They show 0 and contribute nothing, and the leg after one of them is measured from
the last waypoint actually flown.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from game.ato.flightwaypointtype import FlightWaypointType
from qt_ui.windows.mission.flight.waypoints.QFlightWaypointList import leg_distances

#: One nautical mile in metres, so the arithmetic below reads in the unit the column
#: is labelled with.
NM = 1852.0


def _waypoint(kind: FlightWaypointType, metres_from_origin: float) -> MagicMock:
    waypoint = MagicMock()
    waypoint.waypoint_type = kind
    waypoint.position.distance_to_point = lambda other: abs(
        other.x - metres_from_origin
    )
    waypoint.position.x = metres_from_origin
    return waypoint


def test_the_first_waypoint_has_no_leg() -> None:
    legs, total = leg_distances([_waypoint(FlightWaypointType.TAKEOFF, 0.0)])
    assert legs == [None]
    assert total == 0.0


def test_each_leg_is_measured_from_the_one_before() -> None:
    legs, total = leg_distances(
        [
            _waypoint(FlightWaypointType.TAKEOFF, 0.0),
            _waypoint(FlightWaypointType.NAV, 10 * NM),
            _waypoint(FlightWaypointType.LANDING_POINT, 25 * NM),
        ]
    )
    assert legs[1] is not None and round(legs[1]) == 10
    assert legs[2] is not None and round(legs[2]) == 15
    assert round(total) == 25


def test_a_target_neither_ends_a_leg_nor_starts_one() -> None:
    legs, total = leg_distances(
        [
            _waypoint(FlightWaypointType.TAKEOFF, 0.0),
            _waypoint(FlightWaypointType.INGRESS_STRIKE, 40 * NM),
            _waypoint(FlightWaypointType.TARGET_POINT, 41 * NM),
            _waypoint(FlightWaypointType.TARGET_POINT, 42 * NM),
            _waypoint(FlightWaypointType.EGRESS, 60 * NM),
        ]
    )
    assert legs[2] is None and legs[3] is None
    # Measured from the ingress, not from the last aimpoint.
    assert legs[4] is not None and round(legs[4]) == 20
    assert round(total) == 60


def test_the_bullseye_is_not_on_the_route() -> None:
    legs, total = leg_distances(
        [
            _waypoint(FlightWaypointType.TAKEOFF, 0.0),
            _waypoint(FlightWaypointType.LANDING_POINT, 30 * NM),
            _waypoint(FlightWaypointType.BULLSEYE, 500 * NM),
        ]
    )
    assert legs[2] is None
    assert round(total) == 30
