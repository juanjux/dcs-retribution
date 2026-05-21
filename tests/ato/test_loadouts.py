from typing import Any
from unittest.mock import MagicMock

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout


def test_default_loadout_falls_back_when_payloads_fail_to_load() -> None:
    """A payload file that pydcs can't parse must not abort mission planning.

    Some third-party mods ship payload .lua files pydcs chokes on (e.g. a
    numeric field that ends up empty). load_payloads() then raises; the default
    loadout lookup should swallow that and return an empty loadout instead of
    letting the exception propagate through turn generation.
    """
    unit_type: Any = MagicMock()
    unit_type.id = "BrokenMod"
    unit_type.load_payloads.side_effect = ValueError(
        "could not convert string to float: ''"
    )

    loadout = Loadout.default_for_task_and_aircraft(FlightType.ANTISHIP, unit_type)

    assert loadout.name == "Empty"
    assert loadout.pylons == {}
