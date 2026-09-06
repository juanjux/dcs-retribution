"""A hold must never be told to release at a negative mission time.

Flight plans are built backwards from the package TOT, so a TOT the flights cannot
reach puts the push time before the mission starts and the hold's release timer goes
negative. That timer is emitted twice: as the orbit's stop-after-time, and as a mission
trigger (``TimeAfter``) that exists precisely because DCS's native stop-after-time is
unreliable. A trigger scheduled for a negative time never fires, so the flight can hold
for the entire mission.

Seen in the field: a DEAD package given TOT +5 min from a base ~29 min from the target
produced ``stopCondition.time = -865`` — the only negative time condition in the whole
mission file.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from dcs.task import ControlledTask

from game.missiongenerator.aircraft.waypoints.holdpoint import HoldPointBuilder


@pytest.fixture
def emitted(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Capture what the builder puts on the orbit and on the stop trigger."""
    seen: dict[str, Any] = {}

    def fake_stop_after_time(self: ControlledTask, seconds: int) -> None:
        seen["stop_after_time"] = seconds

    def fake_trigger(orbit: Any, group_id: int, mission: Any, elapsed: int) -> None:
        seen["trigger"] = elapsed

    monkeypatch.setattr(ControlledTask, "stop_after_time", fake_stop_after_time)
    monkeypatch.setattr(
        "game.missiongenerator.aircraft.waypoints.holdpoint.create_stop_orbit_trigger",
        fake_trigger,
    )
    return seen


def _build(push_offset_minutes: float, emitted: dict[str, Any]) -> dict[str, Any]:
    now = datetime(2030, 6, 2, 9, 0, 0)
    from game.ato.flightplans.loiter import LoiterFlightPlan

    # The builder gates on isinstance(flight_plan, LoiterFlightPlan), so the fake has to
    # really be one; dropping __abstractmethods__ lets it be built without the engine.
    class FakeLoiter(LoiterFlightPlan):
        def __init__(self, push: datetime) -> None:
            self._push = push

        @property
        def push_time(self) -> datetime:
            return self._push

    FakeLoiter.__abstractmethods__ = frozenset()
    plan: Any = FakeLoiter(now + timedelta(minutes=push_offset_minutes))  # type: ignore[abstract]
    flight: Any = SimpleNamespace(
        flight_plan=plan,
        is_helo=False,
        squadron=SimpleNamespace(
            aircraft=SimpleNamespace(
                preferred_patrol_speed=lambda alt: SimpleNamespace(kph=700)
            )
        ),
    )
    builder = HoldPointBuilder.__new__(HoldPointBuilder)
    builder.flight = flight
    builder.now = now
    dummy: Any = object()
    builder.package = dummy
    builder.mission = dummy
    # The trigger hotfix names the group by id now, so the stub needs one.
    group: Any = SimpleNamespace(id=1)
    builder.group = group
    waypoint: Any = SimpleNamespace(alt=6400, tasks=[], add_task=lambda t: None)
    builder.waypoint = waypoint
    builder.add_tasks(waypoint)
    return emitted


def test_a_push_time_before_the_mission_releases_at_zero(
    emitted: dict[str, Any],
) -> None:
    out = _build(-14.4, emitted)
    assert out["stop_after_time"] == 0
    assert out["trigger"] == 0


def test_a_normal_push_time_is_untouched(emitted: dict[str, Any]) -> None:
    """60 s of margin is subtracted, as before — only the clamp is new."""
    out = _build(30, emitted)
    assert out["stop_after_time"] == 30 * 60 - 60
    assert out["trigger"] == 30 * 60 - 60
