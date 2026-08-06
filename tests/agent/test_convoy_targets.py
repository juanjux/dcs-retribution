"""Enemy convoys and cargo ships are targets the planner can see and attack.

The human opens a base, reads its "Departing Convoys" tab and clicks Attack on any of
them. Without this the planner did not know they existed — and reinforcements in
transit are the cheapest thing on the board to kill, because the units die before
they ever deploy.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.agent import views
from game.theater.player import Player


class _Unit:
    def __init__(self, name: str) -> None:
        self._name = name

    def __str__(self) -> str:
        return self._name


def _point(x: float, y: float) -> Any:
    return SimpleNamespace(x=x, y=y)


def _convoy(name: str, units: dict[Any, int], **extra: Any) -> Any:
    return SimpleNamespace(
        name=name,
        units=units,
        position=_point(0, 0),
        origin=SimpleNamespace(name="Hama"),
        destination=SimpleNamespace(name="Palmyra"),
        **extra,
    )


def _game(convoys: list[Any], ships: list[Any]) -> Any:
    enemy = SimpleNamespace(
        transfers=SimpleNamespace(convoys=convoys, cargo_ships=ships)
    )
    terrain = object()
    return SimpleNamespace(
        coalition_for=lambda _player: SimpleNamespace(opponent=enemy),
        theater=SimpleNamespace(terrain=terrain),
    )


def _patch_latlng(monkeypatch: Any) -> None:
    """DcsPoint needs a real terrain to project; the projection is not what is tested."""
    monkeypatch.setattr(
        views,
        "DcsPoint",
        lambda x, y, _t: SimpleNamespace(latlng=lambda: SimpleNamespace(lat=x, lng=y)),
    )


def test_a_convoy_is_a_bai_target_with_its_route_and_cargo(monkeypatch: Any) -> None:
    _patch_latlng(monkeypatch)
    convoy = _convoy(
        "Convoy 001",
        {_Unit("Leopard 2A4"): 4, _Unit("M113"): 2},
        route_start=_point(1, 2),
        route_end=_point(3, 4),
    )

    targets = views._build_transport_targets(_game([convoy], []), Player.RED)

    assert len(targets) == 1
    t = targets[0]
    assert (t.id, t.kind, t.suggested_task) == ("Convoy 001", "convoy", "BAI")
    assert (t.origin, t.destination) == ("Hama", "Palmyra")
    assert t.route == [[1, 2], [3, 4]]
    assert t.composition == {"Leopard 2A4": 4, "M113": 2}


def test_a_cargo_ship_is_an_antiship_target_and_uses_its_lane(monkeypatch: Any) -> None:
    """A CargoShip has no route_start/route_end — it carries the whole shipping lane,
    of which the endpoints are what matter."""
    _patch_latlng(monkeypatch)
    ship = _convoy(
        "Cargo 001",
        {_Unit("M1 Abrams"): 8},
        route=[_point(1, 1), _point(5, 5), _point(9, 9)],
    )

    targets = views._build_transport_targets(_game([], [ship]), Player.RED)

    assert (targets[0].kind, targets[0].suggested_task) == ("cargo_ship", "ANTISHIP")
    assert targets[0].route == [[1, 1], [9, 9]]


def test_an_empty_convoy_is_not_reported(monkeypatch: Any) -> None:
    """A convoy that carries nothing is bookkeeping, not a target worth a package."""
    _patch_latlng(monkeypatch)
    empty = _convoy("Convoy 002", {}, route_start=_point(0, 0), route_end=_point(1, 1))

    assert views._build_transport_targets(_game([empty], []), Player.RED) == []
