"""Tests for FormationAttackBuilder.strike_targets_for.

This helper turns a ground objective's individual units into the per-target
list used both by the kneeboard target page (with coordinates) and by the
per-target TARGET_POINT waypoints, keeping the two in lockstep for Strike,
DEAD and SEAD.
"""

from game.ato.flightplans.formationattack import FormationAttackBuilder


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
