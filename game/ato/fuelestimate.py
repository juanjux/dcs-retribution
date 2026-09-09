"""What a flight plan is going to cost in fuel, erring high.

The pieces were already here: every aircraft that has been measured carries a
``FuelConsumption`` -- taxi, and pounds per nautical mile for climb, cruise and
combat -- and the flight plan already knows which rate applies to each leg and how
far the aircraft actually flies it (a racetrack charges its laps, not one crossing).
The mission generator walks exactly this to write each waypoint's ``min_fuel``. All
that was missing was showing the player the number before they fly it.

Deliberately pessimistic. The rates are averages over a profile nobody flies exactly,
the AI wanders, and a player who believes an optimistic figure finds out about it over
the sea, so the total carries a margin on top of the reserve the aircraft is supposed
to land with.
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

#: Added on top of taxi + route + reserve. The estimate is meant to be wrong in the
#: direction that costs a diversion rather than a splash.
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

    # Up to and including the landing point, the same slice the generator's min_fuel
    # walk uses. What follows a landing is the bullseye and the divert field, and the
    # bullseye can be hundreds of miles away.
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


#: Nominal still-air range on internal fuel, by what the airframe is. Calibrated on
#: the 24 aircraft somebody has actually measured, which come out between 447 nm (a
#: Growler) and 856 nm (a Tornado F3) -- so a fast jet is given the pessimistic end of
#: that spread, and the classes nobody measured are set by the same reasoning.
NOMINAL_RANGE_NM = {
    "helicopter": 250.0,
    "heavy": 4000.0,  # tankers, AWACS, transports: they exist to stay up
    "propeller": 500.0,
    "jet": 450.0,
}

#: Ratios from the measured set: climb runs 2.0-2.4x cruise and combat 1.2-2.2x.
#: The high end of each would compound with the pessimistic cruise above into an
#: estimate that calls every flight short, which is no more useful than a wrong one.
CLIMB_OVER_CRUISE = 2.4
COMBAT_OVER_CRUISE = 1.8

#: Taxi, and the reserve to land with as a share of internal fuel -- the measured set
#: reserves 1000 lb on a Viper and 2000 on a Hornet, both near a sixth of internal.
ASSUMED_TAXI_LB = 200
RESERVE_SHARE = 0.17
MINIMUM_RESERVE_LB = 400.0


#: An aircraft that can only do these is not a combat aircraft carrying fuel to fight
#: with, it is one whose whole job is staying up. Keyed on the tasking rather than on
#: size, because the Super Hornet tanker is a fighter by every physical measure and
#: carries its transferable fuel as "internal".
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
    """A consumption profile for an airframe nobody has measured.

    Only 24 of the ~300 aircraft carry measured figures, so without this the estimate
    would have nothing to say about almost every flight. Derived from the one number
    every airframe does have -- how much fuel it holds -- over a nominal range for its
    class, which is the crude version of "so many pounds per mile".
    """
    internal = aircraft.dcs_unit_type.fuel_max * KG_TO_LBS
    cruise = internal / NOMINAL_RANGE_NM[_airframe_class(aircraft)]
    return FuelConsumption(
        taxi=ASSUMED_TAXI_LB,
        climb=cruise * CLIMB_OVER_CRUISE,
        cruise=cruise,
        combat=cruise * COMBAT_OVER_CRUISE,
        min_safe=int(max(MINIMUM_RESERVE_LB, internal * RESERVE_SHARE)),
    )
