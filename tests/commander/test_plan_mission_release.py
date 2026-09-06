"""A plan that fails must give its aircraft back.

``plan_mission`` claims aircraft flight by flight. Anything that raises part-way
through used to leave those claims standing: the squadron read as fully committed to
a package that never existed, and nothing ever released it. The agent's dry-run
endpoint hit this every time it probed a task the target does not accept -- one bad
``/packages/evaluate`` and the squadron was grounded for the rest of the turn.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from game.commander import packagefulfiller
from game.commander.packagefulfiller import PackageFulfiller


def _fulfiller() -> PackageFulfiller:
    settings = MagicMock()
    return PackageFulfiller(MagicMock(), MagicMock(), MagicMock(), settings)


def test_a_plan_that_raises_releases_its_aircraft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = MagicMock()
    monkeypatch.setattr(
        packagefulfiller, "PackageBuilder", lambda *args, **kwargs: builder
    )
    monkeypatch.setattr(packagefulfiller, "ObjectiveDistanceCache", MagicMock())

    fulfiller = _fulfiller()

    def explode(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("this target does not accept that task")

    monkeypatch.setattr(fulfiller, "air_wing_can_plan", lambda task: True)
    monkeypatch.setattr(fulfiller, "plan_flight", explode)

    proposed = MagicMock()
    proposed.escort_type = None
    mission = MagicMock()
    mission.flights = [proposed]

    with pytest.raises(RuntimeError):
        fulfiller.plan_mission(mission, 1, datetime(2026, 9, 4, 12, 0), MagicMock())

    builder.release_planned_aircraft.assert_called_once_with()


def test_a_plan_that_succeeds_keeps_its_aircraft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The claim is the point of a successful plan; only failure gives it back."""
    builder = MagicMock()
    builder.package.flights = []
    monkeypatch.setattr(
        packagefulfiller, "PackageBuilder", lambda *args, **kwargs: builder
    )
    monkeypatch.setattr(packagefulfiller, "ObjectiveDistanceCache", MagicMock())

    fulfiller = _fulfiller()
    mission = MagicMock()
    mission.flights = []

    assert (
        fulfiller.plan_mission(mission, 1, datetime(2026, 9, 4, 12, 0), MagicMock())
        is None
    )
    builder.release_planned_aircraft.assert_not_called()
