"""GPS jamming -> Lua config bridge (``dcsRetribution.gpsJamming``).

The the fork's emitter. Python owns which ground sites deny GPS and how far each
reaches (``game/gpsjamming.py``); this hands the ``gpsjamming``
plugin the runtime's whole world view:

* ``sites`` -- one record per live jammer: the owning coalition, the campaign
  position, the denial reach, the miss it scores at full strength, and the
  generated DCS group names so the runtime can re-check liveness (kill the
  jammer mid-mission and accuracy returns on the next weapon).
* ``weaponPatterns`` -- the curated satellite-guided weapon fragments. Emitted
  rather than hardcoded in the Lua so the pattern list has exactly one home
  (Python) and a campaign can never drift from it.

Emits nothing unless the setting is on and a live jammer exists, so a normal
mission carries no ``gpsJamming`` node and the plugin no-ops.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData


def populate_gps_jamming_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.gpsJamming`` subtree."""
    from game.gpsjamming import (
        GPS_GUIDED_WEAPON_PATTERNS,
        gps_jammer_sites,
        gps_jamming_enabled,
    )

    sites = gps_jammer_sites(game)
    if not sites:
        # Say so at generation time, while it can still be fixed. "The setting is
        # on but nothing jams" is otherwise indistinguishable from "the feature is
        # broken" -- and the likeliest cause is a campaign whose factions field no
        # unit carrying a `gps_jamming` block (or one whose jammers are all dead).
        if gps_jamming_enabled(game):
            logging.info(
                "GPS jamming is enabled but no live jamming site exists in this "
                "theater -- no unit in play declares a `gps_jamming` block in its "
                "definition (resources/units/ground_units/<unit>.yaml), or every "
                "jammer is destroyed. Nothing will be jammed this mission."
            )
        return

    node = root.add_item("gpsJamming")
    # As its OWN child item, never add_data_array on the node: LuaData.serialize
    # drops an object's scalar key-values once it also has nested items, so the
    # pattern list would silently vanish alongside `sites` (the same trap the
    # IADS `engine` marker hit).
    node.add_item("weaponPatterns").set_data_array(list(GPS_GUIDED_WEAPON_PATTERNS))
    site_list = node.add_item("sites")
    for site in sites:
        rec = site_list.add_item()
        rec.add_key_value("name", site.name)
        rec.add_key_value("coalition", site.coalition)
        # pydcs Point: x = north, y = east (the emitter frame every 414th mover
        # plugin shares; the Lua converts to the DCS x/z world frame).
        rec.add_key_value("x", str(site.x))
        rec.add_key_value("y", str(site.y))
        rec.add_key_value("reachM", str(site.reach.meters))
        rec.add_key_value("missRadiusM", str(site.miss_radius.meters))
        # The exact names Unit.getByName needs (TheaterUnit.unit_name, what the
        # generator stamps onto the .miz vehicle). UNITS, not groups: a jammer
        # shares its group with the rest of the site, so a group-level liveness
        # check would keep jamming after the jammer truck itself was killed.
        rec.add_data_array("units", list(site.unit_names))
