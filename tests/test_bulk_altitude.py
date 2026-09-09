"""Which waypoints "Apply to all" is allowed to move.

By type. Skipping AGL points as well froze whole flight plans: a helicopter cruises
AGL, so an Apache had nothing left to set at all.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from game.ato.flightwaypointtype import FlightWaypointType
from qt_ui.windows.mission.flight.waypoints.QFlightWaypointTab import QFlightWaypointTab


class _Tab:
    """The rule reads one class attribute, so it needs no widget behind it."""

    def _is_bulk_editable(self, waypoint: Any) -> bool:
        stub = SimpleNamespace(
            BULK_ALTITUDE_SKIP_TYPES=QFlightWaypointTab.BULK_ALTITUDE_SKIP_TYPES
        )
        return QFlightWaypointTab._is_bulk_editable(stub, waypoint)  # type: ignore[arg-type]


def _tab() -> _Tab:
    return _Tab()


def _waypoint(kind: FlightWaypointType, alt_type: str) -> MagicMock:
    waypoint = MagicMock()
    waypoint.waypoint_type = kind
    waypoint.alt_type = alt_type
    return waypoint


def test_an_en_route_point_moves_whatever_it_is_referenced_to() -> None:
    tab = _tab()
    for alt_type in ("BARO", "RADIO"):
        assert tab._is_bulk_editable(_waypoint(FlightWaypointType.JOIN, alt_type))
        assert tab._is_bulk_editable(_waypoint(FlightWaypointType.SPLIT, alt_type))
        assert tab._is_bulk_editable(_waypoint(FlightWaypointType.NAV, alt_type))


def test_a_helicopter_plan_is_not_frozen() -> None:
    """Every en-route point of one is AGL, and every one of them must be settable."""
    tab = _tab()
    helo_route = [
        _waypoint(FlightWaypointType.JOIN, "RADIO"),
        _waypoint(FlightWaypointType.INGRESS_ESCORT, "RADIO"),
        _waypoint(FlightWaypointType.CUSTOM, "RADIO"),
        _waypoint(FlightWaypointType.SPLIT, "RADIO"),
    ]
    assert all(tab._is_bulk_editable(w) for w in helo_route)


def test_the_points_tied_to_the_ground_stay_put() -> None:
    tab = _tab()
    for kind in (
        FlightWaypointType.TAKEOFF,
        FlightWaypointType.LANDING_POINT,
        FlightWaypointType.DESCENT_POINT,
        FlightWaypointType.DIVERT,
        FlightWaypointType.TARGET_POINT,
        FlightWaypointType.TARGET_GROUP_LOC,
        FlightWaypointType.PICKUP_ZONE,
        FlightWaypointType.DROPOFF_ZONE,
        FlightWaypointType.REFUEL,
        FlightWaypointType.BULLSEYE,
    ):
        assert not tab._is_bulk_editable(_waypoint(kind, "BARO"))
        assert not tab._is_bulk_editable(_waypoint(kind, "RADIO"))
