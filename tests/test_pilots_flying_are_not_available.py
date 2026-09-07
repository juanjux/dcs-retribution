"""The pool of pilots on offer has to agree with the roster and the ATO.

It is a stored list, rebuilt from the roster only between turns, so anything that moved
a man during one used to leave it wrong in one of two ways.

Too many: clearing a roster handed its crew back without letting go of them, so a pilot
was in a flight and in the pool at once -- the Edit Flight dropdown listed him twice and
the next flight could claim him again.

Too few: sending a man on leave did not take him out of the pool and bringing him back
did not return him, so every claim after that spent somebody else's place. A squadron
rested down to four pilots ended the turn offering none of them, and the two still fit
to fly could not be picked for anything.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.migrator import Migrator
from game.squadrons.pilot import Pilot, PilotStatus


def _squadron(available: list[Pilot], roster: list[Pilot] | None = None) -> Any:
    """A squadron only as far as the pool reconciliation looks into one."""
    pilots = list(available) if roster is None else list(roster)
    return SimpleNamespace(
        available_pilots=list(available),
        active_pilots=[p for p in pilots if p.status is PilotStatus.Active],
        morale_in_play=True,
    )


def _game(squadron: Any, flights: list[Any]) -> Any:
    coalition = SimpleNamespace(
        ato=SimpleNamespace(packages=[SimpleNamespace(flights=flights)]),
        air_wing=SimpleNamespace(iter_squadrons=lambda: iter([squadron])),
    )
    empty = SimpleNamespace(
        ato=SimpleNamespace(packages=[]),
        air_wing=SimpleNamespace(iter_squadrons=lambda: iter([])),
    )
    return SimpleNamespace(blue=coalition, red=empty)


def _run(squadron: Any, flights: list[Any]) -> None:
    migrator: Any = Migrator.__new__(Migrator)
    migrator.game = _game(squadron, flights)
    migrator._reconcile_available_pilots()


def test_a_pilot_who_is_flying_is_taken_out_of_the_pool() -> None:
    jefe, yayo, spare = Pilot("El Jefe"), Pilot("Yayo"), Pilot("Abascal")
    squadron = _squadron([jefe, yayo, spare])
    flight = SimpleNamespace(
        roster=SimpleNamespace(iter_pilots=lambda: iter([jefe, yayo]))
    )

    _run(squadron, [flight])

    assert [p.name for p in squadron.available_pilots] == ["Abascal"]


def test_a_pilot_listed_twice_is_listed_once() -> None:
    spare = Pilot("Abascal")
    squadron = _squadron([spare, spare])

    _run(squadron, [])

    assert squadron.available_pilots == [spare]


def test_a_clean_squadron_is_left_alone() -> None:
    pilots = [Pilot("Abascal"), Pilot("Fermin")]
    squadron = _squadron(list(pilots))

    _run(squadron, [])

    assert squadron.available_pilots == pilots


def test_a_fit_pilot_who_fell_out_of_the_pool_is_put_back() -> None:
    """The Apache squadron: rested down to four, offering none of them."""
    flying, idle = Pilot("Patrick Duran"), Pilot("Daniel Woods")
    resting = Pilot("Evan Davis")
    resting.send_on_leave()
    squadron = _squadron([], roster=[flying, idle, resting])
    flight = SimpleNamespace(roster=SimpleNamespace(iter_pilots=lambda: iter([flying])))

    _run(squadron, [flight])

    assert [p.name for p in squadron.available_pilots] == ["Daniel Woods"]


def test_the_ones_already_right_keep_their_order() -> None:
    first, second, missing = Pilot("Fermin"), Pilot("Yayo"), Pilot("Abascal")
    squadron = _squadron([first, second], roster=[first, second, missing])

    _run(squadron, [])

    assert [p.name for p in squadron.available_pilots] == ["Fermin", "Yayo", "Abascal"]


def test_a_man_who_will_not_fly_is_not_offered() -> None:
    steady, broken = Pilot("Fermin"), Pilot("Thomasz")
    broken.morale = 0
    squadron = _squadron([steady, broken])

    _run(squadron, [])

    assert [p.name for p in squadron.available_pilots] == ["Fermin"]


def test_with_morale_off_even_the_broken_are_offered() -> None:
    """The figure means nothing when the campaign is not playing that game."""
    steady, broken = Pilot("Fermin"), Pilot("Thomasz")
    broken.morale = 0
    squadron = _squadron([steady, broken])
    squadron.morale_in_play = False

    _run(squadron, [])

    assert [p.name for p in squadron.available_pilots] == ["Fermin", "Thomasz"]
