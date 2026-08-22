"""Naval-magazine emitter (dcsRetribution.navalMagazines) -- the config bridge.

Locks the shape the ``navalmagazines`` plugin consumes: the two tier switches,
one ``group``/``coalition``/``remaining`` record per live naval group (including
a dry one, so the plugin knows to hold it), and no node at all when both tiers
are off or no naval group exists.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.naval_magazines import ASHM_MAGAZINE_BY_TYPE
from game.missiongenerator.luagenerator import LuaData, LuaValue
from game.missiongenerator.navalmagazineluadata import populate_naval_magazines_lua
from game.theater import Player

BURKE = "USS_Arleigh_Burke_IIa"
TYPE055 = "Type055"


def _kv(item: Any) -> dict[str, Any]:
    vals = item.value
    if isinstance(vals, LuaValue):
        vals = [vals]
    return {v.key: v.value for v in vals}


def _ship_tgo(owner_cp: Any, group_name: str, type_id: str) -> Any:
    units = [SimpleNamespace(alive=True, type=SimpleNamespace(id=type_id))]
    return SimpleNamespace(
        category="ship",
        name=group_name,
        control_point=owner_cp,
        groups=[SimpleNamespace(group_name=group_name, units=units)],
        units=units,
    )


def _game(*, stagger: bool = True, metered: bool = True, naval: bool = True) -> Any:
    blue_cp = SimpleNamespace(captured=Player.BLUE, ground_objects=[])
    red_cp = SimpleNamespace(captured=Player.RED, ground_objects=[])
    if naval:
        blue_cp.ground_objects.append(_ship_tgo(blue_cp, "CSG | Burke", BURKE))
        red_cp.ground_objects.append(_ship_tgo(red_cp, "PLAN | Type 055", TYPE055))
    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=[blue_cp, red_cp]),
        settings=SimpleNamespace(
            naval_weapon_release_stagger=stagger,
            naval_magazines=metered,
        ),
    )
    game.naval_magazines = {}
    return game


def _node(game: Any) -> Any:
    root = LuaData("dcsRetribution")
    populate_naval_magazines_lua(root, game, mission_data=None)  # type: ignore[arg-type]
    return root.get_item("navalMagazines")


def _records(node: Any, key: str) -> list[dict[str, Any]]:
    item = node.get_item(key)
    if item is None:
        return []
    assert isinstance(item, LuaData)
    return [_kv(rec) for rec in item.objects]


def _switches(node: Any) -> dict[str, Any]:
    return {str(v.key): v.value for v in node.value if isinstance(v, LuaValue)}


def test_emits_each_live_naval_group_with_its_magazine() -> None:
    node = _node(_game())
    assert node is not None
    groups = _records(node, "magazines")
    assert {g["group"]: (g["coalition"], g["remaining"]) for g in groups} == {
        "CSG | Burke": ("blue", str(ASHM_MAGAZINE_BY_TYPE[BURKE])),
        "PLAN | Type 055": ("red", str(ASHM_MAGAZINE_BY_TYPE[TYPE055])),
    }


def test_the_tier_switches_ride_on_the_node() -> None:
    switches = _switches(_node(_game(stagger=True, metered=False)))
    assert switches["stagger"] == "true"
    assert switches["metered"] == "false"

    switches = _switches(_node(_game(stagger=False, metered=True)))
    assert switches["stagger"] == "false"
    assert switches["metered"] == "true"


def test_a_dry_group_is_still_emitted() -> None:
    game = _game()
    node = _node(game)  # seeds the magazines
    assert node is not None
    for name in game.naval_magazines:
        game.naval_magazines[name] = 0
    groups = _records(_node(game), "magazines")
    assert {g["remaining"] for g in groups} == {"0"}


def test_no_node_when_both_tiers_are_off() -> None:
    assert _node(_game(stagger=False, metered=False)) is None


def test_no_node_when_the_theater_has_no_naval_group() -> None:
    assert _node(_game(naval=False)) is None


def test_emitting_never_debits_the_magazine() -> None:
    """Generation is not a debit site -- re-generating a turn must be free."""
    game = _game()
    _node(game)
    seeded = dict(game.naval_magazines)
    _node(game)
    _node(game)
    assert game.naval_magazines == seeded
