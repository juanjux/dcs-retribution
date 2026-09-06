"""How a pilot holds up, and what it is worth.

Morale is a number nobody can see deciding what a sortie pays, how steady a flight is
under fire and whether a man keeps turning up. These pin the arithmetic so it can be
tuned later without anyone having to rediscover what it was supposed to do.
"""

from __future__ import annotations

import random
from types import SimpleNamespace
from typing import Any

import pytest
from dcs.task import OptReactOnThreat
from dcs.unit import Skill

from game.dcs.skills import CADET_SKILL, SKILL_LADDER
from game.settings import Settings
from game.squadrons import morale as morale_rules
from game.squadrons.pilot import Pilot, PilotStatus

# --- the number -------------------------------------------------------------


def test_a_pilot_starts_with_nobody_having_an_opinion_about_him() -> None:
    assert Pilot("New").morale == morale_rules.MORALE_START == 50


def test_a_pilot_from_an_older_save_starts_the_same_way() -> None:
    """A campaign in progress must not punish pilots for a rest they could not ask for."""
    pilot = Pilot.__new__(Pilot)
    pilot.__setstate__({"name": "Veteran", "status": PilotStatus.Active})
    assert pilot.morale == 50
    assert pilot.turns_since_leave == 0
    assert pilot.wants_leave is False
    assert pilot.leave_turns == 0


@pytest.mark.parametrize("morale,step", [(1, 1), (49, 1), (50, 0), (51, -1), (100, -1)])
def test_he_drifts_back_towards_the_middle_from_either_side(
    morale: int, step: int
) -> None:
    assert morale_rules.drift(morale) == step


def test_but_a_man_at_the_bottom_does_not_mend_on_his_own() -> None:
    """He will not fly, so he can earn nothing back. Only leave lifts him."""
    assert morale_rules.drift(0) == 0


def test_rank_softens_the_knocks_and_not_the_good_news() -> None:
    """A squadron leader has seen it before. He is not too senior to enjoy a promotion."""
    cadet = morale_rules.apply(50, morale_rules.LOST_AIRCRAFT, CADET_SKILL)
    veteran = morale_rules.apply(50, morale_rules.LOST_AIRCRAFT, Skill.Excellent)
    assert cadet < veteran < 50

    assert morale_rules.apply(50, morale_rules.PROMOTED, CADET_SKILL) == (
        morale_rules.apply(50, morale_rules.PROMOTED, Skill.Excellent)
    )


def test_a_knock_always_costs_something() -> None:
    """However senior he is, being shot down is not free."""
    assert morale_rules.apply(50, morale_rules.NO_LEAVE, Skill.Excellent) < 50


@pytest.mark.parametrize("morale", [-40, 0, 50, 100, 160])
def test_it_never_leaves_its_range(morale: int) -> None:
    assert 0 <= morale_rules.clamp(morale) <= 100


# --- what a sortie is worth -------------------------------------------------


@pytest.mark.parametrize(
    "morale,multiplier",
    [
        (0, 0.5),
        (9, 0.5),
        (10, 0.8),
        (39, 0.8),
        (40, 1.0),
        (59, 1.0),
        (60, 1.2),
        (80, 1.2),
        (81, 1.5),
        (100, 1.5),
    ],
)
def test_the_bands_are_where_the_notes_put_them(morale: int, multiplier: float) -> None:
    assert morale_rules.xp_multiplier(morale) == pytest.approx(multiplier)


def test_flying_with_your_betters_is_worth_something() -> None:
    """The worked example: a cadet, an average, a high and an excellent in one flight."""
    best = Skill.Excellent
    assert morale_rules.learning_bonus(CADET_SKILL, best) == pytest.approx(0.4)
    assert morale_rules.learning_bonus(Skill.Average, best) == pytest.approx(0.3)
    assert morale_rules.learning_bonus(Skill.High, best) == pytest.approx(0.1)
    assert morale_rules.learning_bonus(Skill.Excellent, best) == pytest.approx(0.0)


def test_nobody_learns_from_somebody_worse_than_them() -> None:
    assert morale_rules.learning_bonus(Skill.Excellent, CADET_SKILL) == 0.0


# --- what the player is told ------------------------------------------------


@pytest.mark.parametrize(
    "morale,name",
    [
        (100, "Triumphant"),
        (85, "Triumphant"),
        (84, "Confident"),
        (60, "Confident"),
        (59, "Normal"),
        (40, "Normal"),
        (39, "Shaken"),
        (15, "Shaken"),
        (14, "Shattered"),
        (1, "Shattered"),
        (0, "Broken"),
    ],
)
def test_the_player_is_told_a_word_and_never_a_number(morale: int, name: str) -> None:
    assert morale_rules.morale_state(morale).name == name


def test_the_warning_the_word_carries() -> None:
    """Shaken is worth an eye; below it the player has to do something."""
    assert morale_rules.morale_state(50).severity == 0
    assert morale_rules.morale_state(20).severity == 1
    assert morale_rules.morale_state(5).severity == 2
    assert morale_rules.morale_state(0).severity == 2


def test_every_point_has_a_word() -> None:
    for morale in range(morale_rules.MORALE_MIN, morale_rules.MORALE_MAX + 1):
        assert morale_rules.morale_state(morale).name


# --- how he flies -----------------------------------------------------------


def _squadron(settings: Settings) -> Any:
    from game.squadrons.squadron import Squadron

    squadron: Any = Squadron.__new__(Squadron)
    squadron.settings = settings
    squadron.coalition = SimpleNamespace(
        player=SimpleNamespace(is_blue=True), game=SimpleNamespace(turn=6)
    )
    squadron.country = None
    squadron.name = "Zero Company"
    squadron.nickname = None
    return squadron


def _live_settings() -> Settings:
    settings = Settings()
    settings.live_pilots_enabled = True
    settings.ai_pilot_levelling = True
    settings.player_skill = Skill.Good.value
    return settings


def test_morale_moves_what_he_flies_at_and_not_what_he_has_earned() -> None:
    """Or a bad week would demote a Major, and a good one would promote him back."""
    squadron = _squadron(_live_settings())
    pilot = Pilot("Vega")
    pilot.record.xp = 2000  # Good, on his own merits

    rank_at_50 = squadron.pilot_rank(pilot).abbreviation
    assert squadron.mission_skill(pilot) is Skill.Good

    pilot.morale = 95
    assert squadron.mission_skill(pilot) is Skill.High
    assert squadron.pilot_rank(pilot).abbreviation == rank_at_50

    pilot.morale = 5
    assert squadron.mission_skill(pilot) is Skill.Average
    assert squadron.pilot_rank(pilot).abbreviation == rank_at_50


def test_the_ladder_is_not_climbed_past_its_ends() -> None:
    assert morale_rules.shifted_skill(Skill.Excellent, 99) is Skill.Excellent
    assert morale_rules.shifted_skill(CADET_SKILL, 1) is CADET_SKILL


@pytest.mark.parametrize(
    "morale,reaction",
    [
        (50, OptReactOnThreat.Values.EvadeFire),
        (20, OptReactOnThreat.Values.EvadeFire),
        (19, OptReactOnThreat.Values.ByPassAndEscape),
        (10, OptReactOnThreat.Values.ByPassAndEscape),
        (9, OptReactOnThreat.Values.AllowAbortMission),
    ],
)
def test_how_much_the_flight_will_put_up_with(
    morale: int, reaction: OptReactOnThreat.Values
) -> None:
    assert morale_rules.threat_reaction(morale) is reaction


def test_a_hollow_man_is_slower_to_mend_and_a_cheerful_one_quicker() -> None:
    assert morale_rules.recovery_turns(3, morale=5) == 4
    assert morale_rules.recovery_turns(3, morale=50) == 3
    assert morale_rules.recovery_turns(3, morale=95) == 2
    assert morale_rules.recovery_turns(1, morale=95) == 1  # never to nothing


def test_the_steady_man_gets_out_of_the_aircraft() -> None:
    assert morale_rules.survival_modifier(100) > 0
    assert morale_rules.survival_modifier(50) == 0
    assert morale_rules.survival_modifier(0) < 0


# --- leave ------------------------------------------------------------------


def test_leave_is_counted_like_a_wound() -> None:
    pilot = Pilot("Vega")
    pilot.send_on_leave(2, turn=5)
    assert pilot.on_leave

    # Compared as tuples so mypy does not pin the property and call the last one dead.
    pilot.serve_a_turn_of_leave(5)  # the turn it was granted in does not count
    assert (pilot.leave_turns, pilot.on_leave) == (2, True)

    pilot.serve_a_turn_of_leave(6)
    assert (pilot.leave_turns, pilot.on_leave) == (1, True)

    pilot.serve_a_turn_of_leave(7)
    assert (pilot.leave_turns, pilot.on_leave) == (0, False)
    assert pilot.turns_since_leave == 0


def test_open_ended_leave_still_waits_for_the_player() -> None:
    """The Air Wing button grants no particular length, and that has to keep working."""
    pilot = Pilot("Vega")
    pilot.send_on_leave()
    for turn in range(20):
        pilot.serve_a_turn_of_leave(turn)
    assert pilot.on_leave


def test_a_worn_out_pilot_asks_more_often_than_a_contented_one() -> None:
    low = morale_rules.leave_request_chance(5, base_percent=8)
    middling = morale_rules.leave_request_chance(50, base_percent=8)
    high = morale_rules.leave_request_chance(95, base_percent=8)
    assert low > middling > high > 0, "even a happy man wants a week off sometimes"


# --- the end of a pilot -----------------------------------------------------


def test_at_the_bottom_he_will_not_fly() -> None:
    pilot = Pilot("Vega")
    pilot.morale = 0
    assert pilot.refuses_to_fly
    pilot.morale = 1
    assert not pilot.refuses_to_fly


def test_rank_is_what_keeps_a_man_in_his_seat() -> None:
    """Desertion is a roll each turn at the bottom, and the veteran is the last to go."""
    chances = [morale_rules.desertion_chance(s) for s in SKILL_LADDER]
    assert chances == sorted(chances, reverse=True)
    assert all(0 < c < 0.5 for c in chances)


def test_left_at_the_bottom_he_eventually_walks_away() -> None:
    settings = _live_settings()
    settings.morale_leave_request_chance = 0
    squadron = _squadron(settings)
    pilot = Pilot("Vega")
    pilot.morale = 0
    squadron.current_roster = [pilot]

    random.seed(4)  # a run in which the roll comes up
    for turn in range(200):
        squadron.tend_morale(turn)
        if pilot.deserted:
            break

    assert pilot.deserted
    assert not pilot.alive, "gone is gone; the squadron has to replace him"
    assert pilot.turns_at_zero > 1, "he did not go on the first turn every time"


def test_a_man_who_is_not_at_the_bottom_never_deserts() -> None:
    settings = _live_settings()
    settings.morale_leave_request_chance = 0
    squadron = _squadron(settings)
    pilot = Pilot("Vega")
    squadron.current_roster = [pilot]

    random.seed(1)
    for turn in range(50):
        pilot.morale = 50  # held there against the no-leave penalty
        squadron.tend_morale(turn)

    assert not pilot.deserted


def test_he_asks_for_a_number_of_turns_and_the_worse_he_is_the_longer() -> None:
    """Nobody asks for leave in the abstract: he asks for a morning, a day, a week."""
    steady = morale_rules.requested_leave_turns(50, roll=0.0)
    shaken = morale_rules.requested_leave_turns(20, roll=0.0)
    broken = morale_rules.requested_leave_turns(0, roll=0.0)
    assert steady < shaken < broken
    assert all(
        1 <= morale_rules.requested_leave_turns(m) <= morale_rules.MAX_LEAVE_TURNS
        for m in range(0, 101)
    )


def test_what_moved_him_is_written_down() -> None:
    """The pilot dialog reads this back; nothing in the campaign depends on it."""
    pilot = Pilot("Vega")
    pilot.move_morale(morale_rules.AIR_KILL, CADET_SKILL, turn=3)
    pilot.move_morale(morale_rules.LOST_AIRCRAFT, CADET_SKILL, turn=4)

    assert [e.reason for e in pilot.morale_log] == [
        "shot one down",
        "lost his aircraft",
    ]
    assert [e.turn for e in pilot.morale_log] == [3, 4]
    assert pilot.morale_log[0].amount > 0 and pilot.morale_log[1].amount < 0
    assert pilot.morale_log[-1].morale_after == pilot.morale


def test_a_move_that_changes_nothing_is_not_worth_writing_down() -> None:
    pilot = Pilot("Vega")
    pilot.morale = morale_rules.MORALE_MAX
    pilot.move_morale(morale_rules.AIR_KILL, CADET_SKILL, turn=1)
    assert pilot.morale_log == []


def test_the_log_does_not_grow_without_end() -> None:
    """It rides in every save, so a long campaign must not fill one with a man's week."""
    pilot = Pilot("Vega")
    for turn in range(morale_rules.MORALE_HISTORY_LIMIT * 3):
        pilot.morale = 50
        pilot.move_morale(morale_rules.LOST_AIRCRAFT, CADET_SKILL, turn=turn)
    assert len(pilot.morale_log) == morale_rules.MORALE_HISTORY_LIMIT
    assert pilot.morale_log[-1].turn == morale_rules.MORALE_HISTORY_LIMIT * 3 - 1


def test_going_without_leave_gets_worse_the_longer_it_lasts() -> None:
    settings = _live_settings()
    settings.morale_leave_request_chance = 0  # keep the dice out of it
    squadron = _squadron(settings)
    pilot = Pilot("Vega")
    squadron.current_roster = [pilot]

    for turn in range(morale_rules.TURNS_BEFORE_LEAVE_IS_MISSED):
        squadron.tend_morale(turn)
    settled = pilot.morale

    squadron.tend_morale(99)
    first_overdue = settled - pilot.morale
    before = pilot.morale
    squadron.tend_morale(100)
    second_overdue = before - pilot.morale

    assert first_overdue > 0
    assert second_overdue > first_overdue, "it compounds"
