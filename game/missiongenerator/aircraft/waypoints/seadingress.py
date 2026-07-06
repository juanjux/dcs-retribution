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

        # Stand-off release (opt-in per flight) -----------------------------------
        # Weapons that don't need a locked target (decoys, unguided) are normally
        # delivered by closing to their launch range -- for a decoy run that means
        # penetrating the SAM envelope, where the flight just gets shot before it
        # releases. When the flight opts in (release_at_ingress), aim those weapons
        # at a point ~just inside the threat ring on the ingress->target bearing
        # instead: the AI releases from stand-off (outside the SAM's reach) and they
        # sail into the detection zone to bait the SAMs (or lay unguided fire)
        # without penetrating. We deliberately don't need them to reach the target,
        # only to be seen. Guided/anti-radiation weapons still engage normally below.
        threat = target.max_threat_range()
        standoff = self.flight.release_at_ingress and threat.meters > 0
        if standoff:
            ingress_dist = target.position.distance_to_point(waypoint.position)
            # Keep the aim point inside the threat ring *and* inbound of the ingress
            # (so it's a point the flight is flying toward, within glide range).
            offset = min(threat.meters * 0.9, ingress_dist * 0.9)
            bearing = target.position.heading_between_point(waypoint.position)
            aim = target.position.point_from_heading(bearing, offset)
            for weapon_type in (DcsWeaponType.Decoy, DcsWeaponType.Unguided):
                waypoint.tasks.append(
                    Bombing(
                        position=aim,
                        weapon_type=weapon_type,
                        group_attack=True,
                        expend=Expend.All,
                        altitude=round(waypoint.alt * 1.5),  # climb for a longer glide
                    )
                )

        for group in target.groups:
            miz_group = self.mission.find_group(group.group_name)
            if miz_group is None:
                logging.error(
                    f"Could not find group for SEAD mission {group.group_name}"
                )
                continue

            if not standoff:
                # Use decoys first
                waypoint.tasks.append(
                    AttackGroup(
                        miz_group.id,
                        weapon_type=DcsWeaponType.Decoy,
                        group_attack=True,
                        expend=Expend.All,
                        altitude=round(waypoint.alt * 1.5),  # force a climb
                    )
                )

            # Anti-radiation / anti-ship / guided bombs need a real target, so they
            # always engage the group directly regardless of the stand-off option.
            waypoint.tasks.append(
                AttackGroup(
                    miz_group.id,
                    weapon_type=DcsWeaponType.ARM,
                    expend=Expend.All,
                    altitude=waypoint.alt,
                    group_attack=True,
                )
            )

            waypoint.tasks.append(
                AttackGroup(
                    miz_group.id,
                    weapon_type=DcsWeaponType.ASM,
                    expend=Expend.All,
                    altitude=waypoint.alt,
                    group_attack=True,
                )
            )

            waypoint.tasks.append(
                AttackGroup(
                    miz_group.id,
                    weapon_type=DcsWeaponType.GuidedBombs,
                    expend=Expend.All,
                    altitude=waypoint.alt,
                    group_attack=True,
                )
            )

            if not standoff:
                dir = target.position.heading_between_point(waypoint.position)
                waypoint.tasks.append(
                    AttackGroup(
                        miz_group.id,
                        weapon_type=DcsWeaponType.Unguided,
                        attack_limit=1,
                        expend=Expend.All,
                        direction=math.radians(dir),
                        altitude=waypoint.alt,
                    )
                )

        burn_free = OptRestrictAfterburner(False)
        waypoint.tasks.append(burn_free)
