"""Tests for front-anchored support (AEW&C / tanker) orbit placement."""

from __future__ import annotations

import math
from types import SimpleNamespace

from game.ato.flightplans.supportorbit import support_orbit_anchor
from game.utils import Distance, meters, nautical_miles


class FakePoint:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def heading_between_point(self, other: "FakePoint") -> float:
        return math.degrees(math.atan2(other.y - self.y, other.x - self.x)) % 360

    def point_from_heading(self, heading: float, distance: float) -> "FakePoint":
        rad = math.radians(heading)
        return FakePoint(
            self.x + math.cos(rad) * distance, self.y + math.sin(rad) * distance
        )

    def distance_to_point(self, other: "FakePoint") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


class HalfPlaneThreat:
    """Enemy threat = everything with x > threshold (toward the enemy side)."""

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def threatened(self, p: FakePoint) -> bool:
        return p.x > self.threshold

    def distance_to_threat(self, p: FakePoint) -> Distance:
        return meters(abs(p.x - self.threshold))

    def closest_boundary(self, p: FakePoint) -> FakePoint:
        return FakePoint(self.threshold, p.y)


def _theater_with_front() -> tuple[SimpleNamespace, SimpleNamespace]:
    # FLOT centered at origin; blue to the west (-x), red to the east (+x).
    front = SimpleNamespace(
        position=FakePoint(0.0, 0.0),
        blue_cp=SimpleNamespace(position=FakePoint(-100_000, 0.0)),
        red_cp=SimpleNamespace(position=FakePoint(+100_000, 0.0)),
    )
    return SimpleNamespace(conflicts=lambda: iter([front])), front


def test_blue_support_sits_on_blue_side_clear_of_threat() -> None:
    theater, _ = _theater_with_front()
    # Enemy (red) threat spills 30 km onto the blue side of the FLOT.
    threat = HalfPlaneThreat(threshold=-30_000)
    buffer = nautical_miles(80)
    target = SimpleNamespace(position=FakePoint(-100_000, 0.0))

    center, _heading = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=True), threat, target, buffer  # type: ignore[arg-type]
    )

    assert center.x < 0  # blue (friendly) side of the FLOT
    assert abs(center.y) < 1  # centered laterally on the front
    assert not threat.threatened(center)  # type: ignore[arg-type]
    assert threat.distance_to_threat(center).meters >= buffer.meters - 1  # type: ignore[arg-type]


def test_red_support_sits_on_red_side_clear_of_threat() -> None:
    theater, _ = _theater_with_front()

    # Enemy (blue) threat spills onto the red side: threatened when x < +30 km.
    class RedSideThreat(HalfPlaneThreat):
        def threatened(self, p: FakePoint) -> bool:
            return p.x < self.threshold

    threat = RedSideThreat(threshold=+30_000)
    buffer = nautical_miles(70)
    target = SimpleNamespace(position=FakePoint(+100_000, 0.0))

    center, _heading = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=False), threat, target, buffer  # type: ignore[arg-type]
    )

    assert center.x > 0  # red (friendly) side of the FLOT
    assert abs(center.y) < 1
    assert not threat.threatened(center)  # type: ignore[arg-type]
    assert threat.distance_to_threat(center).meters >= buffer.meters - 1  # type: ignore[arg-type]


def test_no_front_falls_back_to_target_anchor() -> None:
    # No active front: anchor on the target, stood off from the threat boundary.
    theater = SimpleNamespace(conflicts=lambda: iter([]))
    threat = HalfPlaneThreat(threshold=-30_000)
    buffer = nautical_miles(80)
    target = SimpleNamespace(position=FakePoint(-100_000, 0.0))

    center, _heading = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=True), threat, target, buffer  # type: ignore[arg-type]
    )

    # Target is already clear; it should not be dragged into the threat.
    assert not threat.threatened(center)  # type: ignore[arg-type]
