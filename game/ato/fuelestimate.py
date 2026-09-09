"""What a flight plan costs in fuel, erring high.

Taxi, each leg at its climb, cruise or combat rate, the landing reserve, and a margin
on top. An aircraft with no measured consumption falls back to a guess.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.data.fueltanks import loadout_fuel
from game.dcs.aircrafttype import AircraftType, FuelConsumption
from game.utils import KG_TO_LBS, Mass, kgs, kph, pairwise, pounds

if TYPE_CHECKING:
    from game.ato.flight import Flight

#: On top of taxi + route + reserve, so the estimate errs towards a diversion rather
#: than towards a splash.
MARGIN = 1.10

#: The legs actually flown in combat. The plan's own combat_speed_waypoints also
#: includes the join and the split, which are package-speed cruise.
ATTACK_WAYPOINTS = frozenset(
    {
        FlightWaypointType.TARGET_POINT,
        FlightWaypointType.TARGET_GROUP_LOC,
        FlightWaypointType.TARGET_SHIP,
    }
)

#: Altitude the measured cruise figures correspond to. A jet's fuel per mile falls as
#: it climbs, and a flat rate meant that raising a flight's cruise band changed nothing.
REFERENCE_ALTITUDE_FT = 25000.0

#: Bounds on that correction. A jet is not four times as thirsty on the deck as it is
#: in the thirties, and above the tropopause the gain stops.
MIN_ALTITUDE_FACTOR = 0.7
MAX_ALTITUDE_FACTOR = 2.0


def _density_ratio(altitude_ft: float) -> float:
    """ISA density over sea-level density, flat above the tropopause."""
    troposphere = min(max(altitude_ft, 0.0), 36089.0)
    ratio = (1.0 - 6.87535e-6 * troposphere) ** 4.2559
    if altitude_ft <= 36089.0:
        return ratio
    # Isothermal above it: density falls exponentially with a 20,806 ft scale height.
    return ratio * math.exp(-(altitude_ft - 36089.0) / 20806.0)


def altitude_factor(altitude_ft: float, helicopter: bool = False) -> float:
    """How much a leg's fuel per mile changes with the height it is flown at.

    Fuel per mile at constant Mach goes roughly with the square root of the density,
    so a jet on the deck burns half again what it does in the twenties. A helicopter
    does not cruise high enough for this to say anything, so it is left alone.
    """
    if helicopter:
        return 1.0
    here = math.sqrt(_density_ratio(altitude_ft))
    reference = math.sqrt(_density_ratio(REFERENCE_ALTITUDE_FT))
    return min(MAX_ALTITUDE_FACTOR, max(MIN_ALTITUDE_FACTOR, here / reference))


@dataclass(frozen=True)
class FuelEstimate:
    """Pounds of fuel this flight plan asks for, and what the flight is carrying."""

    #: Taxi, the whole route and the landing reserve, with the margin applied.
    required: Mass
    #: What the flight takes off with: the internal quantity plus its drop tanks.
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

    # The rate is picked here rather than through the plan's own
    # fuel_consumption_between_points, which returns None for an unmeasured airframe.
    # Only the DISTANCE comes from the plan, which is what knows a racetrack flies its
    # laps rather than one crossing.
    helicopter = flight.unit_type.helicopter
    burn = 0.0
    for a, b in pairwise(waypoints):
        if a.waypoint_type is FlightWaypointType.TAKEOFF:
            # Off the deck and climbing, so no altitude correction: the climb rate
            # already covers the whole climb.
            burn += (
                plan.fuel_burn_distance_between_points(a, b).nautical_miles
                * consumption.climb
            )
            continue
        # Combat rate for the attack itself. The plan also flags the join and the
        # split, which are flown at the package's cruise speed rather than in
        # combat -- charging those at the combat rate put a strike's egress leg,
        # eighty miles of it, at over twice the right figure.
        rate = (
            consumption.combat
            if b.waypoint_type in ATTACK_WAYPOINTS
            else consumption.cruise
        )
        altitude = (a.alt.feet + b.alt.feet) / 2
        burn += (
            plan.fuel_burn_distance_between_points(a, b).nautical_miles
            * rate
            * altitude_factor(altitude, helicopter)
        )

    required = (consumption.taxi + burn + consumption.min_safe) * MARGIN
    # Internal plus the drop tanks. Reading the internal figure alone called a
    # tanked-up strike short of fuel it was carrying on the pylons.
    external = loadout_fuel(flight.roster.members[0].loadout)
    return FuelEstimate(
        required=pounds(required), carried=kgs(flight.fuel + external.kgs)
    )


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
