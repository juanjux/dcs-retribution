"""What the planner can name, and what it can see arriving.

Two gaps found by an LLM playing turn 0: it could not get the id of any of its own
ground objects (so the free turn-0 rebuild was unusable, since `targets` is the enemy's),
and armor it had just bought showed up nowhere, so it had no way to tell a placed order
from a lost one.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, TYPE_CHECKING, cast
from uuid import uuid4

from game.agent import views
from game.theater.player import Player

if TYPE_CHECKING:
    from game import Game

from game.theater.theatergroundobject import (
    BuildingGroundObject,
    SamGroundObject,
    VehicleGroupGroundObject,
)


class _UnitType:
    """Hashable stand-in for a GroundUnitType (SimpleNamespace is not hashable)."""

    def __init__(self, display_name: str) -> None:
        self.display_name = display_name


def _cp(name: str, owner: Player, ground_objects: list[Any], orders: Any = None) -> Any:
    return SimpleNamespace(
        name=name,
        captured=owner,
        ground_objects=ground_objects,
        ground_unit_orders=orders,
    )


def test_pending_ground_shows_what_was_just_bought() -> None:
    cp = _cp(
        "ALPHA",
        Player.RED,
        [],
        orders=SimpleNamespace(units={_UnitType("T-72B3"): 32, _UnitType("BMP-2"): 0}),
    )
    assert views._pending_ground(cp) == {"T-72B3": 32}


def test_a_base_that_cannot_order_ground_is_not_an_error() -> None:
    """Carriers and off-map points have no order book at all."""
    assert views._pending_ground(_cp("CVN", Player.RED, [], orders=None)) == {}


def _tgo(cls: Any, name: str) -> Any:
    """A real TGO subclass instance without running its __init__ (it wants a theater)."""
    tgo = cls.__new__(cls)
    tgo.id = uuid4()
    tgo.name = name
    return tgo


def test_only_your_own_rebuildable_sites_are_listed(
    monkeypatch: Any,
) -> None:
    """Enemy sites are already in `targets`; buildings cannot be rebuilt this way."""
    mine_sam = _tgo(SamGroundObject, "SA-3 Kirovsk")
    mine_armor = _tgo(VehicleGroupGroundObject, "Armor Group Nalchik")
    mine_building = _tgo(BuildingGroundObject, "Factory Nalchik")
    theirs = _tgo(SamGroundObject, "Patriot Batumi")

    game = SimpleNamespace(
        theater=SimpleNamespace(
            controlpoints=[
                _cp("Nalchik", Player.RED, [mine_sam, mine_armor, mine_building]),
                _cp("Batumi", Player.BLUE, [theirs]),
            ]
        )
    )
    monkeypatch.setattr(
        views,
        "_build_target",
        lambda _game, go, kind, task: views.TargetView(
            id=str(go.id), name=go.name, kind=kind, suggested_task=task, pos=[0.0, 0.0]
        ),
    )

    listed = views.build_own_ground_objects(cast("Game", game), "red")
    assert {t.name for t in listed} == {"SA-3 Kirovsk", "Armor Group Nalchik"}
    assert {t.kind for t in listed} == {"sam", "ground"}
    assert all(t.id for t in listed)
