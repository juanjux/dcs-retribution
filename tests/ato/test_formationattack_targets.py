"""Tests for FormationAttackBuilder.strike_targets_for.

This helper turns a ground objective's individual units into the per-target
list used both by the kneeboard target page (with coordinates) and by the
per-target TARGET_POINT waypoints, keeping the two in lockstep for Strike,
DEAD and SEAD.
"""

from types import SimpleNamespace

from game.ato.flighttype import FlightType
from game.ato.flightplans.formationattack import FormationAttackBuilder
from game.ato.flightplans.strike import Builder as StrikeBuilder
from game.ato.flightplans.waypointbuilder import StrikeTarget


class _FakeType:
    def __init__(self, id_: str) -> None:
        self.id = id_


class _FakeUnit:
    """Stands in for a TheaterUnit (not a SceneryUnit, so .type.id is used)."""

    def __init__(self, id_: str) -> None:
        self.type = _FakeType(id_)


class _FakeLocation:
    def __init__(self, units: list[_FakeUnit]) -> None:
        self.strike_targets = units


def test_one_target_per_alive_unit_with_indexed_names() -> None:
    location = _FakeLocation(
        [_FakeUnit("SA-10 ln"), _FakeUnit("SA-10 tr"), _FakeUnit("SA-10 cp")]
    )

    targets = FormationAttackBuilder.strike_targets_for(location)  # type: ignore[arg-type]

    assert [t.name for t in targets] == [
        "SA-10 ln #0",
        "SA-10 tr #1",
        "SA-10 cp #2",
    ]
    # Each StrikeTarget references the originating unit, so the waypoint and the
    # kneeboard row describe the same target.
    assert [t.target for t in targets] == location.strike_targets


def test_no_targets_when_objective_has_no_units() -> None:
    assert FormationAttackBuilder.strike_targets_for(_FakeLocation([])) == []  # type: ignore[arg-type]


def test_target_waypoints_fall_back_to_area_when_no_live_targets() -> None:
    """An objective with all units destroyed yields an empty target list.

    The layout must still get one (area) target waypoint, otherwise
    ``tot_waypoint`` -- which indexes ``targets[0]`` -- raises IndexError while
    planning a Strike/DEAD/SEAD against a fully destroyed objective (regression).
    """
    builder = StrikeBuilder.__new__(StrikeBuilder)  # skip IBuilder.__init__
    builder.flight = SimpleNamespace(  # type: ignore[assignment]
        flight_type=FlightType.STRIKE,
        package=SimpleNamespace(target=object()),
    )
    wp_builder = SimpleNamespace(
        strike_point=lambda target: ("point", target),
        strike_area=lambda location: "area",
    )

    # Empty list (all targets dead) and None both fall back to one area waypoint.
    assert builder._target_waypoints(wp_builder, []) == ["area"]  # type: ignore[arg-type]
    assert builder._target_waypoints(wp_builder, None) == ["area"]  # type: ignore[arg-type]

    # With live targets, one waypoint per target is produced.
    targets = [StrikeTarget("a #0", object()), StrikeTarget("b #1", object())]  # type: ignore[arg-type]
    result = builder._target_waypoints(wp_builder, targets)  # type: ignore[arg-type]
    assert result == [("point", targets[0]), ("point", targets[1])]
