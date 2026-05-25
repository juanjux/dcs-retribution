import logging
from typing import List

from dcs.point import MovingPoint
from dcs.task import AttackUnit, OptFormation, WeaponType

from game.ato.flighttype import FlightType
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

        # Collect every live unit across all groups in the target. We attack
        # individual units (AttackUnit) rather than the group as a whole: for
        # naval targets the DCS AI bunches all weapons on the same "priority"
        # ship of a group, so AttackGroup leaves the rest of the fleet
        # untouched. AttackUnit lets us distribute strikes across ships.
        #
        # IMPORTANT: TheaterUnit.id (Retribution-side, what we see in the UI
        # and store as the user's override) is NOT the same as the pydcs unit
        # id that DCS uses for the AttackUnit task. We have to match them by
        # name (the format is "<id zero-padded> | <type name>", which both
        # sides use). Without this mapping, AttackUnit tasks reference a
        # non-existent unit id and the AI falls back to opportunistic
        # engagement -- often hitting the wrong fleet.
        live: List[tuple[int, int]] = []  # (theater_unit_id, miz_unit_id)
        for tgo_group in tgo_groups:
            miz_group = self.mission.find_group(tgo_group.group_name)
            if miz_group is None:
                logging.error(
                    "Could not find group for Anti-Ship mission %s",
                    tgo_group.group_name,
                )
                continue
            miz_by_name = {u.name: u for u in miz_group.units}
            for theater_unit in tgo_group.units:
                if not theater_unit.alive:
                    continue
                miz_unit = miz_by_name.get(str(theater_unit))
                if miz_unit is None:
                    logging.warning(
                        "Anti-Ship: TheaterUnit %s has no matching pydcs unit "
                        "in group %s; skipping.",
                        theater_unit,
                        tgo_group.group_name,
                    )
                    continue
                live.append((theater_unit.id, miz_unit.id))

        if not live:
            logging.warning(
                "Anti-Ship flight %s has no live target units; it will not "
                "engage anything.",
                self.flight,
            )
            return

        # If the user picked a specific first target in the Edit flight dialog
        # and that unit is still alive, put it first. Override is stored as a
        # TheaterUnit.id (what the UI shows); map it back to its pydcs unit
        # id here. Otherwise (no override, or override targets a dead unit)
        # fall back to round-robin across the package's Anti-Ship flights so
        # flights distribute their initial targets across the fleet instead
        # of all attacking the same ship.
        override_theater_id = self.flight.target_unit_id_override
        override_idx = next(
            (i for i, (t, _m) in enumerate(live) if t == override_theater_id),
            None,
        )
        if override_idx is not None:
            entry = live.pop(override_idx)
            live.insert(0, entry)
        else:
            antiship_flights = [
                f
                for f in self.package.flights
                if f.flight_type == FlightType.ANTISHIP
            ]
            if len(antiship_flights) > 1:
                try:
                    idx = antiship_flights.index(self.flight)
                except ValueError:
                    idx = 0
                offset = idx % len(live)
                live = live[offset:] + live[:offset]

        # Deliberately omit WeaponType.Unguided: that category includes the
        # gun, so emitting an Unguided attack task tells the AI it can also
        # strafe the ships. The AI then closes inside the fleet's air defences
        # even on aircraft with no useful gun (e.g. the S-3B with Harpoons)
        # and gets shot down before firing its standoff weapons. Standoff-
        # friendly categories only.
        for ordnance in (WeaponType.Antiship, WeaponType.Guided):
            for _theater_id, miz_unit_id in live:
                task = AttackUnit(
                    miz_unit_id, weapon_type=ordnance, group_attack=True
                )
                waypoint.tasks.append(task)
