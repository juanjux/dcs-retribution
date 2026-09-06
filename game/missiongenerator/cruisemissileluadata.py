"""Ship cruise missile strikes -> Lua config bridge (``dcsRetribution.cruiseMissiles``).

Python owns the campaign side of the feature (eligibility, the persisted per-group
magazines, the auto-raid target pick — :mod:`game.cruise_raids`); this emits, for the
``cruisemissiles`` plugin:

* ``ships`` — every live launching group with missiles left (``group``/``coalition``/
  ``remaining``), both sides. The plugin builds its F10 call-for-fire menu from these
  and treats ``remaining`` as this mission's hard expenditure cap per group, shared
  between the auto raid and any player salvos.
* ``raids`` — this turn's planned auto raids (at most one per side), each a
  ``group``/``x``/``y``/``count``/``target`` record the plugin fires at a random moment
  inside its launch window. ``x`` is north and ``y`` east: the pydcs planning frame,
  not the DCS vec3 the mission scripting API hands back.

The plugin mirrors what actually fired into the ``cruise_missiles_state`` debrief
channel, and the turn boundary debits the magazines from that report rather than from
this emit — so re-generating a mission is free.

Emits nothing unless the feature is on and a live launching group exists, so an ordinary
mission carries no ``cruiseMissiles`` node at all and the plugin no-ops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData


def populate_cruise_missiles_lua(root: LuaData, game: Game) -> None:
    """Build the ``dcsRetribution.cruiseMissiles`` subtree (ships + auto raids)."""
    if not game.settings.cruise_missile_strikes:
        return

    from game.cruise_raids import lacm_ships, plan_cruise_raids

    ships = lacm_ships(game)
    if not ships:
        return
    raids = plan_cruise_raids(game)

    node = root.add_item("cruiseMissiles")
    ship_list = node.add_item("ships")
    for ship in ships:
        rec = ship_list.add_item()
        # TheaterGroup.group_name is exactly what the TGO/carrier generators stamp onto
        # the .miz group, which is what the plugin's Group lookup needs.
        rec.add_key_value("group", ship.group_name)
        rec.add_key_value("coalition", ship.coalition)
        rec.add_key_value("remaining", str(ship.remaining))
    if raids:
        raid_list = node.add_item("raids")
        for raid in raids:
            rec = raid_list.add_item()
            rec.add_key_value("group", raid.group_name)
            rec.add_key_value("coalition", raid.coalition)
            rec.add_key_value("target", raid.target_name)
            rec.add_key_value("x", str(raid.target_x))
            rec.add_key_value("y", str(raid.target_y))
            rec.add_key_value("count", str(raid.missiles))
