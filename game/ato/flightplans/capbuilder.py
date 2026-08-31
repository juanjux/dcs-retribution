from __future__ import annotations

import logging
import random
from abc import ABC
from typing import Any, TYPE_CHECKING, TypeVar

from dcs import Point
from shapely.geometry import Point as ShapelyPoint

from game.utils import Heading, meters, nautical_miles
from .flightplan import FlightPlan
from .patrolling import PatrollingLayout
from ..closestairfields import ObjectiveDistanceCache
from ..flightplans.ibuilder import IBuilder
from ..flightplans.planningerror import PlanningError

if TYPE_CHECKING:
    from game.theater import MissionTarget

FlightPlanT = TypeVar("FlightPlanT", bound=FlightPlan[Any])
LayoutT = TypeVar("LayoutT", bound=PatrollingLayout)

#: Shortest patrol route DCS will fly instead of deleting the flight on spawn.
#: The measured cliff is between 43 and 46 nm; this keeps a margin over it.
MIN_PATROL_ROUTE_LENGTH = nautical_miles(60)

#: Each step is exact unless moving the start also shortens the leg out to it.
_MAX_LENGTHENING_STEPS = 8


class CapBuilder(IBuilder[FlightPlanT, LayoutT], ABC):
    def cap_racetrack_for_objective(
        self, location: MissionTarget, barcap: bool
    ) -> tuple[Point, Point]:
        closest_cache = ObjectiveDistanceCache.get_closest_airfields(location)
        for airfield in closest_cache.operational_airfields:
            # If the mission is a BARCAP of an enemy airfield, find the *next*
            # closest enemy airfield.
            if airfield == self.package.target:
                continue
            if airfield.captured != self.is_player:
                closest_airfield = airfield
                break
        else:
            for airfield in closest_cache.closest_airfields:
                if airfield.captured != self.is_player:
                    closest_airfield = airfield
                    break
            else:
                raise PlanningError("Could not find any enemy airfields")

        heading = Heading.from_degrees(
            location.position.heading_between_point(closest_airfield.position)
        )

        position = ShapelyPoint(
            self.package.target.position.x, self.package.target.position.y
        )

        if barcap:
            # BARCAPs should remain far enough back from the enemy that their
            # commit range does not enter the enemy's threat zone. Include a 5nm
            # buffer.
            distance_to_no_fly = (
                meters(position.distance(self.threat_zones.all))
                - self.doctrine.cap_engagement_range
                - nautical_miles(5)
            )
            max_track_length = self.doctrine.cap_max_track_length
        else:
            # Other race tracks (TARCAPs, currently) just try to keep some
            # distance from the nearest enemy airbase, but since they are by
            # definition in enemy territory they can't avoid the threat zone
            # without being useless.
            min_distance_from_enemy = nautical_miles(
                self.coalition.game.settings.tarcap_threat_buffer_min_distance
            )
            distance_to_airfield = meters(
                closest_airfield.position.distance_to_point(
                    self.package.target.position
                )
            )
            distance_to_no_fly = distance_to_airfield - min_distance_from_enemy

            # TARCAPs fly short racetracks because they need to react faster.
            max_track_length = self.doctrine.cap_min_track_length + 0.3 * (
                self.doctrine.cap_max_track_length - self.doctrine.cap_min_track_length
            )

        min_cap_distance = min(
            self.doctrine.cap_min_distance_from_cp, distance_to_no_fly
        )
        max_cap_distance = min(
            self.doctrine.cap_max_distance_from_cp, distance_to_no_fly
        )

        end = location.position.point_from_heading(
            heading.degrees,
            random.randint(int(min_cap_distance.meters), int(max_cap_distance.meters)),
        )

        track_length = random.randint(
            int(self.doctrine.cap_min_track_length.meters),
            int(max_track_length.meters),
        )
        start = end.point_from_heading(heading.opposite.degrees, track_length)
        return self._lengthened_to_minimum(start, end, heading)

    def _lengthened_to_minimum(
        self, start: Point, end: Point, heading: Heading
    ) -> tuple[Point, Point]:
        """Push the far end of the track back until the route is long enough.

        DCS deletes an air-started flight the instant it spawns if its route is
        short enough, without flying a metre of it: the engine runs the last
        waypoint's tasks straight away, which for an air-started AI flight is the
        script that despawns it over its base. Measured on Kola by editing only
        the patrol coordinates of one generated mission, a total route of 35.8 or
        42.6 nm died and 46 nm and up flew normally, whatever the shape -- a
        triangle of three 20 nm legs was fine, and a route with the same short
        first leg as a dying one was fine once the rest was longer.

        A CAP guarding its own base is the easy way to hit this: the cold war
        doctrine can put the end of the track 8 nm from the field with a 12 nm
        track, for a 24 nm round trip, and the WWII doctrine is shorter still.

        The track is lengthened away from the enemy -- `end` is the threat-facing
        end, so the station itself does not move closer to them.
        """
        departure = self.flight.departure.position
        arrival = self.flight.arrival.position

        def route_length(track_start: Point) -> float:
            return (
                departure.distance_to_point(track_start)
                + track_start.distance_to_point(end)
                + end.distance_to_point(arrival)
            )

        # Moving the start back lengthens the track by the same amount, but it can
        # also shorten the leg out to it, so converge rather than assuming one step
        # is enough.
        for _ in range(_MAX_LENGTHENING_STEPS):
            shortfall = MIN_PATROL_ROUTE_LENGTH.meters - route_length(start)
            if shortfall <= 0:
                return start, end
            start = start.point_from_heading(heading.opposite.degrees, shortfall)
        logging.warning(
            "Could not lengthen the patrol route for %s past %.0f nm; DCS may "
            "delete the flight as it spawns.",
            self.flight,
            meters(route_length(start)).nautical_miles,
        )
        return start, end
