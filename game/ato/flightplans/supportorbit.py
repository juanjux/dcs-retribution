"""Shared placement for theater support racetracks (AEW&C and tankers).

Both support types want the same thing: a racetrack sitting a safe standoff
*behind the front line*, centered on the fighting, flying parallel to the FLOT.
The old per-builder logic anchored the orbit on a control point
(``package.target``) and offset it along the bearing to the nearest enemy
threat-zone boundary. For a rear/flank CP that bearing is unstable -- it swings
as the front shifts -- so AI AWACS in particular got flung hundreds of NM
off-axis (observed: red AWACS anchored on a far-north CP ended up ~175 NM
laterally off the front and ~326 NM behind it). Tankers anchored on their own
departure field could even clamp onto the home runway.

This helper instead anchors on the **front line center** and pushes the orbit
into friendly territory along the stable enemy->friendly axis until it is at
least ``threat_buffer`` from the enemy threat zone. The result is centered on
the front and at the configured standoff regardless of where the supporting
squadron is based.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from game.utils import Distance, Heading, meters

if TYPE_CHECKING:
    from dcs.mapping import Point
    from game.theater import ConflictTheater, MissionTarget, Player
    from game.theater.frontline import FrontLine
    from game.threatzones import ThreatZones


# AI (enemy) support orbits sit this many *buffers* behind the FLOT, so red
# tankers/AWACS hold deep in friendly airspace instead of loitering near the
# front like the player's do. The player coalition uses 1x (kept forward for
# coverage). With the default buffers (AEWC 80 NM / tanker 70 NM) this puts AI
# support ~200/175 NM back; with a smaller campaign buffer it scales down.
# Whatever the depth, the orbit is still pushed clear of the enemy threat zone.
AI_SUPPORT_DEPTH_FACTOR = 2.5


def _relevant_front(
    theater: ConflictTheater, target: MissionTarget
) -> Optional[FrontLine]:
    """The active front nearest the supported area (``target``)."""
    fronts = list(theater.conflicts())
    if not fronts:
        return None
    return min(fronts, key=lambda fl: fl.position.distance_to_point(target.position))


def support_orbit_anchor(
    theater: ConflictTheater,
    player: Player,
    threat_zones: ThreatZones,
    target: MissionTarget,
    threat_buffer: Distance,
) -> tuple[Point, Heading]:
    """Where a support racetrack should sit, and which way it faces.

    Returns ``(center, toward_enemy)`` where ``center`` is the racetrack center
    (the standoff point behind the front) and ``toward_enemy`` is the heading
    pointing at the enemy -- callers orient the racetrack perpendicular to it so
    the orbit runs parallel to the FLOT.
    """
    front = _relevant_front(theater, target)
    if front is None:
        # No active front (e.g. opening turn): fall back to anchoring on the
        # target and standing off from the nearest threat boundary.
        anchor = target.position
        boundary = threat_zones.closest_boundary(anchor)
        toward_enemy = Heading.from_degrees(anchor.heading_between_point(boundary))
        center = anchor
    else:
        anchor = front.position
        friendly_cp = front.blue_cp if player.is_blue else front.red_cp
        enemy_cp = front.red_cp if player.is_blue else front.blue_cp
        # Stable axis: it tracks the front, not a wandering boundary bearing.
        toward_enemy = Heading.from_degrees(
            friendly_cp.position.heading_between_point(enemy_cp.position)
        )
        center = anchor

    away_from_enemy = toward_enemy.opposite

    # Base standoff behind the front: the player holds forward at 1x the buffer
    # for coverage; the AI holds deep (AI_SUPPORT_DEPTH_FACTOR x) so red
    # tankers/AWACS don't loiter near the FLOT.
    factor = 1.0 if player.is_blue else AI_SUPPORT_DEPTH_FACTOR
    base_push = threat_buffer * factor
    if base_push > meters(0):
        center = center.point_from_heading(away_from_enemy.degrees, base_push.meters)

    # Then guarantee it is at least threat_buffer clear of the enemy threat zone,
    # pushing further into friendly airspace if the base standoff left it exposed.
    distance_to_threat = threat_zones.distance_to_threat(center)
    if threat_zones.threatened(center):
        # Inside the threat zone: get clear, then add the buffer.
        extra = distance_to_threat + threat_buffer
    elif distance_to_threat < threat_buffer:
        extra = threat_buffer - distance_to_threat
    else:
        extra = meters(0)

    if extra > meters(0):
        center = center.point_from_heading(away_from_enemy.degrees, extra.meters)

    return center, toward_enemy
