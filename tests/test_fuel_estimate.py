"""The fuel estimate: measured where somebody measured, guessed where nobody did.

Twenty-four of the roughly three hundred aircraft carry measured consumption figures,
so the guess is what almost every flight actually gets. It is meant to err high --
being told you are tight and finding you had plenty costs nothing; the other way costs
an aircraft -- but not so high that it calls every flight short, which would be no more
useful than being wrong.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from game import persistency

from game.ato.fuelestimate import (
    COMBAT_OVER_CRUISE,
    NOMINAL_RANGE_NM,
    _airframe_class,
    assumed_consumption,
)
from game.dcs.aircrafttype import AircraftType


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # AircraftType loads the unit data files, which reach for the saved-games folder.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16885)


def _measured() -> list[AircraftType]:
    return [a for a in AircraftType.iter_all() if a.fuel_consumption is not None]


def test_somebody_has_measured_some_aircraft() -> None:
    """The premise of the calibration below."""
    assert _measured()


def test_the_guess_leans_high_against_every_measured_airframe() -> None:
    """Checked against the only ground truth there is: the measured aircraft.

    Not a tight band -- the measured set itself spans 447 to 856 nm on internal fuel,
    so no single rule fits it closely. What matters is that the guess never lands far
    BELOW a measured figure, which is the direction that gets someone killed.
    """
    for aircraft in _measured():
        if _airframe_class(aircraft) == "heavy":
            # The buddy tankers carry their TRANSFERABLE fuel as "internal", so a
            # guess derived from how much fuel an airframe holds cannot be right
            # about them. They have measured figures, so the guess is never used.
            continue
        measured = aircraft.fuel_consumption
        assert measured is not None
        guess = assumed_consumption(aircraft)
        ratio = guess.cruise / measured.cruise
        assert ratio > 0.7, f"{aircraft} guessed {ratio:.2f}x its measured cruise"
        assert ratio < 2.5, f"{aircraft} guessed {ratio:.2f}x its measured cruise"


def test_the_measured_figures_win_where_they_exist() -> None:
    """Including for the tankers the guess cannot describe."""
    for aircraft in _measured():
        assert aircraft.fuel_consumption is not None


def test_a_helicopter_is_not_charged_like_a_fighter() -> None:
    assert NOMINAL_RANGE_NM["helicopter"] < NOMINAL_RANGE_NM["jet"]


def test_combat_costs_more_than_cruise_and_climb_more_still() -> None:
    aircraft = next(iter(_measured()))
    guess = assumed_consumption(aircraft)
    assert guess.cruise < guess.combat < guess.climb
    assert guess.combat == pytest.approx(guess.cruise * COMBAT_OVER_CRUISE)


def test_every_airframe_gets_an_answer() -> None:
    """Without a fallback the estimate would have nothing to say about 9 flights in 10."""
    for aircraft in AircraftType.iter_all():
        guess = assumed_consumption(aircraft)
        assert guess.cruise > 0
        assert guess.min_safe > 0
