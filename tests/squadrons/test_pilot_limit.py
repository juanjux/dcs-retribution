"""Unit tests for who holds a place in a squadron.

The pilot limit is a limit on the establishment, not on who happens to be fit to fly
this turn. A wounded pilot and a pilot on leave are both coming back, so their places
are not free to recruit into; a man who is dead, deserted or discharged is gone and his
is.

Counting only the active and the wounded is how a squadron limited to sixteen reached
twenty-four with twelve men resting, and how one that merely backfilled a single absence
sat at seventeen the day he came back.
"""

from types import SimpleNamespace
from typing import Any

import pytest

from game.settings import Settings
from game.squadrons.pilot import Pilot, PilotStatus


def _squadron(limit: int = 16, rate: int = 4) -> Any:
    from game.squadrons.squadron import Squadron

    settings = Settings()
    settings.enable_squadron_pilot_limits = True
    settings.squadron_pilot_limit = limit
    settings.squadron_replenishment_rate = rate

    squadron: Any = Squadron.__new__(Squadron)
    squadron.settings = settings
    squadron.name = "Zero Company"
    squadron.current_roster = []
    squadron.coalition = SimpleNamespace(
        player=SimpleNamespace(is_blue=True), game=SimpleNamespace(turn=6)
    )
    return squadron


def _man(squadron: Any, status: PilotStatus) -> Pilot:
    pilot = Pilot(f"Pilot {len(squadron.current_roster)}")
    pilot.status = status
    squadron.current_roster.append(pilot)
    return pilot


def _fill(squadron: Any, **counts: int) -> Any:
    for name, count in counts.items():
        for _ in range(count):
            _man(squadron, PilotStatus[name])
    return squadron


@pytest.mark.parametrize(
    "status",
    [PilotStatus.Active, PilotStatus.Wounded, PilotStatus.OnLeave],
)
def test_a_man_still_on_the_books_holds_his_place(status: PilotStatus) -> None:
    """Whether he can fly this turn or not: he is coming back to it."""
    squadron = _fill(_squadron(limit=16), Active=15)
    _man(squadron, status)

    assert squadron.replenish_count == 0


@pytest.mark.parametrize(
    "status",
    [PilotStatus.Dead, PilotStatus.Deserted, PilotStatus.Discharged],
)
def test_a_man_who_is_gone_frees_his_place(status: PilotStatus) -> None:
    squadron = _fill(_squadron(limit=16), Active=15)
    _man(squadron, status)

    assert squadron.replenish_count == 1


def test_the_replenishment_rate_is_the_ceiling() -> None:
    """Eight places open, four a turn."""
    squadron = _fill(_squadron(limit=16, rate=4), Active=8)

    assert squadron.replenish_count == 4


def test_a_squadron_over_its_limit_recruits_nobody() -> None:
    """The Apache: twelve flying, twelve resting, a limit of sixteen.

    It used to read four free places and recruit into them. It comes back down on its
    own now as men are lost, rather than having anyone taken off it.
    """
    squadron = _fill(_squadron(limit=16), Active=12, OnLeave=12)

    assert squadron.replenish_count == 0


def test_being_over_the_limit_never_reads_as_a_shrinking_squadron() -> None:
    """A negative count would have told procurement the squadron was losing men."""
    squadron = _fill(_squadron(limit=16), Active=17)

    assert squadron.replenish_count == 0
    assert squadron.expected_pilots_next_turn == 17


def test_the_dead_do_not_hold_places_open_for_ever() -> None:
    """A long campaign accumulates them, and they must not squeeze the living out."""
    squadron = _fill(_squadron(limit=16), Active=10, Dead=30)

    assert squadron.replenish_count == 4
