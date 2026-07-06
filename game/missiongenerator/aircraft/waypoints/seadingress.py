import logging
import math

from dcs.point import MovingPoint
from dcs.task import (
    AttackGroup,
    Bombing,
    EngageGroup,
    Expend,
    OptECMUsing,
    WeaponType as DcsWeaponType,
    OptRestrictAfterburner,
)

from game.data.weapons import WeaponType
from game.theater import TheaterGroundObject
from .pydcswaypointbuilder import PydcsWaypointBuilder


class SeadIngressBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        self.register_special_strike_points(self.waypoint.targets)
        self.register_special_ingress_points()

        target = self.package.target
        if not isinstance(target, TheaterGroundObject):
            logging.error(
                "Unexpected target type for SEAD mission: %s",
                target.__class__.__name__,
            )
            return

        # Preemptively use ECM to better avoid getting swatted.
        ecm_option = OptECMUsing(value=OptECMUsing.Values.UseIfDetectedLockByRadar)
        waypoint.tasks.append(ecm_option)

        # Avoid having AI burn all of its fuel while loitering until next weapon release
        burn_restrict = OptRestrictAfterburner(True)
        waypoint.tasks.append(burn_restrict)

        # Stand-off decoy run (prototype) -----------------------------------------
        # A pure-decoy (e.g. all-TALD) SEAD flight carries nothing that can actually
        # hit the target, so the default AttackGroup makes it close to the decoy's
        # launch range — deep inside the SAM envelope — where it just gets shot and
        # goes defensive before ever releasing. Instead, aim the decoys at a point
        # ~just inside the threat ring on the ingress->target bearing: the AI
        # releases from stand-off (outside the SAM's reach) and the decoys glide
        # into the detection zone, baiting the SAMs. We deliberately do NOT need the
        # decoys to reach the target — only to be seen.
        threat = target.max_threat_range()
        if self._decoys_only() and threat.meters > 0:
            bearing = target.position.heading_between_point(waypoint.position)
            aim = target.position.point_from_heading(bearing, threat.meters * 0.9)
            waypoint.tasks.append(
                Bombing(
                    position=aim,
                    weapon_type=DcsWeaponType.Decoy,
                    group_attack=True,
                    expend=Expend.All,
                    altitude=round(waypoint.alt * 1.5),  # climb for a longer glide
                )
            )
            waypoint.tasks.append(OptRestrictAfterburner(False))
            return

        for group in target.groups:
            miz_group = self.mission.find_group(group.group_name)
            if miz_group is None:
                logging.error(
                    f"Could not find group for SEAD mission {group.group_name}"
                )
                continue

            # Use decoys first
            attack_task = AttackGroup(
                miz_group.id,
                weapon_type=DcsWeaponType.Decoy,
                group_attack=True,
                expend=Expend.All,
                altitude=round(waypoint.alt * 1.5),  # 50% increase to force a climb
            )
            waypoint.tasks.append(attack_task)

            attack_task = AttackGroup(
                miz_group.id,
                weapon_type=DcsWeaponType.ARM,
                expend=Expend.All,
                altitude=waypoint.alt,
                group_attack=True,
            )
            waypoint.tasks.append(attack_task)

            attack_task = AttackGroup(
                miz_group.id,
                weapon_type=DcsWeaponType.ASM,
                expend=Expend.All,
                altitude=waypoint.alt,
                group_attack=True,
            )
            waypoint.tasks.append(attack_task)

            attack_task = AttackGroup(
                miz_group.id,
                weapon_type=DcsWeaponType.GuidedBombs,
                expend=Expend.All,
                altitude=waypoint.alt,
                group_attack=True,
            )
            waypoint.tasks.append(attack_task)

            dir = target.position.heading_between_point(waypoint.position)

            attack_task = AttackGroup(
                miz_group.id,
                weapon_type=DcsWeaponType.Unguided,
                attack_limit=1,
                expend=Expend.All,
                direction=math.radians(dir),
                altitude=waypoint.alt,
            )
            waypoint.tasks.append(attack_task)

        burn_free = OptRestrictAfterburner(False)
        waypoint.tasks.append(burn_free)

    def _decoys_only(self) -> bool:
        """True if this SEAD flight is a pure decoy (e.g. TALD) run: it carries
        decoys and none of the strike weapons (HARM / laser-guided bombs) that need
        to close to a real target. Such a flight can release its decoys from
        stand-off instead of penetrating the SAM envelope."""
        f = self.flight
        return (
            f.any_member_has_weapon_of_type(WeaponType.DECOY)
            and not f.any_member_has_weapon_of_type(WeaponType.ARM)
            and not f.any_member_has_weapon_of_type(WeaponType.LGB)
        )
