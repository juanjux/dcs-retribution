"""The Su-25 attacks from where the AI will actually shoot.

Left to the estimate made from its top speed, an Su-25 is planned to fight at 20,000 ft
and never opens fire. The ceiling is the pilot's: a cadet shoots from the deck to about
3,000 m and nothing above it, and Live Pilots starts every pilot as a cadet.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from game import persistency
from game.dcs.aircrafttype import AircraftType
from game.utils import feet, meters

#: What the planner adds or subtracts, at the default setting of 2.
OFFSET_FT = 2000

#: Above this a cadet flies over the target without attacking it. Measured in game.
CADET_CEILING = meters(3000)


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # AircraftType loads the unit data files, which reach for the saved-games folder.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16885)


@pytest.mark.parametrize("name", ["Su-25 Frogfoot", "Su-25T Frogfoot"])
def test_it_fights_where_a_cadet_will_shoot(name: str) -> None:
    aircraft = AircraftType.named(name)
    assert aircraft.combat_altitude is not None, "would fall back to the speed estimate"
    highest = feet(aircraft.combat_altitude.feet + OFFSET_FT)
    assert highest < CADET_CEILING, (
        f"{name} plans as high as {highest.feet:.0f} ft, and a cadet stops attacking "
        f"at {CADET_CEILING.feet:.0f} ft"
    )
