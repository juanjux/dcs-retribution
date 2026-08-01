"""Wiring checks for the cruise missile strikes plugin.

The plugin's Lua only ever runs inside DCS, so these pin the seams Python owns: the
plugin is registered and injected, its runtime file exists, and the base script both
declares the ``cruise_missiles_state`` channel and writes it into the debrief -- without
which the turn-boundary magazine debit silently never happens.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from dcs import Mission

from game import Game
from game.missiongenerator.luagenerator import LuaGenerator
from game.missiongenerator.missiondata import MissionData
from game.plugins import LuaPluginManager
from game.plugins.luaplugin import LuaPlugin

BASE_SCRIPT = Path("resources/plugins/base/dcs_retribution.lua")


def _plugin() -> LuaPlugin:
    return next(
        p
        for p in LuaPluginManager.plugins()
        if p.definition.identifier == "cruisemissiles"
    )


def test_plugin_is_registered_and_its_runtime_file_exists() -> None:
    plugin = _plugin()
    files = [work_order.filename for work_order in plugin.definition.config_work_orders]
    assert files == ["cruisemissiles-config.lua"]
    assert Path("resources/plugins/cruisemissiles", files[0]).exists()


def test_plugin_configuration_is_injected() -> None:
    mission = Mission()
    # inject_plugins only touches self.mission and self.plugin_scripts, so the game and
    # mission_data arguments are unused here.
    generator = LuaGenerator(cast(Game, None), mission, cast(MissionData, None))

    generator.inject_plugins()

    assert "cruisemissiles-config" in generator.plugin_scripts


def test_base_script_declares_and_writes_the_state_channel() -> None:
    script = BASE_SCRIPT.read_text(encoding="utf-8")
    assert "cruise_missiles_state = {}" in script
    assert '["cruise_missiles_state"] = cruise_missiles_state' in script
