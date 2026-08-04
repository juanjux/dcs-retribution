"""The IADS graph the OPFOR planner sees.

Parity: the human player sees these links on the campaign map, so the planner gets
them too. What matters is that a code-named building reports WHAT it is
(PowerSource / CommandCenter) and that each node lists the sites feeding it.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from game.agent import views
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.theater.player import Player


class _FakeGroup:
    """Duck-typed IadsGroundGroup: only what the view reads."""

    def __init__(self, tgo: Any, role: IadsRole, alive: int = 4) -> None:
        self.ground_object = tgo
        self.iads_role = role
        self.alive_units = alive


def _tgo(name: str, owner: Player) -> Any:
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        is_friendly=lambda to_player, _o=owner: to_player is _o,
    )


def _game(nodes: list[Any], advanced: bool = True) -> Any:
    network = SimpleNamespace(nodes=nodes, advanced_iads=advanced)
    return SimpleNamespace(theater=SimpleNamespace(iads_network=network))


def _node(group: _FakeGroup, connections: list[_FakeGroup]) -> Any:
    return SimpleNamespace(group=group, connections={uuid4(): c for c in connections})


def test_enemy_node_reports_its_role_and_what_feeds_it() -> None:
    power = _tgo("CENTIPEDE", Player.BLUE)
    radar = _tgo("QUAGGA", Player.BLUE)
    node = _node(
        _FakeGroup(radar, IadsRole.EWR),
        [_FakeGroup(power, IadsRole.POWER_SOURCE)],
    )

    view = views.build_iads(_game([node]), "red")

    assert view.advanced is True
    assert len(view.nodes) == 1
    assert view.nodes[0].role == "Ewr"
    assert view.nodes[0].alive is True
    assert view.nodes[0].depends_on == [str(power.id)]


def test_own_network_is_not_returned() -> None:
    """It is a targeting aid: red plans against blue's network, not its own."""
    mine = _tgo("MY SAM", Player.RED)
    node = _node(_FakeGroup(mine, IadsRole.SAM), [])

    assert views.build_iads(_game([node]), "red").nodes == []


def test_non_participating_sites_are_skipped() -> None:
    """Point defenses and plain objects are not part of the Skynet graph."""
    pd = _tgo("SHILKA", Player.BLUE)
    node = _node(_FakeGroup(pd, IadsRole.POINT_DEFENSE), [])

    assert views.build_iads(_game([node]), "red").nodes == []


def test_a_dead_node_is_kept_and_marked() -> None:
    """Knowing a power station is already down is what says its radars are blind."""
    dead = _tgo("HAWK", Player.BLUE)
    node = _node(_FakeGroup(dead, IadsRole.POWER_SOURCE, alive=0), [])

    nodes = views.build_iads(_game([node]), "red").nodes
    assert len(nodes) == 1
    assert nodes[0].alive is False
