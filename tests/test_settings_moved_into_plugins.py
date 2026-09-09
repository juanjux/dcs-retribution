"""Settings that became plugin options have to carry an old save's values with them.

Every one of these plugins ships enabled, and the plugin's own switch is the only gate
now, so a campaign that had the feature switched OFF would load with it ON if nothing
carried the old value across. The numbers are worse than the switches: a reach or a
radius silently reverting to the default changes a campaign nobody thought they had
touched.
"""

from __future__ import annotations

from typing import Any

from game.settings import Settings


def _migrated(state: dict[str, Any]) -> dict[str, Any]:
    plugins: dict[str, Any] = Settings.deserialize_state_dict(state)["plugins"]
    return plugins


def test_a_switch_that_was_off_stays_off() -> None:
    plugins = _migrated({"cruise_missile_strikes": False, "plugins": {}})
    assert plugins["cruisemissiles"] is False


def test_a_switch_that_was_on_needs_its_plugin_too() -> None:
    """The feature used to run only when the setting AND the plugin were on."""
    assert _migrated({"naval_magazines": True, "plugins": {"navalmagazines": True}})[
        "navalmagazines"
    ]
    assert not _migrated(
        {"naval_magazines": True, "plugins": {"navalmagazines": False}}
    )["navalmagazines"]


def test_the_numbers_come_across_unchanged() -> None:
    plugins = _migrated(
        {
            "gps_jamming_default_reach_nm": 45.0,
            "gps_jamming_miss_radius_m": 500.0,
            "perf_skynet_iads_radius": 250,
            "plugins": {},
        }
    )
    assert plugins["gpsjamming.defaultReachNm"] == 45.0
    assert plugins["gpsjamming.missRadiusM"] == 500.0
    assert plugins["skynetiads.radiusKm"] == 250


def test_a_save_that_never_had_them_is_left_alone() -> None:
    assert _migrated({"plugins": {"cruisemissiles": True}}) == {"cruisemissiles": True}


def test_every_removed_setting_is_accounted_for() -> None:
    """A field dropped without an entry here is a value silently lost on load."""
    for setting, option in Settings._MOVED_INTO_PLUGINS.items():
        assert not hasattr(Settings(), setting), f"{setting} still exists"
        assert option, setting
