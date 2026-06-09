from __future__ import annotations

from typing import Type

from game.ato.flighttype import FlightType
from game.utils import Heading, meters, nautical_miles
from .ibuilder import IBuilder
from .patrolling import PatrollingLayout
from .refuelingflightplan import RefuelingFlightPlan
from .waypointbuilder import WaypointBuilder


class TheaterRefuelingFlightPlan(RefuelingFlightPlan):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder


class Builder(IBuilder[TheaterRefuelingFlightPlan, PatrollingLayout]):
    def layout(self) -> PatrollingLayout:
        racetrack_half_distance = nautical_miles(20)

        location = self.package.target

        closest_boundary = self.threat_zones.closest_boundary(location.position)
        heading_to_threat_boundary = Heading.from_degrees(
            location.position.heading_between_point(closest_boundary)
        )
        distance_to_threat = meters(
            location.position.distance_to_point(closest_boundary)
        )

        threat_buffer = nautical_miles(
            self.coalition.game.settings.tanker_threat_buffer_min_distance
        )

        if self.threat_zones.threatened(location.position):
            # Target inside the threat zone — escape to safety.
            orbit_heading = heading_to_threat_boundary
            orbit_distance = distance_to_threat + threat_buffer
        elif self.coalition.player.is_blue:
            # Player-coalition tankers: orbit as far forward as the threat buffer
            # allows so strike packages don't have to fly far for fuel.  Clamp to
            # zero so we never end up behind the reference point.
            orbit_heading = heading_to_threat_boundary
            orbit_distance = max(meters(0), distance_to_threat - threat_buffer)
        else:
            # Enemy/AI tankers: orbit well inside friendly airspace, away from
            # the threat boundary.
            orbit_heading = heading_to_threat_boundary.opposite
            orbit_distance = threat_buffer

        base_center = location.position.point_from_heading(
            orbit_heading.degrees, orbit_distance.meters
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

        lateral_m = (idx - (n - 1) / 2) * (racetrack_half_distance * 2).meters
        if lateral_m >= 0:
            racetrack_center = base_center.point_from_heading(
                orbit_heading.right.degrees, lateral_m
            )
        else:
            racetrack_center = base_center.point_from_heading(
                orbit_heading.left.degrees, -lateral_m
            )

        racetrack_start = racetrack_center.point_from_heading(
            orbit_heading.right.degrees, racetrack_half_distance.meters
        )
        racetrack_end = racetrack_center.point_from_heading(
            orbit_heading.left.degrees, racetrack_half_distance.meters
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
