from __future__ import annotations

from pydantic import BaseModel

from game.ato import Flight, FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.server.leaflet import LeafletPoint

#: What the flight is there for. A target is not somewhere the aircraft flies to and
#: then leaves from -- it releases at it, from wherever the run takes it -- so drawing
#: the route through it says something about the plan that is not true, and on a strike
#: with several aim points it says it several times over.
TARGET_TYPES = {
    FlightWaypointType.TARGET_POINT,
    FlightWaypointType.TARGET_GROUP_LOC,
    FlightWaypointType.TARGET_SHIP,
}


def timing_info(flight: Flight, waypoint_idx: int) -> str:
    if waypoint_idx == 0:
        return f"Depart T+{flight.flight_plan.takeoff_time():%H:%M:%S}"

    waypoint = flight.flight_plan.waypoints[waypoint_idx - 1]
    prefix = "TOT"
    time = flight.flight_plan.tot_for_waypoint(waypoint)
    if time is None:
        prefix = "Depart"
        time = flight.flight_plan.depart_time_for_waypoint(waypoint)
    if time is None:
        return ""
    return f"{prefix} {time:%H:%M:%S}"


def leg_speed(flight: Flight, waypoint_idx: int) -> float:
    """Knots on the leg into this waypoint, or 0 where there is no leg.

    The plan owns this: a package flies its formation speed between the join and the
    split whatever each flight would do alone, so asking the aircraft would be wrong.
    """
    if waypoint_idx < 1:
        return 0.0
    waypoints = flight.flight_plan.waypoints
    if waypoint_idx > len(waypoints):
        return 0.0
    destination = waypoints[waypoint_idx - 1]
    if waypoint_idx == 1:
        origin = FlightWaypoint(
            "TAKEOFF",
            FlightWaypointType.TAKEOFF,
            flight.departure.position,
        )
    else:
        origin = waypoints[waypoint_idx - 2]
    try:
        return float(
            flight.flight_plan.speed_between_waypoints(origin, destination).knots
        )
    except Exception:
        # A custom plan can be asked about a pair it has no opinion on. Nothing to
        # show is better than a dialog that will not open.
        return 0.0


class FlightWaypointJs(BaseModel):
    name: str
    position: LeafletPoint
    altitude_ft: float
    altitude_reference: str
    is_movable: bool
    should_mark: bool
    include_in_path: bool
    timing: str
    #: Its place in the route, which is how every other endpoint addresses it.
    index: int
    #: Whether the flight can give it up without its plan being rebuilt. The map
    #: refuses the ones it cannot rather than quietly degrading the plan.
    can_delete: bool
    #: What the flight flies the leg into this waypoint at. Computed from the plan --
    #: there is no per-waypoint speed to set -- so the dialog shows it and no more.
    speed_kts: float
    #: Whether this is what the flight came for. Marked rather than drawn through.
    is_target: bool

    class Config:
        title = "Waypoint"

    @staticmethod
    def for_waypoint(
        waypoint: FlightWaypoint, flight: Flight, waypoint_idx: int
    ) -> FlightWaypointJs:
        # Target *points* are the exact location of a unit, whereas the target area is
        # only the center of the objective. Allow moving the latter since its exact
        # location isn't very important.
        #
        # Landing, and divert should be changed in the flight settings UI, takeoff
        # cannot be changed because that's where the plane is.
        #
        # Moving the bullseye reference only makes it wrong.
        is_movable = waypoint.waypoint_type not in {
            FlightWaypointType.BULLSEYE,
            FlightWaypointType.DIVERT,
            FlightWaypointType.LANDING_POINT,
            FlightWaypointType.TAKEOFF,
            FlightWaypointType.TARGET_POINT,
        }

        # We don't need a marker for the departure waypoint (and it's likely
        # coincident with the landing waypoint, so hard to see). We do want to draw
        # the path from it though.
        #
        # We also don't need the landing waypoint since we'll be drawing that path
        # as well, and it's clear what it is, and only obscured the CP icon.
        #
        # The divert waypoint also obscures the CP. We don't draw the path to it,
        # but it can be seen in the flight settings page, so it's not really a
        # problem to exclude it.
        #
        # Bullseye ought to be (but currently isn't) drawn *once* rather than as a
        # flight waypoint.
        should_mark = waypoint.waypoint_type not in {
            FlightWaypointType.BULLSEYE,
            FlightWaypointType.DIVERT,
            FlightWaypointType.LANDING_POINT,
            FlightWaypointType.TAKEOFF,
        }

        is_target = waypoint.waypoint_type in TARGET_TYPES

        include_in_path = not is_target and waypoint.waypoint_type not in {
            FlightWaypointType.BULLSEYE,
            FlightWaypointType.DIVERT,
        }

        return FlightWaypointJs(
            name=waypoint.display_name,
            position=waypoint.position.latlng(),
            altitude_ft=waypoint.alt.feet,
            altitude_reference=waypoint.alt_type,
            is_movable=is_movable,
            should_mark=should_mark,
            include_in_path=include_in_path,
            timing=timing_info(flight, waypoint_idx),
            index=waypoint_idx,
            can_delete=waypoint_idx > 0
            and flight.flight_plan.can_delete_waypoint(waypoint),
            speed_kts=leg_speed(flight, waypoint_idx),
            is_target=is_target,
        )
