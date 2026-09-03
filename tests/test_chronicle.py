"""The chronicle's judgement calls, which are the part worth testing.

Rendering prose is not testable in any useful sense -- there is no correct
sentence. What is testable is when the chronicle decides something deserves
emphasis, and that it says the same thing twice about the same mission.
"""

from typing import Any, Dict, List

from game.chronicle import (
    LogEvent,
    chronicle_from_events,
    is_own_goal,
    is_upset,
    streak_positions,
    survived_defence,
)


def kill(t: float, pilot: str, aircraft: str = "F-15C Eagle") -> Dict[str, Any]:
    return {
        "t": t,
        "kind": "airkill",
        "side": 2,
        "actor_type": aircraft,
        "actor_pilot": pilot,
        "target_type": "MiG-29A Fulcrum",
        "weapon": "AIM-7M",
    }


def parse(raw: List[Dict[str, Any]]) -> List[LogEvent]:
    events = [LogEvent.from_raw(entry) for entry in raw]
    return [event for event in events if event is not None]


def test_an_attack_jet_downing_an_aircraft_is_an_upset() -> None:
    events = parse([kill(100, "Bentley", "A-10C Thunderbolt II (Suite 7)")])
    assert is_upset(events[0])


def test_a_fighter_downing_an_aircraft_is_not() -> None:
    """An Eagle killing a Fulcrum is Tuesday, and must not be shouted about."""
    events = parse([kill(100, "Carpenter", "F-15C Eagle")])
    assert not is_upset(events[0])


def test_two_kills_close_together_are_a_run() -> None:
    events = parse([kill(100, "Carpenter"), kill(150, "Carpenter")])
    assert streak_positions(events) == {0: 1, 1: 2}


def test_two_kills_far_apart_are_not() -> None:
    """Otherwise every second kill of a long mission reads as a hot streak."""
    events = parse([kill(100, "Carpenter"), kill(900, "Carpenter")])
    assert streak_positions(events) == {}


def test_kills_by_different_pilots_are_not_one_run() -> None:
    events = parse([kill(100, "Carpenter"), kill(150, "Bentley")])
    assert streak_positions(events) == {}


def test_a_crash_with_nobody_shooting_is_an_own_goal() -> None:
    events = parse([{"t": 500, "kind": "crash", "side": 2, "actor_pilot": "Gafotas"}])
    assert is_own_goal(events[0], events)


def test_a_crash_just_after_being_shot_at_is_not() -> None:
    events = parse(
        [
            {"t": 480, "kind": "defending", "side": 2, "actor_pilot": "Gafotas"},
            {"t": 500, "kind": "crash", "side": 2, "actor_pilot": "Gafotas"},
        ]
    )
    assert not is_own_goal(events[1], events)


def test_being_shot_at_and_flying_on_is_a_close_call() -> None:
    events = parse([{"t": 480, "kind": "defending", "side": 2, "actor_pilot": "Jefe"}])
    assert survived_defence(events[0], events)


def test_being_shot_at_and_going_down_is_not() -> None:
    events = parse(
        [
            {"t": 480, "kind": "defending", "side": 2, "actor_pilot": "Jefe"},
            {"t": 490, "kind": "crash", "side": 2, "actor_pilot": "Jefe"},
        ]
    )
    assert not survived_defence(events[0], events)


def test_the_enemy_side_is_not_our_story() -> None:
    red = dict(kill(100, "Petrov"), side=1)
    assert chronicle_from_events([red]) == ""


def test_a_mission_with_nothing_worth_telling_renders_nothing() -> None:
    """Taxiing about does not make a chronicle, and an empty one must be empty
    rather than a title with no body under it."""
    quiet = {"t": 10, "kind": "takeoff", "side": 2, "actor_pilot": "Carpenter"}
    assert chronicle_from_events([quiet]) == ""


def test_the_same_mission_reads_the_same_twice() -> None:
    """Phrasing is chosen by position, not at random: a debrief that rewords
    itself every time you open it is not a report."""
    raw = [kill(100, "Carpenter"), kill(150, "Carpenter"), kill(1200, "Bentley")]
    assert chronicle_from_events(raw) == chronicle_from_events(raw)


def test_a_malformed_record_is_dropped_rather_than_fatal() -> None:
    """State files predate fields, and a chronicle is never worth a broken
    debrief."""
    raw: List[Dict[str, Any]] = [{"nonsense": True}, kill(100, "Carpenter")]
    assert "Carpenter" in chronicle_from_events(raw)


def test_a_quiet_stretch_starts_a_new_act() -> None:
    raw = [kill(100, "Carpenter"), kill(2000, "Bentley")]
    assert chronicle_from_events(raw).count("**") == 4  # two headings, two ends
