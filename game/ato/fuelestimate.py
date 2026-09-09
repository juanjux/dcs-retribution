"""What a flight plan costs in fuel, erring high.

Taxi, each leg at its climb, cruise or combat rate, the landing reserve, and a margin
on top. An aircraft with no measured consumption falls back to a guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.dcs.aircrafttype import AircraftType, FuelConsumption
from game.utils import KG_TO_LBS, Mass, kgs, kph, pairwise, pounds

if TYPE_CHECKING:
    from game.ato.flight import Flight

#: On top of taxi + route + reserve, so the estimate errs towards a diversion rather
#: than towards a splash.
MARGIN = 1.10


@dataclass(frozen=True)
class FuelEstimate:
    """Pounds of fuel this flight plan asks for, and what the flight is carrying."""

    #: Taxi, the whole route and the landing reserve, with the margin applied.
    required: Mass
    #: What the flight is set to take off with.
    carried: Mass

    @property
    def enough(self) -> bool:
        return self.carried >= self.required


def estimate_fuel(flight: Flight) -> Optional[FuelEstimate]:
    """Never None in practice: an unmeasured airframe falls back to a guess."""
    consumption = flight.unit_type.fuel_consumption or assumed_consumption(
        flight.unit_type
    )
    plan = flight.flight_plan

    # Stop at the landing point: what follows it is the bullseye, hundreds of miles
    # away, and the divert field.
    waypoints = list(plan.waypoints)
    landing = None
    for index, waypoint in enumerate(waypoints):
        if waypoint.waypoint_type is FlightWaypointType.LANDING_POINT:
            landing = index
    if landing is not None:
        waypoints = waypoints[: landing + 1]

    # The plan's own fuel_consumption_between_points reads the aircraft's measured
    # figures and returns None when there are none, so the rate is picked here -- the
    # same rule it uses -- and only the DISTANCE comes from the plan, which is what
    # knows a racetrack flies its laps rather than one crossing.
    burn = 0.0
    for a, b in pairwise(waypoints):
        if a.waypoint_type is FlightWaypointType.TAKEOFF:
            rate = consumption.climb
        elif b in plan.combat_speed_waypoints:
            rate = consumption.combat
        else:
            rate = consumption.cruise
        burn += plan.fuel_burn_distance_between_points(a, b).nautical_miles * rate

    required = (consumption.taxi + burn + consumption.min_safe) * MARGIN
    return FuelEstimate(required=pounds(required), carried=kgs(flight.fuel))


#: Nominal still-air range on internal fuel, per class. The measured aircraft span
#: 447 to 856 nm, so a jet takes the pessimistic end.
NOMINAL_RANGE_NM = {
    "helicopter": 250.0,
    "heavy": 4000.0,  # tankers, AWACS, transports: they exist to stay up
    "propeller": 500.0,
    "jet": 450.0,
}

#: The measured set runs climb 2.0-2.4x cruise and combat 1.2-2.2x. Both at their
#: high end compound with the cruise above into an estimate that calls everything
#: short.
CLIMB_OVER_CRUISE = 2.4
COMBAT_OVER_CRUISE = 1.8

#: The measured set reserves 1000 lb on a Viper and 2000 on a Hornet, both near a
#: sixth of internal.
ASSUMED_TAXI_LB = 200
RESERVE_SHARE = 0.17
MINIMUM_RESERVE_LB = 400.0


#: An aircraft that can only do these exists to stay up. Keyed on tasking, not size:
#: the Super Hornet tanker is a fighter carrying its transferable fuel as "internal".
SUPPORT_ONLY_TASKS = frozenset(
    {
        FlightType.AEWC,
        FlightType.REFUELING,
        FlightType.RECOVERY,
        FlightType.TRANSPORT,
    }
)


def _airframe_class(aircraft: AircraftType) -> str:
    if aircraft.helicopter:
        return "helicopter"
    tasks = set(aircraft.iter_task_capabilities())
    if tasks and tasks <= SUPPORT_ONLY_TASKS:
        return "heavy"
    if aircraft.max_speed < kph(600):
        return "propeller"
    return "jet"


def assumed_consumption(aircraft: AircraftType) -> FuelConsumption:
    """A profile for an airframe nobody has measured, from its fuel capacity."""
    internal = aircraft.dcs_unit_type.fuel_max * KG_TO_LBS
    cruise = internal / NOMINAL_RANGE_NM[_airframe_class(aircraft)]
    return FuelConsumption(
        taxi=ASSUMED_TAXI_LB,
        climb=cruise * CLIMB_OVER_CRUISE,
        cruise=cruise,
        combat=cruise * COMBAT_OVER_CRUISE,
        min_safe=int(max(MINIMUM_RESERVE_LB, internal * RESERVE_SHARE)),
    )
