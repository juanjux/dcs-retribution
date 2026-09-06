"""A pilot in a cockpit is not available, whatever the save says.

Clearing a roster used to hand its crew back to the squadron without letting go of them,
so a pilot could be in a flight and in the pool at once: the Edit Flight dropdown listed
him twice, and the next flight could claim him again. The fault is fixed, but saves made
while it was live still carry the state -- five pilots in one campaign.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.migrator import Migrator
from game.squadrons.pilot import Pilot


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
    migrator._release_pilots_who_are_flying()


def test_a_pilot_who_is_flying_is_taken_out_of_the_pool() -> None:
    jefe, yayo, spare = Pilot("El Jefe"), Pilot("Yayo"), Pilot("Abascal")
    squadron = SimpleNamespace(available_pilots=[jefe, yayo, spare])
    flight = SimpleNamespace(
        roster=SimpleNamespace(iter_pilots=lambda: iter([jefe, yayo]))
    )

    _run(squadron, [flight])

    assert [p.name for p in squadron.available_pilots] == ["Abascal"]


def test_a_pilot_listed_twice_is_listed_once() -> None:
    spare = Pilot("Abascal")
    squadron = SimpleNamespace(available_pilots=[spare, spare])

    _run(squadron, [])

    assert squadron.available_pilots == [spare]


def test_a_clean_squadron_is_left_alone() -> None:
    pilots = [Pilot("Abascal"), Pilot("Fermin")]
    squadron = SimpleNamespace(available_pilots=list(pilots))

    _run(squadron, [])

    assert squadron.available_pilots == pilots
