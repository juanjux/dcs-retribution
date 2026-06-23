from __future__ import annotations

from typing import Type

from game.ato.flighttype import FlightType
from game.utils import nautical_miles
from .ibuilder import IBuilder
from .patrolling import PatrollingLayout
from .refuelingflightplan import RefuelingFlightPlan
from .supportorbit import support_orbit_anchor
from .waypointbuilder import WaypointBuilder


class TheaterRefuelingFlightPlan(RefuelingFlightPlan):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder


class Builder(IBuilder[TheaterRefuelingFlightPlan, PatrollingLayout]):
    def layout(self) -> PatrollingLayout:
        racetrack_half_distance = nautical_miles(20).meters

        threat_buffer = nautical_miles(
            self.coalition.game.settings.tanker_threat_buffer_min_distance
        )

        # Anchor on the front line and stand off into friendly airspace, centered
        # on the fighting and parallel to the FLOT. See supportorbit for why this
        # replaced the old per-CP anchoring (which could pin a tanker onto its
        # own departure runway).
        base_center, orbit_heading = support_orbit_anchor(
            self.theater,
            self.coalition.player,
            self.threat_zones,
            self.package.target,
            threat_buffer,
        )

        # Deconflict multiple tankers: spread orbits laterally along the front
        # so each covers a different slice of the strike corridor.
        all_tankers = sorted(
            [
                f
                for p in self.coalition.ato.packages
                for f in p.flights
                if f.flight_type is FlightType.REFUELING
            ],
            key=lambda f: str(f.id),
        )
        n = len(all_tankers)
        try:
            idx = next(i for i, f in enumerate(all_tankers) if f is self.flight)
        except StopIteration:
            idx = 0

        lateral_m = (idx - (n - 1) / 2) * (racetrack_half_distance * 2)
        if lateral_m >= 0:
            racetrack_center = base_center.point_from_heading(
                orbit_heading.right.degrees, lateral_m
            )
        else:
            racetrack_center = base_center.point_from_heading(
                orbit_heading.left.degrees, -lateral_m
            )

        racetrack_start = racetrack_center.point_from_heading(
            orbit_heading.right.degrees, racetrack_half_distance
        )

        racetrack_end = racetrack_center.point_from_heading(
            orbit_heading.left.degrees, racetrack_half_distance
        )

        builder = WaypointBuilder(self.flight)

        altitude = builder.get_patrol_altitude

        racetrack = builder.race_track(racetrack_start, racetrack_end, altitude)

        return PatrollingLayout(
            departure=builder.takeoff(self.flight.departure),
            nav_to=builder.nav_path(
                self.flight.departure.position, racetrack_start, altitude
            ),
            nav_from=builder.nav_path(
                racetrack_end, self.flight.arrival.position, altitude
            ),
            patrol_start=racetrack[0],
            patrol_end=racetrack[1],
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
        )

    def build(self, dump_debug_info: bool = False) -> TheaterRefuelingFlightPlan:
        return TheaterRefuelingFlightPlan(self.flight, self.layout())
