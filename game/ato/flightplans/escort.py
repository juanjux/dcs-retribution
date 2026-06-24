from __future__ import annotations

from datetime import datetime
from typing import Optional, Type, TYPE_CHECKING

from dcs.mapping import Point

from .airassault import AirAssaultLayout
from .airlift import AirliftLayout
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .patrolling import PatrollingLayout
from .waypointbuilder import WaypointBuilder
from .. import FlightType
from ..packagewaypoints import PackageWaypoints
from ...utils import feet

if TYPE_CHECKING:
    from ..flight import Flight


class EscortFlightPlan(FormationAttackFlightPlan):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    @property
    def split_time(self) -> datetime:
        # Avoid infinite recursion when this escort flight is itself the primary flight
        # This can happen when only escort flights remain in a package
        if (
            self.package.primary_flight
            and self.package.primary_flight != self.flight
            and self.package.primary_flight.flight_plan
        ):
            return self.package.primary_flight.flight_plan.mission_departure_time
        else:
            return super().split_time


class EwarFlightPlan(EscortFlightPlan):
    """Escort flight plan for dedicated EW jamming (FlightType.EWAR).

    Identical to the escort plan except the near-target hold is replaced with a
    threat-aware JAMMING HOLD at the ingress standoff (see EwarBuilder), so the
    jammer stays with the package instead of orbiting inside the target's threat ring.
    """

    @staticmethod
    def builder_type() -> Type[Builder]:
        return EwarBuilder


class Builder(FormationAttackBuilder[EscortFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        non_formation_escort = False
        if self.package.waypoints is None:
            self.package.waypoints = PackageWaypoints.create(
                self.package, self.coalition, dump_debug_info=False
            )
            if self.package.primary_flight:
                departure = self.package.primary_flight.flight_plan.layout.departure
                self.package.waypoints.join = departure.position.lerp(
                    self.package.target.position, 0.2
                )
                non_formation_escort = True

        builder = WaypointBuilder(self.flight)
        ingress, target = builder.escort(
            self.package.waypoints.ingress, self.package.target
        )
        if non_formation_escort:
            target.position = self.package.waypoints.join
        ingress.only_for_player = True
        target.only_for_player = True
        hold = None
        if not (self.flight.is_helo or non_formation_escort):
            hold = builder.hold(self._hold_point())

        join_pos = (
            WaypointBuilder.perturb(self.package.waypoints.ingress, feet(500))
            if self.flight.is_helo
            else self.package.waypoints.join
        )
        join = builder.join(join_pos)

        split = builder.split(self._get_split())

        is_helo = builder.flight.is_helo
        pf = self.package.primary_flight

        # When escorting a flight that flies a racetrack orbit (AWACS/tanker), hold
        # on that racetrack so the escort actually co-locates with and protects it.
        # Otherwise the hold defaults to the package's target-relative geometry, which
        # can land 70-80 NM away from where the protected flight actually orbits.
        racetrack_hold = self._racetrack_hold_point(pf)
        if racetrack_hold is not None:
            initial = builder.escort_hold(racetrack_hold)
        else:
            initial = builder.escort_hold(
                target.position if is_helo else self.package.waypoints.initial,
            )

        if pf and pf.flight_type in [FlightType.AIR_ASSAULT, FlightType.TRANSPORT]:
            layout = pf.flight_plan.layout
            assert isinstance(layout, AirAssaultLayout) or isinstance(
                layout, AirliftLayout
            )
            if isinstance(layout, AirliftLayout):
                ascent = layout.pickup_ascent or layout.drop_off_ascent
                assert ascent is not None
                join = builder.join(ascent.position)
                if layout.pickup and layout.drop_off_ascent:
                    join = builder.join(layout.drop_off_ascent.position)
            split = builder.split(layout.arrival.position)
            if layout.drop_off:
                initial = builder.escort_hold(
                    layout.drop_off.position,
                )

        refuel = self._build_refuel(builder)

        departure = builder.takeoff(self.flight.departure)
        nav_to = builder.nav_path(
            hold.position if hold else departure.position,
            join.position,
            builder.get_cruise_altitude,
        )

        nav_from = builder.nav_path(
            refuel.position if refuel else split.position,
            self.flight.arrival.position,
            builder.get_cruise_altitude,
        )

        return FormationAttackLayout(
            departure=departure,
            hold=hold,
            nav_to=nav_to,
            join=join,
            ingress=ingress,
            initial=initial,
            targets=[target],
            split=split,
            refuel=refuel,
            nav_from=nav_from,
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
        )

    @staticmethod
    def _racetrack_hold_point(primary: Optional[Flight]) -> Optional[Point]:
        """Center of the protected flight's racetrack, if it flies one.

        AWACS and tanker flights orbit a racetrack that is stationed far from the
        package's target reference (70-80 NM beyond the threat boundary). Returning
        the racetrack center lets the escort hold on the orbit it is meant to
        protect, instead of at the unrelated target-relative escort-hold geometry.
        Returns None for non-racetrack primaries, leaving the default behaviour.
        """
        if primary is None:
            return None
        flight_plan = primary.flight_plan
        if not flight_plan.is_patrol(flight_plan):
            return None
        layout = flight_plan.layout
        assert isinstance(layout, PatrollingLayout)
        return layout.patrol_start.position.midpoint(layout.patrol_end.position)

    def build(self, dump_debug_info: bool = False) -> EscortFlightPlan:
        return EscortFlightPlan(self.flight, self.layout())


class EwarBuilder(Builder):
    def layout(self) -> FormationAttackLayout:
        layout = super().layout()
        # Replace the near-target ESCORT HOLD with a JAMMING HOLD at the threat-aware
        # ingress standoff so the jammer holds with the package instead of orbiting
        # inside the target's threat ring. Air-assault/transport escorts (which hold at
        # the drop-off zone) are left untouched.
        pf = self.package.primary_flight
        is_air_assault = pf is not None and pf.flight_type in [
            FlightType.AIR_ASSAULT,
            FlightType.TRANSPORT,
        ]
        if layout.initial is not None and not is_air_assault:
            # Anchor the hold on the ingress waypoint itself: the threat-aware IP for
            # fixed-wing, or the helo's 5 NM re-anchored ingress. Using layout.ingress
            # (not package.waypoints.ingress) keeps the route monotonic for both, so a
            # player-flown helo jammer doesn't backtrack.
            builder = WaypointBuilder(self.flight)
            layout.initial = builder.jamming_hold(layout.ingress.position)
        return layout

    def build(self, dump_debug_info: bool = False) -> EscortFlightPlan:
        return EwarFlightPlan(self.flight, self.layout())
