import logging
import math
from typing import Optional

from dcs.point import MovingPoint
from dcs.task import (
    AttackGroup,
    Expend,
    OptECMUsing,
    SetImmortalCommand,
    WeaponType as DcsWeaponType,
    OptRestrictAfterburner,
)

from game.theater import TheaterGroundObject
from game.utils import Distance
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

        # Stand-off decoy run (opt-in per flight) ---------------------------------
        # A decoy (e.g. TALD) is only ever released by an AttackGroup against a real
        # group, and the AI always closes to the decoy's launch range *from that
        # group*. Against the real ships that means penetrating the SAM envelope,
        # where the flight is shot before it releases. So we plant a hidden, unarmed
        # "bait" group just inside the threat ring and release the decoys at *that*:
        # the AI closes to launch range from the bait (~just inside the ring), i.e.
        # it fires from outside the SAM's reach, and the decoys glide the rest of the
        # way in to draw fire. The bait exists only in the generated mission (never in
        # the campaign save) and is hidden on the map.
        threat = target.max_threat_range()
        bait_id: Optional[int] = None
        if self.flight.release_at_ingress and threat.meters > 0:
            bait_id = self._spawn_decoy_bait(target, waypoint, threat)
        if bait_id is not None:
            waypoint.tasks.append(
                AttackGroup(
                    bait_id,
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
            waypoint.tasks.append(
                AttackGroup(
                    miz_group.id,
                    weapon_type=DcsWeaponType.Decoy,
                    group_attack=True,
                    expend=Expend.All,
                    altitude=round(waypoint.alt * 1.5),  # 50% increase to force a climb
                )
            )

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

    def _spawn_decoy_bait(
        self, target: TheaterGroundObject, waypoint: MovingPoint, threat: Distance
    ) -> Optional[int]:
        """Plant a hidden, unarmed enemy "bait" ship just inside the target's threat
        ring, on the ingress->target bearing, and return its group id (or None if we
        can't build one). Decoys released at this bait fall inside the SAM detection
        zone while the flight fires from stand-off. The bait lives only in the
        generated mission, not in the campaign save."""
        # The target's coalition is by definition the flight's opponent, so its
        # faction/country make the bait an enemy of the attacking flight (either side).
        # Any failure here must degrade to the normal decoy attack, never break
        # mission generation, so swallow and fall back.
        try:
            faction = target.control_point.coalition.faction
            country = self.mission.country(faction.country.name)
            if country is None:
                return None
            ingress_dist = target.position.distance_to_point(waypoint.position)
            # Just inside the threat ring, never beyond the ingress (keep it inbound).
            offset = min(threat.meters * 0.9, ingress_dist * 0.9)
            bearing = target.position.heading_between_point(waypoint.position)
            aim = target.position.point_from_heading(bearing, offset)
            bait = self.mission.ship_group(
                country,
                f"{self.group.name} decoy bait",
                faction.cargo_ship.dcs_unit_type,
                position=aim,
            )
            bait.hidden = True
            # Immortal so the friendly fleet's fire can't sink the bait before the
            # SEAD flight arrives to release its decoys at it. (SetInvisible also stops
            # the fleet firing, but it hides the bait from the SEAD flight too, so the
            # flight finds no target and never releases -- so we can't use it here.)
            bait.points[0].tasks.append(SetImmortalCommand(True))
            return bait.id
        except Exception:
            logging.exception("Could not spawn SEAD decoy bait; using normal attack")
            return None
