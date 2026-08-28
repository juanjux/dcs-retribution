import copy
from typing import Union

from dcs import Point
from dcs.planes import B_17G, B_52H, Tu_22M3, B_1B, F_15ESE
from dcs.point import MovingPoint
from dcs.task import Bombing, Expend, OptFormation, WeaponType, CarpetBombing

from game.utils import mach, meters
from .pydcswaypointbuilder import PydcsWaypointBuilder

#: Bounds DCS accepts for a bombing carpet. pydcs defaults to the upper one.
MIN_CARPET_LENGTH = 500.0
MAX_CARPET_LENGTH = 3000.0


class StrikeIngressBuilder(PydcsWaypointBuilder):
    _special_wpts_injected: bool = False

    def add_tasks(self, waypoint: MovingPoint) -> None:
        bomber = self.group.units[0].unit_type in [B_17G, Tu_22M3]
        bomber_guided = self.group.units[0].unit_type in [B_1B, B_52H]
        if bomber_guided or not bomber:
            waypoint.tasks.append(OptFormation.finger_four_open())
            self.add_strike_tasks(waypoint, WeaponType.ASM)
            waypoint.tasks.append(OptFormation.trail_open())
            self.add_strike_tasks(waypoint, WeaponType.GuidedBombs)

        waypoint.tasks.append(OptFormation.ww2_bomber_element_close())
        if bomber or bomber_guided:
            # A heavy bomber covers the whole objective in a single pass.
            self.add_bombing_tasks(waypoint)
        else:
            # Everything else re-attacks: one aimpoint per target with the load
            # split between them, rather than emptying the racks into the middle
            # of the objective and cratering whatever already died there.
            self.add_strike_tasks(waypoint, WeaponType.Bombs)
        waypoint.tasks.append(OptFormation.finger_four_open())
        self.register_special_ingress_points()

    def add_bombing_tasks(self, waypoint: MovingPoint) -> None:
        targets = self.waypoint.targets
        if not targets:
            return

        center: Point = copy.copy(targets[0].position)
        for target in targets[1:]:
            center += target.position
        center /= len(targets)
        # The carpet is laid along the run-in, so it has to span the objective
        # rather than its mean radius. The average came out at roughly a third of
        # the real spread -- 65 m over a camp several hundred metres across --
        # which stacked every bomb around the centroid, pass after pass.
        spread = max(center.distance_to_point(t.position) for t in targets)
        carpet_length = min(max(2.0 * spread, MIN_CARPET_LENGTH), MAX_CARPET_LENGTH)
        bombing: Union[CarpetBombing, Bombing]
        if self.group.task == "Ground Attack":
            bombing = CarpetBombing(
                center,
                weapon_type=WeaponType.Bombs,
                expend=Expend.All,
                carpet_length=carpet_length,
                altitude=waypoint.alt,
            )
        else:
            bombing = Bombing(
                center,
                weapon_type=WeaponType.Bombs,
                expend=Expend.All,
                group_attack=True,
                altitude=waypoint.alt,
            )
        waypoint.tasks.append(bombing)

    def add_strike_tasks(
        self, waypoint: MovingPoint, weapon_type: WeaponType = WeaponType.Auto
    ) -> None:
        if not self.waypoint.targets:
            # Nothing to strike (e.g. an objective whose units are all already
            # destroyed). Skip -- as add_bombing_tasks does -- so we neither add
            # an empty attack task nor divide by zero on the units/targets ratio.
            return
        bomber = self.group.units[0].unit_type in [B_1B, B_52H]
        ratio = len(self.group.units) / len(self.waypoint.targets)
        for target in self.waypoint.targets:
            bombing = Bombing(target.position, weapon_type=weapon_type)
            # If there is only one target, drop all ordnance in one pass with group attack.
            if len(self.waypoint.targets) == 1:
                bombing.params["expend"] = Expend.All.value
                bombing.params["groupAttack"] = True
            elif ratio >= 1:
                # #TGTs > 1 & #AC >= #TGTs => each AC drops entire payload per TGT
                bombing.params["expend"] = Expend.All.value
            elif 1 > ratio >= 0.5:
                # #TGTs > 1 & 2 * #AC >= #TGTs => each AC drops half payload per TGT
                bombing.params["expend"] = Expend.Half.value
            elif 0.5 > ratio >= 0.25:
                # #TGTs > 1 & 4 * #AC >= #TGTs => each AC drops quarter payload per TGT
                bombing.params["expend"] = Expend.Quarter.value
            elif 0.25 > ratio >= (1.0 / 6) and bomber:
                # #TGTs > 1 & 4 * #AC < #TGTs & bomber => each AC drops 4 bombs per TGT
                bombing.params["expend"] = Expend.Four.value
            elif bomber:
                # #TGTs > 1 & 6 * #AC < #TGTs & bomber => each AC drops 2 bombs per TGT
                bombing.params["expend"] = Expend.Two.value
            # else => Auto QTY

            waypoint.tasks.append(bombing)

            waypoint.speed = mach(0.85, meters(waypoint.alt)).meters_per_second

        # Register special waypoints
        if not self._special_wpts_injected:
            self.register_special_strike_points(self.waypoint.targets)
            if self.flight.unit_type.dcs_unit_type == F_15ESE:
                self.register_special_strike_points(self.flight.custom_targets, 2)
            self._special_wpts_injected = True
