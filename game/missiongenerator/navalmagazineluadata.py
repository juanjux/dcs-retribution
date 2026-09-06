"""Cross-turn naval magazines -> Lua config bridge (``dcsRetribution.navalMagazines``).

The emitter. Python owns the campaign side (the persisted per-group
anti-ship stock — ``game/naval_magazines``); this hands the
``navalmagazines`` plugin:

* ``stagger`` — N1's weapons-release switch. When on, the generator has already
  spawned every ship ``ReturnFire`` (``TgoGenerator.set_ship_engagement``) and
  the plugin releases each group to weapons-free at its own moment inside the
  window, so the exchange develops instead of detonating at t=0.
* ``magazines`` — N2's per-group stock: ``group``/``coalition``/``remaining``
  anti-ship missiles. The plugin counts real ``S_EVENT_SHOT`` releases and drops
  a spent group back to ``ReturnFire``.

The plugin mirrors what actually fired into the ``naval_magazines_state``
debrief channel; the turn boundary debits from that report, never from this
emit — so re-generating the mission is free.

Emits nothing unless at least one tier is enabled and a live naval group
exists, so a normal mission carries no ``navalMagazines`` node and the plugin
no-ops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData


def populate_naval_magazines_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.navalMagazines`` subtree."""
    settings = game.settings
    stagger = bool(getattr(settings, "naval_weapon_release_stagger", False))
    metered = bool(getattr(settings, "naval_magazines", False))
    if not (stagger or metered):
        return

    from game.naval_magazines import naval_group_magazines

    groups = naval_group_magazines(game)
    if not groups:
        return

    node = root.add_item("navalMagazines")
    node.add_key_value("stagger", "true" if stagger else "false")
    node.add_key_value("metered", "true" if metered else "false")
    group_list = node.add_item("magazines")
    for group in groups:
        rec = group_list.add_item()
        # The exact name Group.getByName needs (TheaterGroup.group_name, what the
        # generator stamps onto the .miz ship group).
        rec.add_key_value("group", group.group_name)
        rec.add_key_value("coalition", group.coalition)
        rec.add_key_value("remaining", str(group.remaining))
