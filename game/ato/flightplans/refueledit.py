"""Re-deciding the refuelling waypoint after the player has edited a flight.

The planner decides this once, while it builds the plan, from the plan it is building.
That is the right moment for a flight nobody touches, but it is the only moment: take
the drop tanks off, or take the route down to eight thousand feet, and nothing asks the
question again. The flight is short of fuel and the plan still says it is fine.

So the flight editor asks again on the way out, the same way it already asks whether the
ingress point should move when the stand-off weapons changed. The measure is
:func:`estimate_fuel`, which walks the route the flight actually has rather than the one
the planner would have built, so it sees the edits.

Nothing here changes a plan on its own -- it reports a verdict, and the dialog asks.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

from game.ato.fuelestimate import estimate_fuel
from .refuelneed import can_carry_a_refuel_waypoint, has_refuel_waypoint
from .waypointbuilder import WaypointBuilder

if TYPE_CHECKING:
    from ..flight import Flight


#: How much fuel to spare before offering to take the waypoint back off. A flight that
#: is barely making it is one bad vector from not making it, and being sent to a tanker
#: it turns out not to need costs it a few minutes; being sent home with the tanker
#: removed costs it the aircraft. So the two thresholds are deliberately not the same
#: number, and nothing is offered in the band between them.
COMFORTABLE_MARGIN = 1.15


class RefuelVerdict(Enum):
    """What the edited flight now says about meeting a tanker."""

    #: It is short of fuel and has nowhere to take any on.
    SHOULD_ADD = auto()
    #: It is carrying comfortably more than the route asks for and still has one.
    SHOULD_REMOVE = auto()
    #: Leave it alone.
    NOTHING_TO_DO = auto()


def refuel_verdict(flight: Flight) -> RefuelVerdict:
    """Whether the flight as the player left it wants its waypoint added or removed."""
    if not _could_meet_a_tanker(flight):
        return RefuelVerdict.NOTHING_TO_DO

    estimate = estimate_fuel(flight)
    if estimate is None:
        return RefuelVerdict.NOTHING_TO_DO

    if has_refuel_waypoint(flight):
        # The estimate does not model taking fuel on, so a flight that has a tanker to
        # meet is *expected* to read short. Only a comfortable surplus means the
        # detour has stopped being worth flying.
        if estimate.carried.pounds >= estimate.required.pounds * COMFORTABLE_MARGIN:
            return RefuelVerdict.SHOULD_REMOVE
        return RefuelVerdict.NOTHING_TO_DO

    if not estimate.enough:
        return RefuelVerdict.SHOULD_ADD
    return RefuelVerdict.NOTHING_TO_DO


def _could_meet_a_tanker(flight: Flight) -> bool:
    """Whether there is any point asking the question at all."""
    from game.ato.flighttype import FlightType

    if flight.is_helo:
        return False
    if not can_carry_a_refuel_waypoint(flight):
        return False
    if not flight.coalition.air_wing.can_auto_plan(FlightType.REFUELING):
        return False
    return flight.package.refuel_point is not None


def add_refuel_waypoint(flight: Flight) -> bool:
    """Put the waypoint in without rebuilding the plan.

    Rebuilding is what the player is trying to avoid: it would throw away the very
    edits that made the flight short. The layout has a slot for this waypoint and
    yields it in the right place -- after the target, or after the last lap -- so
    filling the slot is the whole change.
    """
    point = flight.package.refuel_point
    if point is None:
        return False
    try:
        layout = flight.flight_plan.layout
    except Exception:
        logging.debug("No usable flight plan for %s", flight, exc_info=True)
        return False
    if not hasattr(layout, "refuel"):
        return False
    layout.refuel = WaypointBuilder(flight).refuel(point)
    return True


def remove_refuel_waypoint(flight: Flight) -> bool:
    """Take it back off, the same way deleting it from the route table does."""
    try:
        layout = flight.flight_plan.layout
    except Exception:
        logging.debug("No usable flight plan for %s", flight, exc_info=True)
        return False
    existing = getattr(layout, "refuel", None)
    if existing is None:
        return False
    # Through delete_waypoint rather than by assignment: that is the path the route
    # table uses, and a waypoint the layout still holds a reference to is what breaks
    # mission generation.
    return bool(layout.delete_waypoint(existing))


def planned_tanker_name(flight: Flight) -> Optional[str]:
    """A tanker this flight could actually reach, or None if none is flying.

    The waypoint on its own is not a promise of fuel: the AI goes looking for a tanker
    of its own coalition and, if the turn has none in the air, finds nothing. Worth
    saying out loud when we offer to add one.
    """
    from game.ato.flighttype import FlightType

    for package in flight.coalition.ato.packages:
        for other in package.flights:
            if other.flight_type is FlightType.REFUELING:
                return str(other.callsign or other.unit_type)
    return None
