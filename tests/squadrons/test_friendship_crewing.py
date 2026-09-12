"""Filling a flight tries to keep a crew together.

The player's preference about who flies still decides who is eligible; friendship only
orders the men who already matched it. Everything here is about not disturbing that,
because crewing is the one part of the turn that must never surprise anybody.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs.unit import Skill

from game.settings import AutoAtoBehavior, Settings
from game.squadrons import friendship
from game.squadrons.pilot import Pilot
from game.theater.player import Player


def _squadron(settings: Settings, pilots: list[Pilot], blue: bool = True) -> Any:
    from game.squadrons.squadron import Squadron

    squadron: Any = Squadron.__new__(Squadron)
    squadron.settings = settings
    squadron.coalition = SimpleNamespace(
        player=Player.BLUE if blue else Player.RED,
        game=SimpleNamespace(turn=6),
    )
    squadron.available_pilots = list(pilots)
    squadron.current_roster = list(pilots)
    return squadron


def _settings(**values: Any) -> Settings:
    settings = Settings()
    settings.live_pilots_enabled = True
    settings.ai_pilot_levelling = True
    settings.player_skill = Skill.Good.value
    settings.enable_squadron_pilot_limits = False
    for name, value in values.items():
        setattr(settings, name, value)
    return settings


def test_the_second_seat_goes_to_somebody_the_first_gets_on_with() -> None:
    lead, friend, stranger = Pilot("Lead"), Pilot("Friend"), Pilot("Stranger")
    friendship.move(lead, friend, 4.0)
    friendship.move(friend, lead, 4.0)
    squadron = _squadron(_settings(), [friend, stranger])

    assert squadron.claim_available_pilot([lead]) is friend
    assert friend not in squadron.available_pilots


def test_a_man_the_crew_cannot_stand_is_the_last_one_taken() -> None:
    lead, enemy, stranger = Pilot("Lead"), Pilot("Enemy"), Pilot("Stranger")
    friendship.move(lead, enemy, -4.0)
    friendship.move(enemy, lead, -4.0)
    squadron = _squadron(_settings(), [enemy, stranger])

    assert squadron.claim_available_pilot([lead]) is stranger


def test_the_first_seat_is_filled_the_way_it_always_was() -> None:
    """Nobody to get on with yet, so the list decides -- and it has to decide exactly
    as it did before any of this existed."""
    first, second = Pilot("First"), Pilot("Second")
    squadron = _squadron(_settings(), [first, second])
    assert squadron.claim_available_pilot() is second  # off the end, as ever


def test_switched_off_friendship_does_not_touch_the_order() -> None:
    lead, friend, stranger = Pilot("Lead"), Pilot("Friend"), Pilot("Stranger")
    friendship.move(lead, friend, 4.0)
    friendship.move(friend, lead, 4.0)
    squadron = _squadron(_settings(friendship_enabled=False), [friend, stranger])
    assert squadron.claim_available_pilot([lead]) is stranger


def test_a_crew_of_strangers_is_no_reason_to_reorder_anything() -> None:
    first, second = Pilot("First"), Pilot("Second")
    squadron = _squadron(_settings(), [first, second])
    assert squadron.claim_available_pilot([Pilot("Lead")]) is second


def test_the_preference_about_players_still_decides_who_is_eligible() -> None:
    """Friendship orders the men who matched it. It does not get to overrule it."""
    lead = Pilot("Lead")
    human = Pilot("Human", player=True)
    friend = Pilot("Friend")
    friendship.move(lead, friend, 4.0)
    friendship.move(friend, lead, 4.0)

    settings = _settings(auto_ato_behavior=AutoAtoBehavior.Prefer)
    squadron = _squadron(settings, [friend, human])
    assert squadron.claim_available_pilot([lead]) is human


def test_red_groups_its_crews_too() -> None:
    """Red goes straight to the pool, so without this it would be the only side whose
    pilots never get to know each other beyond the drift."""
    lead, friend, stranger = Pilot("Lead"), Pilot("Friend"), Pilot("Stranger")
    friendship.move(lead, friend, 4.0)
    friendship.move(friend, lead, 4.0)
    squadron = _squadron(_settings(), [friend, stranger], blue=False)
    assert squadron.claim_available_pilot([lead]) is friend
