from __future__ import annotations

from datetime import timedelta
from typing import Type

from game.ato.flightplans.ibuilder import IBuilder
from game.ato.flightplans.patrolling import PatrollingFlightPlan, PatrollingLayout
from game.ato.flightplans.supportorbit import support_orbit_anchor
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.ato.flighttype import FlightType
from game.utils import Distance, Speed, knots, meters, nautical_miles


class AewcFlightPlan(PatrollingFlightPlan[PatrollingLayout]):
    @property
    def patrol_duration(self) -> timedelta:
        return self.flight.coalition.game.settings.desired_awacs_mission_duration

    @property
    def patrol_speed(self) -> Speed:
        altitude = self.layout.patrol_start.alt
        if self.flight.unit_type.preferred_patrol_speed(altitude) is not None:
            return self.flight.unit_type.preferred_patrol_speed(altitude)
        return knots(390)

    @property
    def engagement_distance(self) -> Distance:
        # TODO: Factor out a common base of the combat and non-combat race-tracks.
        # No harm in setting this, but we ought to clean up a bit.
        return meters(0)

    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder


class Builder(IBuilder[AewcFlightPlan, PatrollingLayout]):
    def layout(self) -> PatrollingLayout:
        racetrack_half_distance = nautical_miles(30).meters

        threat_buffer = nautical_miles(
            self.coalition.game.settings.aewc_threat_buffer_min_distance
        )

        # Anchor on the front line and stand off into friendly airspace, centered
        # on the fighting and parallel to the FLOT. See supportorbit for why this
        # replaced the old per-CP anchoring (which flung AI AWACS off-axis).
        base_center, orbit_heading = support_orbit_anchor(
            self.theater,
            self.coalition.player,
            self.threat_zones,
            self.package.target,
            threat_buffer,
        )

        # When multiple AWACS are planned, spread their orbits laterally along
        # the front so each covers a different section rather than stacking.
        # Orbits are spaced one full racetrack width (2 * half_distance) apart,
        # centered on the natural orbit point.
        all_awacs = sorted(
            [
                f
                for p in self.coalition.ato.packages
                for f in p.flights
                if f.flight_type is FlightType.AEWC
            ],
            key=lambda f: str(f.id),
        )
        n = len(all_awacs)
        try:
            idx = next(i for i, f in enumerate(all_awacs) if f is self.flight)
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

    def build(self, dump_debug_info: bool = False) -> AewcFlightPlan:
        return AewcFlightPlan(self.flight, self.layout())
