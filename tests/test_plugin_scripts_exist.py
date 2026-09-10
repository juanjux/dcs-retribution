"""A plugin's manifest and the files beside it have to agree.

The injector logs a missing script and carries on, so a manifest naming a file that
is not there produces a mission that silently lacks part of a plugin.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PLUGINS = Path(__file__).resolve().parent.parent / "resources/plugins"


def _manifests() -> list[Path]:
    return sorted(PLUGINS.glob("*/plugin.json"))


def test_there_are_plugins_to_check() -> None:
    assert _manifests()


@pytest.mark.parametrize("manifest", _manifests(), ids=lambda p: p.parent.name)
def test_every_declared_script_is_on_disk(manifest: Path) -> None:
    declared = json.loads(manifest.read_text(encoding="utf-8"))
    for order in declared.get("scriptsWorkOrders", []):
        script = manifest.parent / order["file"]
        assert script.is_file(), f"{manifest.parent.name} declares {order['file']}"


def test_the_tick_profiler_is_off_by_default() -> None:
    """Its count hook is not free: a measurement run, never a campaign."""
    profiler = json.loads(
        (PLUGINS / "tickprofile/plugin.json").read_text(encoding="utf-8")
    )
    assert profiler["defaultValue"] is False


def test_the_tick_profiler_loads_before_the_plugins_it_measures() -> None:
    order = json.loads((PLUGINS / "plugins.json").read_text(encoding="utf-8"))
    assert order.index("tickprofile") < min(
        index for index, name in enumerate(order) if name not in {"base", "tickprofile"}
    )
