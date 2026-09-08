"""Unit tests for the pool of pilots a squadron will offer for a sortie.

The pool is a stored list, rebuilt from the roster only between turns, so anything that
claims a pilot and then loses track of him leaves a man who is Active, unhurt and in
nobody's flight but cannot be given a seat. His record says one thing and the list says
another, and from outside there is no way to tell which is wrong -- which is exactly how
it was reported, with the API answering "he is dead, wounded, on leave or already flying
something else" about a pilot at 86 morale who was none of those.

Two defences: the claim paths compare by identity, because Pilot is a dataclass and two
men with the same record are equal to one another; and the list is checked against the
roster rather than trusted.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.settings import Settings
from game.squadrons.pilot import Pilot, PilotStatus


def _squadron(morale: bool = False) -> Any:
    from game.squadrons.squadron import Squadron

    settings = Settings()
    settings.live_pilots_enabled = True
    settings.morale_enabled = morale

    squadron: Any = Squadron.__new__(Squadron)
    squadron.settings = settings
    squadron.name = "Lucky Tang"
    squadron.nickname = None  # __str__ reads it, and the refusal names the squadron
    squadron.current_roster = []
    squadron.available_pilots = []
    squadron.coalition = SimpleNamespace(
        player=SimpleNamespace(is_blue=False), game=SimpleNamespace(turn=11)
    )
    return squadron


def _pilot(squadron: Any, name: str, available: bool = True) -> Pilot:
    pilot = Pilot(name)
    squadron.current_roster.append(pilot)
    if available:
        squadron.available_pilots.append(pilot)
    return pilot


def test_claiming_a_copy_does_not_strike_the_original_off() -> None:
    """Pilot is a dataclass: a copy of a man compares equal to him.

    list.remove takes the first equal entry, so claiming the copy used to take the
    original off the list -- leaving a pilot who reads Active and unassigned and can
    never be given a seat.
    """
    squadron = _squadron()
    original = _pilot(squadron, "Kevin Byrd")
    copy = Pilot("Kevin Byrd")
    assert copy == original, "the premise: they compare equal"

    with pytest.raises(ValueError):
        squadron.claim_pilot(copy)

    assert any(p is original for p in squadron.available_pilots)


def test_a_pilot_is_claimed_once_and_returned_once() -> None:
    squadron = _squadron()
    pilot = _pilot(squadron, "Byrd")

    squadron.claim_pilot(pilot)
    assert squadron.available_pilots == []

    squadron.return_pilot(pilot)
    squadron.return_pilot(pilot)
    assert len(squadron.available_pilots) == 1, "returning twice is not two pilots"


def test_a_fit_unassigned_pilot_who_fell_off_the_list_is_put_back() -> None:
    """The reported symptom, and the defence against every way of causing it."""
    squadron = _squadron()
    lost = _pilot(squadron, "Kevin Byrd", available=False)
    _pilot(squadron, "David Hayes")

    restored = squadron.reconcile_available_pilots(flying=set())

    assert [p.name for p in restored] == ["Kevin Byrd"]
    assert any(p is lost for p in squadron.available_pilots)


def test_a_pilot_in_a_seat_is_left_off_it() -> None:
    squadron = _squadron()
    flying = _pilot(squadron, "Ryan Hayes", available=False)

    restored = squadron.reconcile_available_pilots(flying={id(flying)})

    assert restored == []
    assert squadron.available_pilots == []


@pytest.mark.parametrize(
    "status", [PilotStatus.Dead, PilotStatus.Wounded, PilotStatus.OnLeave]
)
def test_the_unfit_are_not_put_back(status: PilotStatus) -> None:
    squadron = _squadron()
    pilot = _pilot(squadron, "Byrd", available=False)
    pilot.status = status

    assert squadron.reconcile_available_pilots(flying=set()) == []


def test_a_man_at_rock_bottom_is_not_put_back_while_morale_is_on() -> None:
    """He is on the books and counts against the establishment, but is not offered."""
    squadron = _squadron(morale=True)
    pilot = _pilot(squadron, "Byrd", available=False)
    pilot.morale = 0

    assert pilot.refuses_to_fly
    assert squadron.reconcile_available_pilots(flying=set()) == []


def test_reconciling_twice_does_not_duplicate_anyone() -> None:
    squadron = _squadron()
    _pilot(squadron, "Byrd", available=False)

    squadron.reconcile_available_pilots(flying=set())
    squadron.reconcile_available_pilots(flying=set())

    assert len(squadron.available_pilots) == 1
