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

from game.ato.fuelestimate import fuel_for_route
from game.utils import meters

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.ato.package import Package


def planned_route_nm(flight: Flight, package: Package) -> float:
    """The route the package geometry implies, in nautical miles.

    Out through the join and the ingress to the target, back through the split to
    wherever the flight lands. Closer to the truth than a straight line there and
    back, and available before a single waypoint has been built.
    """
    waypoints = package.waypoints
    if waypoints is None:
        return 0.0
    arrival = flight.arrival if flight.arrival is not None else flight.departure
    legs = [
        flight.departure.position,
        waypoints.join,
        waypoints.ingress,
        package.target.position,
        waypoints.split,
        arrival.position,
    ]
    total = 0.0
    for previous, current in zip(legs, legs[1:]):
        total += meters(previous.distance_to_point(current)).nautical_miles
    return total


def needs_refuelling(flight: Flight, package: Package, settings: Any) -> bool:
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
    distance = planned_route_nm(flight, package)
    if distance <= 0:
        return False
    estimate = fuel_for_route(flight, distance)
    return not estimate.enough


def flight_is_short_of_fuel(flight: Flight) -> bool:
    """The same question once the flight HAS a plan, which is more exact.

    estimate_fuel walks the real legs at their real rates and altitudes, so once the
    package's main flights are planned there is no need to guess from the geometry.
    """
    from game.ato.fuelestimate import estimate_fuel

    try:
        estimate = estimate_fuel(flight)
    except Exception:
        # A plan that cannot answer yet is not a reason to scrub the package or to
        # send a tanker it may not need. Say no and let the waypoint decide later.
        logging.debug("Could not estimate fuel for %s", flight, exc_info=True)
        return False
    return estimate is not None and not estimate.enough


def package_needs_tanker(package: Package, settings: Any) -> bool:
    """Whether anything in this package cannot make the plan on what it carries.

    Asked after the package's main flights have their plans, which is when the
    fulfiller decides whether to keep the tanker it proposed.
    """
    if not getattr(settings, "plan_refuelling_when_needed", True):
        return False
    for flight in package.flights:
        if flight.is_helo:
            continue
        if flight_is_short_of_fuel(flight):
            return True
    return False
