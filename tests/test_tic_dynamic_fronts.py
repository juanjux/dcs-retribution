"""Tests for the per-stance TIC (Troops In Contact) movement shaping.

`FlotGenerator._plan_tic_action` encodes orders as TIC waypoint NAMES
("t+N hdg=H roe=simulate"). These tests pin the design decisions from
docs/dev/design/414th-tic-dynamic-fronts-notes.md: stances produce distinct
firing-line postures (no symmetric wall), DEFENSIVE digs in with a forward
bound instead of idling at the rear spawn and only occasionally counterattacks,
and the leg cadence is staggered per group.

The full FlotGenerator constructor is heavy (Mission/Game/conflict), so we build
a bare instance via ``object.__new__`` and attach only the attributes
``_plan_tic_action`` touches, matching the duck-typed-fake style used elsewhere.
"""

from __future__ import annotations

import math
import random
from typing import List

import pytest
from dcs.point import PointAction

from game.ground_forces.combat_stance import CombatStance
from game.missiongenerator.flotgenerator import (
    FlotGenerator,
    TIC_AMBUSH_STANDOFF,
    TIC_CONTACT_STANDOFF,
    TIC_DEFENSIVE_STANDOFF,
    TIC_STANCE_PROFILES,
)
from game.utils import Heading

FORWARD = Heading.from_degrees(0)
FRONT_DISTANCE = 6000.0  # group -> trace, large enough that every stance bounds


class FakePoint:
    """Minimal stand-in for dcs.mapping.Point (which needs a terrain arg). Only
    the methods _plan_tic_action and its helpers call are implemented, and the
    trig matches pydcs so the geometry stays self-consistent."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def point_from_heading(self, heading: float, distance: float) -> "FakePoint":
        rad = math.radians(heading)
        return FakePoint(
            self.x + math.cos(rad) * distance, self.y + math.sin(rad) * distance
        )

    def distance_to_point(self, other: "FakePoint") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def random_point_within(
        self, max_distance: float, min_distance: float = 0
    ) -> "FakePoint":
        return self.point_from_heading(
            random.uniform(0, 360), random.uniform(min_distance, max_distance)
        )


class FakeWaypoint:
    def __init__(self, position: FakePoint) -> None:
        self.position = position
        self.name = ""


class FakeGroup:
    """Records waypoints added after the spawn point (points[0])."""

    def __init__(self, position: FakePoint) -> None:
        self.points = [FakeWaypoint(position)]
        self.added: List[FakeWaypoint] = []

    def add_waypoint(self, point: FakePoint, action: PointAction) -> FakeWaypoint:
        wp = FakeWaypoint(point)
        self.added.append(wp)
        return wp


class FakeTheater:
    @staticmethod
    def is_on_land(point: FakePoint) -> bool:
        return True

    @staticmethod
    def nearest_land_pos(point: FakePoint, extend_dist: int = 50) -> FakePoint:
        return point


class FakeConflict:
    def __init__(self, front: FakePoint) -> None:
        self.position = front
        self.theater = FakeTheater()


class FakeCp:
    def __init__(self, position: FakePoint) -> None:
        self.position = position


def make_generator(bound_pause: int = 25) -> FlotGenerator:
    gen = object.__new__(FlotGenerator)
    gen.tic_bound_pause = bound_pause
    gen.wpt_pointaction = PointAction.OffRoad
    spawn = FakePoint(0, 0)
    gen.conflict = FakeConflict(spawn.point_from_heading(FORWARD.degrees, FRONT_DISTANCE))  # type: ignore[assignment]
    return gen


def plan(stance: CombatStance, gen: FlotGenerator) -> FakeGroup:
    group = FakeGroup(FakePoint(0, 0))
    from_cp = FakeCp(FakePoint(0, 0))
    to_cp = FakeCp(FakePoint(0, FRONT_DISTANCE))
    gen._plan_tic_action(stance, group, FORWARD, from_cp, to_cp)  # type: ignore[arg-type]
    return group


def front_position() -> FakePoint:
    return FakePoint(0, 0).point_from_heading(FORWARD.degrees, FRONT_DISTANCE)


def leg_times(group: FakeGroup) -> List[int]:
    times = []
    for wp in group.added:
        assert wp.name.startswith("t+"), wp.name
        assert "roe=simulate" in wp.name
        times.append(int(wp.name.split()[0][2:]))
    return times


# --- Profile divergence (pure mapping) ---------------------------------------


def test_aggressive_stances_have_distinct_shapes() -> None:
    aggressive = TIC_STANCE_PROFILES[CombatStance.AGGRESSIVE]
    breakthrough = TIC_STANCE_PROFILES[CombatStance.BREAKTHROUGH]
    elimination = TIC_STANCE_PROFILES[CombatStance.ELIMINATION]

    # Breakthrough thrusts straight and deep, faster cadence.
    assert breakthrough.slide_before_press is False
    assert breakthrough.push_depth_scale > aggressive.push_depth_scale
    assert breakthrough.cadence_scale < aggressive.cadence_scale

    # Elimination hunts LOS with an extra slide/press cycle.
    assert elimination.assault_cycles > aggressive.assault_cycles
    assert aggressive.slide_before_press is True


def test_defenders_dig_in_behind_the_attacker_standoff() -> None:
    # Defensive/ambush halt deeper (further from the trace) than attackers, but
    # ambush is the most rearward.
    assert TIC_DEFENSIVE_STANDOFF[0] >= TIC_CONTACT_STANDOFF[1]
    assert TIC_AMBUSH_STANDOFF[0] >= TIC_DEFENSIVE_STANDOFF[1]

    assert TIC_STANCE_PROFILES[CombatStance.DEFENSIVE].assault_cycles == 0
    assert TIC_STANCE_PROFILES[CombatStance.AMBUSH].assault_cycles == 0
    assert TIC_STANCE_PROFILES[CombatStance.DEFENSIVE].counter_chance > 0
    assert TIC_STANCE_PROFILES[CombatStance.AMBUSH].counter_chance == 0


# --- Waypoint shape per stance ----------------------------------------------


def test_attacker_waypoint_counts_match_profile() -> None:
    random.seed(1)
    gen = make_generator()
    # opening bound + cycles. counter_chance is 0 for attackers, so counts are
    # deterministic regardless of rng.
    assert len(plan(CombatStance.AGGRESSIVE, gen).added) == 3  # bound + slide + press
    assert len(plan(CombatStance.BREAKTHROUGH, gen).added) == 2  # bound + press
    assert (
        len(plan(CombatStance.ELIMINATION, gen).added) == 5
    )  # bound + 2x(slide+press)


def test_defensive_emits_a_forward_bound_not_idle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    random.seed(0)
    gen = make_generator()
    # Suppress the occasional counterattack to isolate the opening bound.
    monkeypatch.setattr(random, "random", lambda: 1.0)
    group = plan(CombatStance.DEFENSIVE, gen)

    assert len(group.added) == 1
    spawn = group.points[0].position
    bound = group.added[0].position
    front = front_position()
    # The bound moves forward but stops short of the trace (inside the bubble).
    assert 0 < bound.distance_to_point(spawn) < front.distance_to_point(spawn)


def test_defensive_counterattacks_only_occasionally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    random.seed(0)
    gen = make_generator()

    # Force the counter roll to fire: bound + counterattack = 2 legs.
    monkeypatch.setattr(random, "random", lambda: 0.0)
    assert len(plan(CombatStance.DEFENSIVE, gen).added) == 2

    # Ambush never counterattacks even when the roll would fire.
    assert len(plan(CombatStance.AMBUSH, gen).added) == 1


def test_legs_are_time_ordered_and_staggered() -> None:
    random.seed(7)
    gen = make_generator()
    times = leg_times(plan(CombatStance.ELIMINATION, gen))
    # Every leg lands on a strictly later minute than the one before it.
    assert all(b > a for a, b in zip(times, times[1:]))


def test_retreat_still_emits_single_fallback_leg() -> None:
    random.seed(3)
    gen = make_generator()
    group = plan(CombatStance.RETREAT, gen)
    assert len(group.added) == 1
    assert group.added[0].name.startswith("t+0 ")


# --- Cadence helpers ---------------------------------------------------------


def test_step_off_window_scales_with_bound_pause() -> None:
    random.seed(0)
    gen = make_generator(bound_pause=40)
    for _ in range(200):
        assert 0 <= gen._tic_step_off() <= 20  # max(3, 40 // 2)

    small = make_generator(bound_pause=2)
    for _ in range(50):
        assert 0 <= small._tic_step_off() <= 3  # floor


def test_jitter_and_leg_gap_bounds() -> None:
    random.seed(0)
    gen = make_generator(bound_pause=20)
    for _ in range(200):
        assert 11 <= gen._tic_jitter() <= 29  # round(20*.55) .. round(20*1.45)
        assert gen._tic_leg_gap(0.7, 0.7) >= 1
