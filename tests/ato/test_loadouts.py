from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.dcs.payload_loading import install_resilient_payload_loading


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


_GOOD_PAYLOAD = """\
local unitPayloads = {
\t["name"] = "ResilientTestJet",
\t["payloads"] = {
\t\t[1] = {
\t\t\t["name"] = "Good Loadout",
\t\t\t["pylons"] = {
\t\t\t\t[1] = { ["CLSID"] = "{GOOD-WEAPON}", ["num"] = 1 },
\t\t\t},
\t\t\t["tasks"] = { [1] = 31 },
\t\t},
\t},
\t["unitType"] = "ResilientTestJet",
}
return unitPayloads
"""

# Mirrors a hand-written mod payload that pydcs' minimal Lua reader chokes on:
# a numeric field that resolves to an empty token (the real-world
# "could not convert string to float: ''").
_BAD_PAYLOAD = """\
local unitPayloads = {
\t["name"] = "ResilientTestJet",
\t["payloads"] = {
\t\t[1] = {
\t\t\t["name"] = "Bad Loadout",
\t\t\t["pylons"] = {
\t\t\t\t[1] = { ["CLSID"] = "{BAD-WEAPON}", ["num"] = - },
\t\t\t},
\t\t\t["tasks"] = { [1] = 31 },
\t\t},
\t},
\t["unitType"] = "ResilientTestJet",
}
return unitPayloads
"""


def test_load_payloads_skips_unparseable_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One unparseable payload file must not hide the rest for an airframe.

    A hand-written mod payload file makes pydcs raise while parsing it (here a
    numeric field that resolves to an empty token). The resilient loader should
    skip just
    that file and still return every payload it can read -- e.g. the user's
    own Mission-Editor-saved loadouts.
    """
    from dcs import lua
    from dcs.payloads import PayloadDirectories
    from dcs.unittype import FlyingType

    (tmp_path / "good.lua").write_text(_GOOD_PAYLOAD, encoding="utf-8")
    (tmp_path / "bad.lua").write_text(_BAD_PAYLOAD, encoding="utf-8")

    # Sanity check: the bad file really is unparseable by pydcs, so the test
    # actually exercises the skip path rather than passing trivially.
    with pytest.raises(Exception):
        lua.loads(_BAD_PAYLOAD)

    class _ResilientTestType(FlyingType):
        id = "ResilientTestJet"
        payloads = None

    # Isolate pydcs from the real payload directories and its global scan cache.
    monkeypatch.setattr(
        PayloadDirectories, "payload_dirs", classmethod(lambda cls: iter([tmp_path]))
    )
    monkeypatch.setattr(FlyingType, "_payload_cache", None)

    install_resilient_payload_loading()
    payloads = _ResilientTestType.load_payloads()

    assert set(payloads) == {"Good Loadout"}
