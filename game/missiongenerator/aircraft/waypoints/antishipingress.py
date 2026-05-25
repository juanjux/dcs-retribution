import logging
from typing import List

from dcs.point import MovingPoint
from dcs.task import AttackUnit, OptFormation, WeaponType

from game.theater import NavalControlPoint, TheaterGroundObject
from .pydcswaypointbuilder import PydcsWaypointBuilder


class AntiShipIngressBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        self.register_special_ingress_points()
        waypoint.tasks.append(OptFormation.finger_four_open())

        target = self.package.target
        if isinstance(target, NavalControlPoint):
            # Use the carrier/LHA group the flight plan actually routes to
            # (AntiShipFlightPlan targets find_main_tgo()), not
            # ground_objects[0]: a naval control point can own several ground
            # objects and the first is not necessarily the carrier. Targeting
            # the wrong one (e.g. a sunk escort group that is never spawned)
            # leaves the flight with no AttackUnit task, so the AI flies to
            # the ingress point and turns away without engaging.
            tgo_groups = target.find_main_tgo().groups
        elif isinstance(target, TheaterGroundObject):
            tgo_groups = target.groups
        else:
            logging.error(
                "Unexpected target type for Anti-Ship mission: %s",
                target.__class__.__name__,
            )
            return

        # Collect every live unit id across all groups in the target. We attack
        # individual units (AttackUnit) rather than the group as a whole: for
        # naval targets the DCS AI bunches all weapons on the same "priority"
        # ship of a group, so AttackGroup leaves the rest of the fleet
        # untouched. AttackUnit lets us distribute strikes across ships.
        live_unit_ids: List[int] = []
        for tgo_group in tgo_groups:
            miz_group = self.mission.find_group(tgo_group.group_name)
            if miz_group is None:
                logging.error(
                    "Could not find group for Anti-Ship mission %s",
                    tgo_group.group_name,
                )
                continue
            for unit in tgo_group.units:
                if unit.alive:
                    live_unit_ids.append(unit.id)

        if not live_unit_ids:
            logging.warning(
                "Anti-Ship flight %s has no live target units; it will not "
                "engage anything.",
                self.flight,
            )
            return

        # Rotate the unit list per flight in the package so flights distribute
        # their initial targets across the fleet instead of all attacking the
        # same ship first. Each flight's task list is the same set of unit ids,
        # just starting from a different one.
        if len(self.package.flights) > 1:
            try:
                idx = self.package.flights.index(self.flight)
            except ValueError:
                idx = 0
            offset = idx % len(live_unit_ids)
            live_unit_ids = live_unit_ids[offset:] + live_unit_ids[:offset]

        # Deliberately omit WeaponType.Unguided: that category includes the
        # gun, so emitting an Unguided attack task tells the AI it can also
        # strafe the ships. The AI then closes inside the fleet's air defences
        # even on aircraft with no useful gun (e.g. the S-3B with Harpoons)
        # and gets shot down before firing its standoff weapons. Standoff-
        # friendly categories only.
        for ordnance in (WeaponType.Antiship, WeaponType.Guided):
            for unit_id in live_unit_ids:
                task = AttackUnit(
                    unit_id, weapon_type=ordnance, group_attack=True
                )
                waypoint.tasks.append(task)
