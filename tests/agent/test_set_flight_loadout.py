"""Re-arming a flight the planner did not create.

``POST /packages`` arms the flights it builds, but the engine builds some on its own and
does not arm them: a ``squadron/relocate`` launches its ferry flights with the "Empty"
loadout, because no airframe ships a payload named for the Ferry task and that task has
no fallback. The player fixes that in the Payload tab; without this endpoint the planner
could not fix it at all.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.agent import planner
from game.ato.loadouts import Loadout
from game.theater.player import Player

_ANY_UUID = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"
_NAMED = "Retribution BARCAP"


def _empty_member() -> Any:
    return SimpleNamespace(
        loadout=Loadout("Empty", {}, date=None), use_custom_loadout=False
    )


@pytest.fixture
def flight() -> Any:
    members = [_empty_member(), _empty_member()]
    return SimpleNamespace(
        coalition=SimpleNamespace(player=Player.RED),
        unit_type=SimpleNamespace(display_name="Su-27", dcs_unit_type=object()),
        flight_type=SimpleNamespace(value="Ferry"),
        members=members,
        iter_members=lambda: iter(members),
    )


@pytest.fixture
def game(flight: Any) -> Any:
    return SimpleNamespace(
        db=SimpleNamespace(flights=SimpleNamespace(get=lambda _uuid: flight))
    )


@pytest.fixture(autouse=True)
def offered(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for the names ``GET /aircraft/loadouts`` offers for this airframe, and
    for the live-map event sink (there is no server in a test)."""
    available = [Loadout(_NAMED, {}, date=None)]
    monkeypatch.setattr(
        Loadout, "iter_for", classmethod(lambda cls, flight: iter(available))
    )
    monkeypatch.setattr(
        planner,
        "_new_map_events",
        lambda: SimpleNamespace(update_flight=lambda _flight: None),
    )


def test_a_named_loadout_reaches_every_member(game: Any, flight: Any) -> None:
    result = planner.set_flight_loadout(game, "red", _ANY_UUID, _NAMED)
    assert result.ok, result.error
    assert [m.loadout.name for m in flight.members] == [_NAMED, _NAMED]


def test_a_named_loadout_is_not_flagged_custom(game: Any, flight: Any) -> None:
    """``use_custom_loadout`` gates the per-pylon editor and the date degradation that
    swaps LGBs for iron. A ready-made loadout is neither hand-built nor exempt."""
    planner.set_flight_loadout(game, "red", _ANY_UUID, _NAMED)
    assert not any(m.use_custom_loadout for m in flight.members)


def test_a_pylon_map_is_flagged_custom(game: Any, flight: Any) -> None:
    result = planner.set_flight_loadout(game, "red", _ANY_UUID, {1: "{clsid}"})
    assert result.ok, result.error
    assert all(m.use_custom_loadout for m in flight.members)


def test_an_unknown_name_is_refused_and_changes_nothing(game: Any, flight: Any) -> None:
    """A name the airframe does not offer must not quietly leave the flight Empty."""
    result = planner.set_flight_loadout(game, "red", _ANY_UUID, "Retribution Nonsense")
    assert not result.ok
    assert "Retribution Nonsense" in (result.error or "")
    assert [m.loadout.name for m in flight.members] == ["Empty", "Empty"]


def test_the_other_side_cannot_re_arm_the_players_flight(flight: Any) -> None:
    """db.flights is a global registry: an id alone would reach the human's flights."""
    flight.coalition = SimpleNamespace(player=Player.BLUE)
    game: Any = SimpleNamespace(
        db=SimpleNamespace(flights=SimpleNamespace(get=lambda _uuid: flight))
    )
    result = planner.set_flight_loadout(game, "red", _ANY_UUID, _NAMED)
    assert not result.ok
    assert "no flight with id" in (result.error or "")
    assert [m.loadout.name for m in flight.members] == ["Empty", "Empty"]
