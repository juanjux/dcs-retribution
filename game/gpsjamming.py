"""GPS jamming -- the campaign side.

DCS models no GPS receiver, so a jammer cannot be made to degrade a jet's
navigation or a weapon's guidance through any engine API. What it *can* do is
watch the released weapon: the runtime hooks ``S_EVENT_SHOT``, tracks each
satellite-guided store, and -- if that store flies through a live jammer's bubble
-- destroys it just short of impact and detonates it a scored distance off the
aimpoint. The bomb visibly goes long. That is the whole trick, and it is honest
in the ways that matter: real ordnance from a real jet, no phantom spawns, no
invented kills, and killing the jammer restores accuracy immediately.

This module owns the *campaign* half:

* which ground units jam (any unit whose definition carries a ``gps_jamming``
  block -- see :class:`game.dcs.groundunittype.GpsJammingProperties`),
* where the live sites are and how far each reaches, and
* what the player is briefed about them (recon-fogged: an un-engaged jammer is
  not on the kneeboard, so finding it is worth a recon sortie).

The runtime half is ``resources/plugins/gpsjamming``; the bridge between them is
``game/missiongenerator/gpsjammingluadata.py``.

Symmetric by construction: a site degrades the *opposing* coalition's weapons, so
a blue jammer works the day a blue faction fields one. In practice red owns them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterator, Optional

from game.utils import Distance, meters, nautical_miles

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint

#: DCS weapon *type name* fragments that identify a satellite-guided store.
#: Matched as plain, case-insensitive substrings (never a Lua pattern -- weapon
#: names carry ``-`` and ``(`` which a pattern match would read as magic
#: ), so ``GBU-31`` catches every ``GBU-31(V)*/B`` variant at once.
#:
#: Curated deliberately narrowly (squadron call 2026-08-04): **GPS-guided air
#: ordnance only**. Laser, TV, IR and anti-radiation weapons do not use GPS and
#: must never appear here -- a Paveway that mysteriously misses is a bug report,
#: not a feature. Ship-launched land-attack cruise missiles are
#: deliberately absent too: they are their own flown feature and coupling them to
#: an unflown one buys nothing.
#:
#: ``GBU-54`` (Laser JDAM) is included because its *baseline* mode is GPS/INS --
#: it only becomes a laser weapon when someone is lasing, which the runtime
#: cannot see. ``KAB-500S``/``KAB-1500S`` are the GLONASS Russian equivalents, so
#: red eats its own medicine wherever blue fields a jammer.
#: The SLAM/SLAM-ER family is deliberately ABSENT. Its GPS/INS leg is only the
#: midcourse: the imaging seeker can be brought up far outside a jammer's reach --
#: bubbles are around 15 nm -- so by the time the weapon is over denied ground it is
#: already looking at the target and no longer navigating by satellite. Degrading it
#: would punish a weapon that, flown properly, does not depend on GPS where it counts.
GPS_GUIDED_WEAPON_PATTERNS: tuple[str, ...] = (
    "GBU-31",  # JDAM, 2000 lb
    "GBU-32",  # JDAM, 1000 lb
    "GBU-38",  # JDAM, 500 lb
    "GBU-54",  # Laser JDAM (GPS/INS baseline)
    "JDAM",  # any mod store that names itself plainly
    "AGM-154",  # JSOW A/B/C
    "JSOW",
    "AGM-158",  # JASSM / JASSM-ER
    "JASSM",
    "CBU-103",  # WCMD -- inertial/GPS-corrected dispensers
    "CBU-105",
    "CBU-97_",  # the WCMD variant names; the plain CBU-97 is unguided
    "KAB_500S",  # GLONASS
    "KAB-500S",
    "KAB_1500S",
    "KAB-1500S",
)

#: The reach a jammer gets when its unit definition names none.
#:
#: Sized off what the bubble actually IS: a GPS-denied **target** area, not a
#: denied release area. A weapon aimed at anything inside the bubble flies
#: through the bubble whatever range it was released from, so standing off does
#: not help a covered target -- the radius is simply the size of the target set
#: that loses satellite guidance. At 27-30 nm one site denied a large share of a
#: medium map; 15 nm denies a target cluster, so a campaign can field two or
#: three on distinct clusters and most of the theatre stays GPS-usable.
DEFAULT_REACH = nautical_miles(15)

#: How far off the aimpoint a fully-jammed weapon lands when the unit definition
#: and the campaign setting both stay quiet. Far enough to be a clean miss, close
#: enough to read as "the bomb went long", not "the bomb vanished".
DEFAULT_MISS_RADIUS = meters(200)


@dataclass(frozen=True)
class GpsJammerSite:
    """One live GPS-jamming site, as the runtime needs it."""

    #: The TGO's display name -- what the kneeboard brief calls it.
    name: str
    #: ``"blue"`` / ``"red"`` -- the side that OWNS the jammer. The runtime
    #: degrades the *other* side's weapons.
    coalition: str
    #: Campaign-map position (pydcs Point frame: x north, y east).
    x: float
    y: float
    #: Denial reach and the miss the runtime scores at full strength.
    reach: Distance
    miss_radius: Distance
    #: The generated DCS *unit* names of the jammer vehicles themselves, so the
    #: runtime can re-check liveness: a jammer the player kills mid-mission stops
    #: denying GPS.
    #:
    #: Unit names, NOT group names -- a jammer shares its DCS group with whatever
    #: else the site fields (its escort, its radar), so a group-level liveness
    #: check would keep jamming after the jammer truck itself was destroyed, on
    #: the strength of some surviving truck beside it. The player must be able to
    #: kill the thing that is jamming them.
    unit_names: tuple[str, ...]


def gps_jamming_enabled(game: "Game") -> bool:
    """Whether the feature is switched on for this campaign."""
    return bool(getattr(game.settings, "gps_jamming", False))


def gps_jammer_sites(game: "Game") -> list[GpsJammerSite]:
    """Every live GPS-jamming site in the theater, both coalitions.

    Ground truth (``viewer=None``) -- this feeds the runtime, which must behave
    the same whether or not the player has engaged the site. The *briefing* is
    fogged separately (:func:`briefed_jammer_areas`).
    """
    if not gps_jamming_enabled(game):
        return []
    default_reach = _campaign_default_reach(game)
    default_miss = _campaign_default_miss(game)
    sites: list[GpsJammerSite] = []
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            site = _site_for_tgo(tgo, cp, default_reach, default_miss)
            if site is not None:
                sites.append(site)
    return sites


def briefed_jammer_areas(game: "Game", viewer: Any) -> list[GpsJammerSite]:
    """The enemy jamming areas ``viewer`` has actually found, for the kneeboard.

    Recon-fogged through the standard ``known_for`` leaf, so an un-engaged
    jammer is *not* briefed -- the first sign of it is a pass that goes long, and
    identifying it is worth a TARPS sortie. Friendly jammers are omitted: they do
    not threaten the viewer's own weapons.
    """
    briefed: list[GpsJammerSite] = []
    wanted = "blue" if not _is_blue(viewer) else "red"
    default_reach = _campaign_default_reach(game)
    default_miss = _campaign_default_miss(game)
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            site = _site_for_tgo(tgo, cp, default_reach, default_miss)
            if site is None or site.coalition != wanted:
                continue
            # This fork has no recon fog, so every jammer is briefed. Kept as a
            # duck-typed check rather than deleted: a build that grows a fog leaf
            # starts respecting it without touching this feature.
            known_for = getattr(tgo, "known_for", None)
            if known_for is not None:
                try:
                    if not known_for(viewer):
                        continue
                except TypeError:
                    pass
            briefed.append(site)
    return briefed


def _site_for_tgo(
    tgo: Any,
    cp: "ControlPoint",
    default_reach: Distance,
    default_miss: Distance,
) -> Optional[GpsJammerSite]:
    """Build the site record for a TGO that carries live jammer vehicles."""
    units: list[str] = []
    # A site with several jammer types takes the LONGEST declared reach and the
    # WORST declared miss: the strongest emitter present is what the weapon
    # actually hears. Units that declare neither ride the campaign defaults.
    reach = default_reach
    miss = default_miss
    for group in getattr(tgo, "groups", []) or []:
        for unit, props in _live_jammers(group):
            name = getattr(unit, "unit_name", None)
            if not name:
                continue
            units.append(str(name))
            if props.radius_nm is not None:
                reach = max(reach, nautical_miles(props.radius_nm))
            if props.miss_radius_m is not None:
                miss = max(miss, meters(props.miss_radius_m))
    if not units:
        return None
    position = getattr(tgo, "position", None)
    if position is None or not hasattr(position, "x"):
        return None
    return GpsJammerSite(
        name=str(getattr(tgo, "name", None) or getattr(tgo, "obj_name", "GPS jammer")),
        coalition="blue" if _is_blue(cp.captured) else "red",
        x=float(position.x),
        y=float(position.y),
        reach=reach,
        miss_radius=miss,
        unit_names=tuple(units),
    )


def _live_jammers(group: Any) -> Iterator[tuple[Any, Any]]:
    """Every ALIVE jammer unit in the group, with its ``GpsJammingProperties``.

    A destroyed jammer stops denying GPS immediately -- that is the whole reward
    for finding and striking it, so liveness is checked here as well as at
    runtime (this decides whether the site is emitted at all).
    """
    for unit in getattr(group, "units", []) or []:
        if not getattr(unit, "alive", False):
            continue
        unit_type = getattr(unit, "unit_type", None)
        props = getattr(unit_type, "gps_jamming", None)
        if props is not None:
            yield unit, props


def _campaign_default_reach(game: "Game") -> Distance:
    value = getattr(game.settings, "gps_jamming_default_reach_nm", None)
    if not value:
        return DEFAULT_REACH
    return nautical_miles(float(value))


def _campaign_default_miss(game: "Game") -> Distance:
    value = getattr(game.settings, "gps_jamming_miss_radius_m", None)
    if not value:
        return DEFAULT_MISS_RADIUS
    return meters(float(value))


def _is_blue(player: Any) -> bool:
    """``player`` is a ``Player``/bool-ish coalition marker.

    Never ``if player:`` -- the enum-truthiness trap (a falsy RED enum member
    reads as "no player at all"); always the explicit ``is_blue`` accessor with a
    bool fallback for the test doubles.
    """
    is_blue = getattr(player, "is_blue", None)
    if is_blue is None:
        return bool(player)
    return bool(is_blue)
