"""Whether a flight is going to need a tanker, decided before its plan exists.

The refuelling waypoint used to be added to every non-helicopter flight of any
faction that owned a tanker, whether the flight could reach its target and come
home twice over or not. Now that a flight's fuel can be estimated, the question can
be asked properly -- but it has to be asked while the plan is being built, so there
are no legs to measure yet. The package geometry is what there is: the flight goes
out through the join and the ingress, works the target, and comes back through the
split.
"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Any

from game.ato.fuelestimate import CLIMB_DISTANCE_NM, Leg, fuel_for_route
from game.utils import Distance, meters

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.ato.package import Package


#: The geometry is a floor: the real plan holds before the join, routes around
#: threats and flies its laps, so it comes out a few percent longer. Erring long here
#: is deliberate -- the waypoint is free and the tanker is not, so the cheap decision
#: has to be the eager one, or a tanker gets bought that nobody is sent to meet.
ROUTE_SLACK = 1.10


def can_carry_a_refuel_waypoint(flight: Flight) -> bool:
    """Whether this flight's plan has anywhere to put one.

    Only formation attacks and TARCAP do. A CAS or BARCAP flight short of fuel is a
    real problem, but buying it a tanker it can never be routed to meet is not the
    answer to it.
    """
    try:
        layout = flight.flight_plan.layout
    except Exception:
        return False
    return hasattr(layout, "refuel")


def planned_legs(
    flight: Flight,
    package: Package,
    cruise_altitude: Distance,
    combat_altitude: Distance,
    on_station: Distance = meters(0),
) -> list[Leg]:
    """The route the package geometry implies, itemised the way a plan would be.

    Out through the join and the ingress to the target, back through the split to
    wherever it lands. Charged like the real thing: the first stretch at the climb
    rate, the run in to the target at the combat rate, and everything else at cruise
    with the altitude correction for the band it will actually be flown at. A flat
    cruise rate at no altitude came out 20-35% cheap, which is the wrong direction --
    a flight told it has fuel to spare gets no tanker.

    ``on_station`` is the distance a patrolling flight flies in its laps. A TARCAP
    that holds for half an hour burns more there than on the way, and leaving it out
    meant a patrol was judged on about half the fuel it really needs.
    """
    waypoints = package.waypoints
    if waypoints is None:
        return []
    arrival = flight.arrival if flight.arrival is not None else flight.departure
    cruise_ft = cruise_altitude.feet
    combat_ft = combat_altitude.feet

    def nm(a: Any, b: Any) -> float:
        return meters(a.distance_to_point(b)).nautical_miles

    out = nm(flight.departure.position, waypoints.join) * ROUTE_SLACK
    climbing = min(CLIMB_DISTANCE_NM, out)
    legs = [
        Leg(climbing, cruise_ft, climb=True),
        Leg(out - climbing, cruise_ft),
        Leg(nm(waypoints.join, waypoints.ingress) * ROUTE_SLACK, cruise_ft),
        # The run in, at the combat rate and the combat band.
        Leg(
            nm(waypoints.ingress, package.target.position) * ROUTE_SLACK,
            combat_ft,
            attack=True,
        ),
        Leg(on_station.nautical_miles, combat_ft),
        Leg(nm(package.target.position, waypoints.split) * ROUTE_SLACK, combat_ft),
        Leg(nm(waypoints.split, arrival.position) * ROUTE_SLACK, cruise_ft),
    ]
    return [leg for leg in legs if leg.nautical_miles > 0]


def planned_route_nm(flight: Flight, package: Package) -> float:
    """How far the package geometry says the flight goes, laps included."""
    return sum(
        leg.nautical_miles
        for leg in planned_legs(flight, package, meters(0), meters(0))
    )


def needs_refuelling(
    flight: Flight,
    package: Package,
    settings: Any,
    cruise_altitude: Distance,
    combat_altitude: Distance,
    on_station: Distance = meters(0),
) -> bool:
    """Whether this flight should be given a tanker and a refuelling waypoint.

    A helicopter never is: it cannot use the boom, and the tanker's track is not
    where it flies. Nor is anything asked for when the campaign has switched the
    whole idea off, or when the faction has no tanker to send.
    """
    if not getattr(settings, "plan_refuelling_when_needed", True):
        return False
    if flight.is_helo:
        return False
    from game.ato.flighttype import FlightType

    if not flight.coalition.air_wing.can_auto_plan(FlightType.REFUELING):
        return False
    legs = planned_legs(flight, package, cruise_altitude, combat_altitude, on_station)
    if not legs:
        return False
    return not fuel_for_route(flight, legs).enough


def has_refuel_waypoint(flight: Flight) -> bool:
    """Whether this flight was already given somewhere to meet a tanker."""
    try:
        layout = flight.flight_plan.layout
    except Exception:
        # A plan that cannot answer yet is not a reason to send a tanker.
        logging.debug("No usable flight plan for %s", flight, exc_info=True)
        return False
    return getattr(layout, "refuel", None) is not None


def package_needs_tanker(package: Package, settings: Any) -> bool:
    """Whether anything in this package has been routed to meet a tanker.

    This READS the decision rather than repeating it. The waypoint was settled flight
    by flight while the layouts were built, from the package geometry; asking a second
    question here -- estimate_fuel over the finished plans -- is what let the two
    halves disagree, and they disagreed one way: the tanker was bought and the flight
    that paid for it was routed nowhere near it. One decision, made once, read twice.

    Called after the package's main flights have their plans, which is where the
    fulfiller decides whether to keep the tanker it proposed.
    """
    if not getattr(settings, "plan_refuelling_when_needed", True):
        return False
    return any(has_refuel_waypoint(flight) for flight in package.flights)
