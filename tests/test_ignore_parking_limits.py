"""Ignoring parking has to reach everything that gates on it, and stop at the sea.

Buying, auto-procurement, relocating a squadron and starting a campaign full all ask
ControlPoint.unclaimed_parking, so that is where the setting answers. A carrier is
excluded on purpose: its deck is the thing being modelled, not a shortage of concrete.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from game.theater.controlpoint import Airfield, Carrier, ControlPoint, ParkingType

PARKING = ParkingType(fixed_wing=True, fixed_wing_stol=True, rotary_wing=True)


def _control_point(kind: type[ControlPoint], *, ignoring: bool) -> ControlPoint:
    control_point = object.__new__(kind)
    coalition = MagicMock()
    coalition.game.settings.ignore_parking_limits = ignoring
    # coalition is a read-only property over _coalition.
    control_point._coalition = coalition
    return control_point


def test_an_airbase_holds_whatever_you_can_pay_for() -> None:
    airfield = _control_point(Airfield, ignoring=True)
    with patch.object(Airfield, "total_aircraft_parking", return_value=4), patch.object(
        Airfield, "allocated_aircraft"
    ) as allocated:
        allocated.return_value.total = 40
        assert airfield.unclaimed_parking(PARKING) > 0


def test_the_ramp_still_counts_while_the_setting_is_off() -> None:
    airfield = _control_point(Airfield, ignoring=False)
    with patch.object(Airfield, "total_aircraft_parking", return_value=4), patch.object(
        Airfield, "allocated_aircraft"
    ) as allocated:
        allocated.return_value.total = 40
        assert airfield.unclaimed_parking(PARKING) == -36


def test_a_carrier_deck_is_not_concrete() -> None:
    carrier = _control_point(Carrier, ignoring=True)
    with patch.object(Carrier, "total_aircraft_parking", return_value=4), patch.object(
        Carrier, "allocated_aircraft"
    ) as allocated:
        allocated.return_value.total = 40
        assert carrier.unclaimed_parking(PARKING) == -36
