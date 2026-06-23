from types import SimpleNamespace

from game.theater.theatergroundobject import ShipGroundObject


class _FakePoint:
    """Minimal stand-in for dcs Point: supports subtraction, x/y, distance."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __sub__(self, other: "_FakePoint") -> "_FakePoint":
        return _FakePoint(self.x - other.x, self.y - other.y)

    def distance_to_point(self, other: "_FakePoint") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


def _ship() -> ShipGroundObject:
    # Bypass __init__ (which needs a PresetLocation + control point); we only
    # exercise the movement maths, which depend on position / groups / units.
    return object.__new__(ShipGroundObject)


def test_commit_move_shifts_group_and_units_by_delta() -> None:
    ship = _ship()
    ship.position = _FakePoint(0.0, 0.0)
    unit_a = SimpleNamespace(position=_FakePoint(10.0, 20.0))
    unit_b = SimpleNamespace(position=_FakePoint(-5.0, 5.0))
    ship.groups = [SimpleNamespace(units=[unit_a, unit_b])]
    ship.target_position = _FakePoint(1000.0, 2000.0)

    ship.commit_move()

    # Group recentered on the target, pending move cleared.
    assert (ship.position.x, ship.position.y) == (1000.0, 2000.0)
    assert ship.target_position is None
    # Every unit shifted by the same delta (+1000, +2000).
    assert (unit_a.position.x, unit_a.position.y) == (1010.0, 2020.0)
    assert (unit_b.position.x, unit_b.position.y) == (995.0, 2005.0)


def test_commit_move_without_target_is_a_noop() -> None:
    ship = _ship()
    ship.position = _FakePoint(3.0, 4.0)
    ship.groups = []
    ship.target_position = None

    ship.commit_move()  # must not raise

    assert (ship.position.x, ship.position.y) == (3.0, 4.0)


def test_destination_in_range_respects_80nm_cap() -> None:
    ship = _ship()
    ship.position = _FakePoint(0.0, 0.0)
    # 80 nm == 148160 m.
    assert ship.destination_in_range(_FakePoint(100_000.0, 0.0)) is True
    assert ship.destination_in_range(_FakePoint(200_000.0, 0.0)) is False
