"""The planner commands RED and must never be served BLUE's own view.

Every other asymmetry in this game is one the human can see and reason about. This
one is not: nothing tells them their plan is being read. So the API refuses it.

Two distinct holes are covered here:

* ``side=blue`` on any read — it used to hand over the player's entire ATO
  (32 packages with targets, tasks, TOTs and aircraft), air wing and budget.
* a BLUE flight id on a ``side=red`` call — ``game.db.flights`` is a global registry,
  so an id alone reached the player's flights. Reading one exposes the route they are
  about to fly; ``edit_waypoint`` would have let the planner MOVE it.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.agent import planner, service
from game.theater.player import Player


@pytest.mark.parametrize(
    "call",
    [
        lambda: service.turn_context(side="blue"),
        lambda: service.get_packages(side="blue"),
        lambda: service.iads(side="blue"),
        lambda: service.map_image(side="blue"),
        lambda: service.validate_plan(side="blue"),
        lambda: service.get_waypoints(side="blue", flight_id="x"),
    ],
)
def test_reads_for_the_other_side_are_refused(call: Any) -> None:
    with pytest.raises(service.SideNotAllowedError):
        call()


def test_the_refusal_names_the_side_it_serves() -> None:
    with pytest.raises(service.SideNotAllowedError) as excinfo:
        service.get_packages(side="blue")
    assert "red" in str(excinfo.value)


def _game_with_flight(owner: Player) -> Any:
    flight = SimpleNamespace(coalition=SimpleNamespace(player=owner))
    return SimpleNamespace(
        db=SimpleNamespace(flights=SimpleNamespace(get=lambda _uuid: flight))
    )


_ANY_UUID = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"


def test_a_flight_of_the_commanded_side_resolves() -> None:
    game = _game_with_flight(Player.RED)
    assert planner.flight_for_side(game, "red", _ANY_UUID) is not None


def test_a_flight_of_the_other_side_does_not_resolve() -> None:
    """Returned as "unknown id", not "forbidden": distinguishing the two would let the
    planner probe for which ids exist."""
    game = _game_with_flight(Player.BLUE)
    assert planner.flight_for_side(game, "red", _ANY_UUID) is None


def test_a_malformed_id_does_not_raise() -> None:
    game = _game_with_flight(Player.RED)
    assert planner.flight_for_side(game, "red", "not-a-uuid") is None
