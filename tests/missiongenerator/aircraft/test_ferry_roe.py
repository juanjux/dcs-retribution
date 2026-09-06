"""A ferry flight must be allowed to shoot back.

It used to fly on WeaponHold, which in DCS means hold fire unconditionally -- with
EvadeFire it would jink away from a missile all the way into the ground without ever
firing at the fighter that launched it. A squadron relocating through contested
airspace was a free kill, and arming the flight changed nothing.

This is upstream code and a one-word change, so it is the kind of thing a sync
silently reverts. Hence the test.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from dcs.task import Nothing, OptROE

from game.ato.flighttype import FlightType
from game.missiongenerator.aircraft.aircraftbehavior import AircraftBehavior


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """The kwargs configure_ferry hands to configure_behavior."""
    seen: dict[str, Any] = {}

    def fake(self: Any, flight: Any, group: Any, **kwargs: Any) -> None:
        seen.update(kwargs)

    monkeypatch.setattr(AircraftBehavior, "configure_behavior", fake)
    return seen


def _ferry(captured: dict[str, Any]) -> Any:
    mission_data: Any = SimpleNamespace()
    group: Any = SimpleNamespace(task=None)
    flight: Any = SimpleNamespace()
    AircraftBehavior(FlightType.FERRY, mission_data).configure_ferry(group, flight)
    return group


def test_a_ferry_may_return_fire(captured: dict[str, Any]) -> None:
    _ferry(captured)
    assert captured["roe"] == OptROE.Values.ReturnFire
    assert captured["roe"] != OptROE.Values.WeaponHold


def test_a_ferry_still_flies_a_transit_not_a_patrol(captured: dict[str, Any]) -> None:
    """ReturnFire only lets it answer; the Nothing task is what keeps it from going
    hunting and abandoning the relocation."""
    group = _ferry(captured)
    assert group.task == Nothing.name
    assert captured["rtb_on_bingo"] is False
