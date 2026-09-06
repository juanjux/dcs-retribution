"""Sending a CAS flight higher than it fights from is worth a word of warning.

Not a refusal: flying high is how a flight stays out of MANPADS, and there is no
altitude that both avoids them and lets every pilot attack. The caller decides.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.agent.planner import _too_high_to_attack
from game.ato import FlightType
from game.utils import meters


def _flight(task: FlightType, planned_m: int) -> Any:
    return SimpleNamespace(
        flight_type=task,
        unit_type=SimpleNamespace(preferred_combat_altitude=meters(planned_m)),
    )


def test_above_what_the_aircraft_fights_from_earns_a_warning() -> None:
    warning = _too_high_to_attack(_flight(FlightType.CAS, 2134), 5000)
    assert "WARNING" in warning
    assert "5000 m" in warning and "2134 m" in warning


def test_at_or_below_it_says_nothing() -> None:
    assert _too_high_to_attack(_flight(FlightType.CAS, 2134), 2134) == ""
    assert _too_high_to_attack(_flight(FlightType.BAI, 2134), 900) == ""


@pytest.mark.parametrize(
    "task", [FlightType.STRIKE, FlightType.BARCAP, FlightType.SEAD]
)
def test_only_the_tasks_that_loiter_over_the_target_are_warned_about(
    task: FlightType,
) -> None:
    """A strike releasing from height is doing what it is supposed to."""
    assert _too_high_to_attack(_flight(task, 2134), 9000) == ""
