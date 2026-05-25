import logging
from typing import List

from dcs.point import MovingPoint
from dcs.task import AttackGroup, OptFormation, WeaponType

from game.ato.flighttype import FlightType
from game.theater import NavalControlPoint, TheaterGroundObject
from .pydcswaypointbuilder import PydcsWaypointBuilder


class AntiShipIngressBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        self.register_special_ingress_points()
        group_names: List[str] = []
        waypoint.tasks.append(OptFormation.finger_four_open())

        target = self.package.target
        if isinstance(target, NavalControlPoint):
            # Use the carrier/LHA group the flight plan actually routes to
            # (AntiShipFlightPlan targets find_main_tgo()), not
            # ground_objects[0]: a naval control point can own several ground
            # objects and the first is not necessarily the carrier. Targeting
            # the wrong one (e.g. a sunk escort group that is never spawned)
            # leaves the flight with no AttackGroup task, so the AI flies to
            # the ingress point and turns away without engaging.
            carrier_tgo = target.find_main_tgo()
            for g in carrier_tgo.groups:
                group_names.append(g.group_name)
        elif isinstance(target, TheaterGroundObject):
            for group in target.groups:
                group_names.append(group.group_name)
        else:
            logging.error(
                "Unexpected target type for Anti-Ship mission: %s",
                target.__class__.__name__,
            )
            return

        # Rotate the target group list per Anti-Ship flight in the package so
        # flights don't all bunch up on the same group. Index is taken among
        # Anti-Ship flights only (not escorts/SEAD/etc. in the same package)
        # so the offsets advance one per attacking flight and the distribution
        # is even. Only helps when the target has more than one group; a
        # single-group target (typical naval TGO) gives len(group_names)=1 and
        # all flights attack the same group.
        antiship_flights = [
            f for f in self.package.flights if f.flight_type == FlightType.ANTISHIP
        ]
        if group_names and len(antiship_flights) > 1:
            try:
                idx = antiship_flights.index(self.flight)
            except ValueError:
                idx = 0
            offset = idx % len(group_names)
            group_names = group_names[offset:] + group_names[:offset]

        added = 0
        # Deliberately omit WeaponType.Unguided: that category includes the
        # gun, so emitting an Unguided AttackGroup task tells the AI it can
        # also strafe the ships. The AI then closes inside the fleet's air
        # defences even on aircraft with no useful gun (e.g. an S-3B with
        # Harpoons) and gets shot down before it has fired its standoff
        # weapons. Standoff-friendly categories only.
        for ordnance in (WeaponType.Antiship, WeaponType.Guided):
            added += self.add_attack_group_tasks_for_ordnance(
                waypoint, group_names, ordnance
            )

        if not added:
            logging.warning(
                "Anti-Ship flight %s has no attackable target group "
                "(resolved %s); it will not engage anything.",
                self.flight,
                group_names or "no groups",
            )

    def add_attack_group_tasks_for_ordnance(
        self,
        waypoint: MovingPoint,
        group_names: List[str],
        ordnance: WeaponType,
    ) -> int:
        added = 0
        for group_name in group_names:
            miz_group = self.mission.find_group(group_name)
            if miz_group is None:
                logging.error(
                    "Could not find group for Anti-Ship mission %s", group_name
                )
                continue

            task = AttackGroup(miz_group.id, group_attack=True, weapon_type=ordnance)
            waypoint.tasks.append(task)
            added += 1
        return added
