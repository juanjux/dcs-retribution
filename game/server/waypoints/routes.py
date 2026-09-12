from uuid import UUID

from dcs.mapping import LatLng, Point
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import Response

from game import Game
from game.ato import Flight
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.server import GameContext
from game.server.leaflet import LeafletPoint
from game.server.waypoints.models import FlightWaypointJs
from game.sim import GameUpdateEvents
from game.utils import meters

router: APIRouter = APIRouter(prefix="/waypoints")


def waypoints_for_flight(flight: Flight) -> list[FlightWaypointJs]:
    departure = FlightWaypointJs.for_waypoint(
        FlightWaypoint(
            "TAKEOFF",
            FlightWaypointType.TAKEOFF,
            flight.departure.position,
            meters(0),
            "RADIO",
        ),
        flight,
        0,
    )
    return [departure] + [
        FlightWaypointJs.for_waypoint(w, flight, i)
        for i, w in enumerate(flight.flight_plan.waypoints, 1)
    ]


@router.get(
    "/{flight_id}",
    operation_id="list_all_waypoints_for_flight",
    response_model=list[FlightWaypointJs],
)
def all_waypoints_for_flight(
    flight_id: UUID, game: Game = Depends(GameContext.require)
) -> list[FlightWaypointJs]:
    return waypoints_for_flight(game.db.flights.get(flight_id))


@router.post(
    "/{flight_id}/{waypoint_idx}/position",
    operation_id="set_waypoint_position",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def set_position(
    flight_id: UUID,
    waypoint_idx: int,
    position: LeafletPoint,
    game: Game = Depends(GameContext.require),
) -> None:
    from game.server import EventStream

    flight = game.db.flights.get(flight_id)
    if waypoint_idx == 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    waypoint = flight.flight_plan.waypoints[waypoint_idx - 1]
    waypoint.position = Point.from_latlng(
        LatLng(position.lat, position.lng), game.theater.terrain
    )
    package_model = (
        GameContext.get_model()
        .ato_model_for(flight.blue)
        .find_matching_package_model(flight.package)
    )
    if package_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find PackageModel owning {flight}",
        )
    events = GameUpdateEvents()
    update_package_waypoints_if_primary_flight(waypoint, flight, events)
    package_model.update_tot()
    EventStream.put_nowait(events.update_flight(flight))


def formation_waypoint(
    flight: Flight, kind: FlightWaypointType
) -> FlightWaypoint | None:
    """A flight's join or split, whatever it happens to be labelled.

    A lone AI ship's two package waypoints read as NAV -- it has no formation to form --
    so matching on the label would miss them here, and would then drag the first nav
    point of every other flight in the package instead. The layout knows which waypoint
    is which; a custom flight plan has no layout to ask, and falls back to the label.
    """
    from game.ato.flightplans.formation import FormationLayout

    layout = flight.flight_plan.layout
    if isinstance(layout, FormationLayout):
        return layout.join if kind is FlightWaypointType.JOIN else layout.split
    for wpt in flight.flight_plan.iter_waypoints():
        if wpt.waypoint_type is kind:
            return wpt
    return None


def update_package_waypoints_if_primary_flight(
    waypoint: FlightWaypoint,
    flight: Flight,
    events: GameUpdateEvents,
) -> None:
    wpts = flight.package.waypoints
    if flight is flight.package.primary_flight and wpts:
        moved: FlightWaypointType | None = None
        if waypoint is formation_waypoint(flight, FlightWaypointType.JOIN):
            moved = FlightWaypointType.JOIN
            wpts.join = waypoint.position
        elif waypoint is formation_waypoint(flight, FlightWaypointType.SPLIT):
            moved = FlightWaypointType.SPLIT
            wpts.split = waypoint.position
        elif waypoint.waypoint_type is FlightWaypointType.REFUEL:
            wpts.refuel = waypoint.position
        elif "INGRESS" in waypoint.waypoint_type.name:
            wpts.ingress = waypoint.position
            wpts.initial = wpts.get_initial_point(
                waypoint.position, flight.package.target.position
            )
        else:
            return
        for f in flight.package.flights:
            if f is flight:
                continue
            counterpart = (
                formation_waypoint(f, moved)
                if moved is not None
                else _same_kind_of_waypoint(f, waypoint)
            )
            if counterpart is not None:
                counterpart.position = waypoint.position.new_in_same_map(
                    waypoint.position.x, waypoint.position.y
                )
                events.update_flight(f)


def _same_kind_of_waypoint(
    flight: Flight, waypoint: FlightWaypoint
) -> FlightWaypoint | None:
    for wpt in flight.flight_plan.iter_waypoints():
        if wpt.waypoint_type == waypoint.waypoint_type or (
            "INGRESS" in wpt.waypoint_type.name
            and "INGRESS" in waypoint.waypoint_type.name
        ):
            return wpt
    return None
