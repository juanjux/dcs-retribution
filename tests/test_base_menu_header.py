"""The base menu says what the base is and whether it works, before anything else.

The window used to state neither: the kind was inferred from which tabs turned up,
the owner from the colours, and the runway state was the tail of a paragraph of rich
text that also held the aircraft and the ground units.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any, cast

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app() -> Any:
    try:
        from PySide6.QtWidgets import QApplication
    except Exception as exc:  # pragma: no cover - no Qt on this machine
        pytest.skip(f"PySide6 unavailable: {exc}")
    yield QApplication.instance() or QApplication([])


def _cp(
    runway: Any = None,
    depots: tuple[int, int] | None = None,
    factory: bool = False,
) -> Any:
    objectives = []
    if depots is not None:
        alive, total = depots
        for index in range(total):
            objectives.append(SimpleNamespace(category="ammo", is_dead=index >= alive))
    if factory:
        objectives.append(SimpleNamespace(category="factory", is_dead=False))
    return SimpleNamespace(
        name="Creech",
        runway_status=runway,
        connected_objectives=objectives,
        captured=SimpleNamespace(is_blue=True),
    )


def _pills(cp: Any) -> list[str]:
    from qt_ui.windows.basemenu.header import BaseHeader

    header = BaseHeader.__new__(BaseHeader)
    header.cp = cp
    return [pill.text() for pill in BaseHeader.status_pills(header)]


def test_a_working_runway_says_so(qt_app: Any) -> None:
    cp = _cp(runway=SimpleNamespace(damaged=False, repair_turns_remaining=None))
    assert _pills(cp) == ["Runway operational"]


def test_a_runway_under_repair_says_how_long(qt_app: Any) -> None:
    """The number is the whole point: it decides whether to frag from here next turn."""
    cp = _cp(runway=SimpleNamespace(damaged=True, repair_turns_remaining=2))
    assert _pills(cp) == ["Runway damaged · repairs in 2"]


def test_a_damaged_runway_nobody_is_fixing_says_only_that(qt_app: Any) -> None:
    cp = _cp(runway=SimpleNamespace(damaged=True, repair_turns_remaining=None))
    assert _pills(cp) == ["Runway damaged"]


def test_the_ammo_depots_are_a_figure(qt_app: Any) -> None:
    cp = _cp(
        runway=SimpleNamespace(damaged=False, repair_turns_remaining=None),
        depots=(7, 9),
        factory=True,
    )
    assert _pills(cp) == [
        "Runway operational",
        "Ammo depots 7/9",
        "Factory producing",
    ]


def test_a_base_with_no_depots_and_no_factory_says_nothing_about_them(
    qt_app: Any,
) -> None:
    """Only what is there: a FOB with neither should not carry two empty pills."""
    cp = _cp(runway=SimpleNamespace(damaged=False, repair_turns_remaining=None))
    assert _pills(cp) == ["Runway operational"]


def test_a_dead_factory_is_not_producing(qt_app: Any) -> None:
    cp = _cp(runway=None)
    cp.connected_objectives = [SimpleNamespace(category="factory", is_dead=True)]
    assert _pills(cp) == []


def test_every_kind_of_base_is_named(qt_app: Any) -> None:
    """Stated rather than inferred from which tabs appeared."""
    from game.theater import ControlPoint, Fob
    from qt_ui.windows.basemenu.header import kind_of

    def fake(**kwargs: bool) -> ControlPoint:
        return cast(ControlPoint, SimpleNamespace(**kwargs))

    assert kind_of(fake(is_carrier=False, is_lha=False)) == "AIRBASE"
    assert kind_of(fake(is_carrier=True, is_lha=False)) == "CARRIER"
    assert kind_of(fake(is_carrier=False, is_lha=True)) == "LHA"

    # is_carrier and is_lha are properties on the real class, so a FOB stand-in
    # subclasses it rather than assigning over them.
    class _Fob(Fob):
        def __init__(self, pads: bool, spawns: bool) -> None:
            self.pads = pads
            self.spawns = spawns

        @property
        def is_carrier(self) -> bool:
            return False

        @property
        def is_lha(self) -> bool:
            return False

        @property
        def has_helipads(self) -> bool:
            return self.pads

        @property
        def has_ground_spawns(self) -> bool:
            return self.spawns

    assert kind_of(_Fob(pads=False, spawns=True)) == "FOB"
    assert kind_of(_Fob(pads=True, spawns=False)) == "HELIPORT"
