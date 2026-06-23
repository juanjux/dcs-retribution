from types import SimpleNamespace

from shapely.geometry import Point as ShapelyPoint

from game.commander.tasks.primitive.dead import PlanDead
from game.commander.theaterstate import TheaterState


def _flight(*xy: tuple[float, float]) -> SimpleNamespace:
    """A fake flight whose flight plan visits the given (x, y) waypoints."""
    waypoints = [SimpleNamespace(position=SimpleNamespace(x=x, y=y)) for x, y in xy]
    return SimpleNamespace(flight_plan=SimpleNamespace(waypoints=waypoints))


def _rings(
    *entries: tuple[object, float, float, float]
) -> list[tuple[object, ShapelyPoint, float]]:
    """(tgo, cx, cy, radius) -> the initial_radar_sam_rings shape."""
    return [(tgo, ShapelyPoint(cx, cy), radius) for tgo, cx, cy, radius in entries]


def test_dead_can_reach_true_when_route_avoids_other_sams() -> None:
    target = object()
    other = object()
    state = SimpleNamespace(
        initial_radar_sam_rings=_rings((target, 1000, 0, 50), (other, 0, 0, 100))
    )
    # Route runs well north of the `other` ring (200 m away from a 100 m ring).
    flights = [_flight((0, 200), (1000, 200))]
    assert TheaterState.dead_can_reach(state, target, flights) is True  # type: ignore[arg-type]


def test_dead_can_reach_false_when_route_crosses_another_sam() -> None:
    target = object()
    other = object()
    state = SimpleNamespace(
        initial_radar_sam_rings=_rings((target, 1000, 0, 50), (other, 0, 0, 100))
    )
    # Route drives straight through the `other` ring at (0, 0).
    flights = [_flight((-200, 0), (1000, 0))]
    assert TheaterState.dead_can_reach(state, target, flights) is False  # type: ignore[arg-type]


def test_dead_can_reach_excludes_targets_own_ring() -> None:
    target = object()
    state = SimpleNamespace(initial_radar_sam_rings=_rings((target, 1000, 0, 300)))
    # Route ends deep inside the target's own ring -- that must not count.
    flights = [_flight((900, 0), (1000, 0))]
    assert TheaterState.dead_can_reach(state, target, flights) is True  # type: ignore[arg-type]


def test_dead_apply_effects_clears_reachable_sam() -> None:
    target = object()
    eliminated: list[object] = []
    state = SimpleNamespace(
        unreachable_air_defenses=set(),
        dead_can_reach=lambda tgt, flights: True,
        eliminate_air_defense=eliminated.append,
    )
    task = PlanDead(target)  # type: ignore[arg-type]
    task.package = SimpleNamespace(flights=[])  # type: ignore[assignment]
    task.apply_effects(state)  # type: ignore[arg-type]

    assert eliminated == [target]
    assert target not in state.unreachable_air_defenses


def test_dead_apply_effects_defers_unreachable_sam() -> None:
    target = object()
    eliminated: list[object] = []
    state = SimpleNamespace(
        unreachable_air_defenses=set(),
        dead_can_reach=lambda tgt, flights: False,
        eliminate_air_defense=eliminated.append,
    )
    task = PlanDead(target)  # type: ignore[arg-type]
    task.package = SimpleNamespace(flights=[])  # type: ignore[assignment]
    task.apply_effects(state)  # type: ignore[arg-type]

    # The SAM is NOT optimistically cleared; it's recorded as unreachable so
    # dependent strikes stay deferred and we don't re-task the DEAD.
    assert eliminated == []
    assert target in state.unreachable_air_defenses
