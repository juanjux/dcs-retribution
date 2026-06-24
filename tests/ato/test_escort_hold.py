"""Tests for the escort-hold placement of EscortFlightPlan.Builder.

An escort tasked to protect an AWACS or tanker must hold on that flight's
racetrack orbit, which is stationed far from the package's target reference.
``_racetrack_hold_point`` returns the racetrack center for such (patrolling)
primaries and ``None`` for everything else (where the default target-relative
escort-hold geometry is used).
"""

from types import SimpleNamespace

from dcs.mapping import Point

from game.ato.flightplans.escort import Builder
from game.ato.flightplans.patrolling import PatrollingLayout


def _patrolling_primary(start: Point, end: Point) -> SimpleNamespace:
    layout = object.__new__(PatrollingLayout)
    layout.patrol_start = SimpleNamespace(position=start)
    layout.patrol_end = SimpleNamespace(position=end)

    class _Plan:
        def is_patrol(self, _fp: object) -> bool:
            return True

        @property
        def layout(self) -> PatrollingLayout:
            return layout

    return SimpleNamespace(flight_plan=_Plan())


def test_hold_anchors_on_racetrack_center_for_patrolling_primary() -> None:
    primary = _patrolling_primary(Point(100000, 0, None), Point(100000, 60000, None))

    hold = Builder._racetrack_hold_point(primary)

    assert hold is not None
    assert hold.x == 100000
    assert hold.y == 30000


def test_no_racetrack_hold_for_non_patrolling_primary() -> None:
    class _Plan:
        def is_patrol(self, _fp: object) -> bool:
            return False

        @property
        def layout(self) -> object:
            raise AssertionError("layout must not be read for non-patrol primaries")

    primary = SimpleNamespace(flight_plan=_Plan())

    assert Builder._racetrack_hold_point(primary) is None


def test_no_racetrack_hold_without_primary_flight() -> None:
    assert Builder._racetrack_hold_point(None) is None
