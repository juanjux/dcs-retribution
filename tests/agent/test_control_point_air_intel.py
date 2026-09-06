"""A control point reports the aircraft based there, grouped by role.

Parity: the human opens a base and reads "CAP: F-16CM x7, F-5E x2 / CAS: AH-64D x6"
on its Intel tab. Without the same breakdown the planner sees only a squadron count
and cannot tell a fighter wing worth an OCA package from a couple of transports.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.agent import views


class _Aircraft:
    """Hashable stand-in for AircraftType: it is used as a dict key."""

    def __init__(self, display_name: str, task: str) -> None:
        self.display_name = display_name
        self.dcs_unit_type = SimpleNamespace(task_default=SimpleNamespace(name=task))


def _aircraft(display_name: str, task: str) -> Any:
    return _Aircraft(display_name, task)


def _cp(present: dict[Any, int]) -> Any:
    return SimpleNamespace(
        allocated_aircraft=lambda _parking: SimpleNamespace(present=present)
    )


def test_groups_present_aircraft_by_role() -> None:
    viper = _aircraft("F-16CM Fighting Falcon (Block 50)", "CAP")
    tiger = _aircraft("F-5E Tiger II", "CAP")
    apache = _aircraft("AH-64D Apache Longbow", "CAS")

    air = views._air_intel(_cp({viper: 7, tiger: 2, apache: 6}))

    assert air == {
        "CAP": {"F-16CM Fighting Falcon (Block 50)": 7, "F-5E Tiger II": 2},
        "CAS": {"AH-64D Apache Longbow": 6},
    }


def test_zero_counts_are_dropped() -> None:
    """An empty squadron is not aircraft on the field, and the payload is per-turn."""
    viper = _aircraft("F-16CM", "CAP")
    empty = _aircraft("KC-135", "Refueling")

    assert views._air_intel(_cp({viper: 3, empty: 0})) == {"CAP": {"F-16CM": 3}}


def test_empty_base_reports_nothing() -> None:
    assert views._air_intel(_cp({})) is None


def test_a_control_point_without_parking_is_not_an_error() -> None:
    """Off-map spawns and the like cannot allocate aircraft; that is not a failure."""

    def _raise(_parking: Any) -> Any:
        raise AttributeError("no parking here")

    assert views._air_intel(SimpleNamespace(allocated_aircraft=_raise)) is None
