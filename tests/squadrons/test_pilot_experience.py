"""Experience, promotion, and what a sortie is worth.

Rank used to be a count of missions flown, which ticked for every pilot in the ATO
whether he flew, fought, or died on the ramp. It is earned now.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from dcs.unit import Skill

from game.dcs.skills import (
    CADET_SKILL,
    SKILL_LADDER,
    SKILL_XP_THRESHOLDS,
    experience_for_skill,
    skill_for_experience,
)
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.squadrons.experience import (
    XP_AIR_KILL,
    XP_GROUND_KILL,
    XP_SHIP_KILL,
    building_xp,
    survival_chance,
)
from game.squadrons.pilot import PilotRecord

# --- the ladder -------------------------------------------------------------


def test_a_rung_costs_what_it_says() -> None:
    assert SKILL_XP_THRESHOLDS == (0, 1000, 2000, 4000, 8000)
    assert len(SKILL_XP_THRESHOLDS) == len(SKILL_LADDER)


@pytest.mark.parametrize(
    "xp,expected",
    [
        (0, CADET_SKILL),
        (999, CADET_SKILL),
        (1000, Skill.Average),
        (1999, Skill.Average),
        (2000, Skill.Good),
        (3999, Skill.Good),
        (4000, Skill.High),
        (7999, Skill.High),
        (8000, Skill.Excellent),
        (99999, Skill.Excellent),
    ],
)
def test_the_threshold_is_the_boundary(xp: int, expected: Skill) -> None:
    """One point short is one rank short."""
    assert skill_for_experience(xp, CADET_SKILL) is expected


def test_the_coalition_setting_is_a_floor_not_a_start() -> None:
    """Raising the difficulty lifts the wing; it never demotes a veteran."""
    assert skill_for_experience(0, Skill.High) is Skill.High
    assert skill_for_experience(8000, Skill.High) is Skill.Excellent


def test_seeding_a_veteran_costs_what_his_rank_costs() -> None:
    for skill, threshold in zip(SKILL_LADDER, SKILL_XP_THRESHOLDS):
        assert experience_for_skill(skill) == threshold


def test_a_skill_that_is_not_a_rung_seeds_nothing() -> None:
    assert experience_for_skill(Skill.Random) == 0


# --- persistence ------------------------------------------------------------


def test_a_pilot_from_an_older_save_starts_at_zero() -> None:
    """PilotRecord predates experience; unpickling one must not raise."""
    record = PilotRecord.__new__(PilotRecord)
    record.__setstate__({"missions_flown": 12})
    assert record.missions_flown == 12
    assert record.xp == 0


# --- what things are worth --------------------------------------------------


@pytest.mark.parametrize(
    "category,xp",
    [("oil", 500), ("derrick", 400), ("factory", 125), ("ammo", 100), ("farp", 50)],
)
def test_a_building_is_paid_by_what_it_is_worth(category: str, xp: int) -> None:
    assert building_xp(category) == xp


def test_an_unpriced_category_still_pays_something() -> None:
    """Power plants and command centres earn nothing per turn but are worth bombing."""
    assert building_xp("power") > 0
    assert building_xp(None) > 0


def test_the_better_pilot_is_likelier_to_walk_away() -> None:
    chances = [survival_chance(skill) for skill in SKILL_LADDER]
    assert chances == sorted(chances)
    assert chances[0] < chances[-1]


# --- crediting a kill -------------------------------------------------------


def _processor() -> MissionResultsProcessor:
    return MissionResultsProcessor(MagicMock())


def _victim_flight() -> Any:
    return SimpleNamespace(flight=MagicMock(), pilot=MagicMock())


def _victim_theater_unit(unit_type: Any, category: str = "oil") -> Any:
    tgo = SimpleNamespace(category=category, control_point=MagicMock())
    return SimpleNamespace(
        theater_unit=SimpleNamespace(unit_type=unit_type, ground_object=tgo)
    )


def test_an_aircraft_is_worth_an_air_kill() -> None:
    assert _processor()._kill_xp(_victim_flight()) == XP_AIR_KILL


def test_a_building_is_worth_its_category() -> None:
    # Statics carry no unit type at all, which is exactly how a building is recognised.
    assert _processor()._kill_xp(_victim_theater_unit(None, "oil")) == building_xp(
        "oil"
    )


def test_a_hull_is_worth_a_flat_rate() -> None:
    from game.dcs.shipunittype import ShipUnitType

    ship = MagicMock(spec=ShipUnitType)
    assert _processor()._kill_xp(_victim_theater_unit(ship)) == XP_SHIP_KILL


def test_a_vehicle_is_worth_a_ground_kill() -> None:
    from game.dcs.groundunittype import GroundUnitType

    vehicle = MagicMock(spec=GroundUnitType)
    assert _processor()._kill_xp(_victim_theater_unit(vehicle)) == XP_GROUND_KILL


def test_nothing_destroyed_is_worth_nothing() -> None:
    assert _processor()._kill_xp(None) == 0


# --- naming the killer ------------------------------------------------------


def _debriefing_with(killer_pilot_name: str | None, killer_is_blue: bool) -> Any:
    if killer_pilot_name is None:
        killer = None
    else:
        killer = SimpleNamespace(
            pilot=SimpleNamespace(name=killer_pilot_name),
            flight=SimpleNamespace(
                squadron=SimpleNamespace(player=SimpleNamespace(is_blue=killer_is_blue))
            ),
        )
    return SimpleNamespace(unit_map=SimpleNamespace(flight=lambda name: killer))


def test_nobody_credited_reads_as_a_crash() -> None:
    text, friendly = _processor()._describe_killer(None, MagicMock(), True)
    assert text == "a crash"
    assert friendly is False


def test_the_roster_pilot_is_named_when_he_can_be_resolved() -> None:
    detail = {
        "initiator": "STAG|2|1|F-15C|",
        "initiator_type": "F-15C",
        "weapon": "AIM-120C",
    }
    text, friendly = _processor()._describe_killer(
        detail, _debriefing_with("Capt Ortega", killer_is_blue=False), True
    )
    assert text == "Capt Ortega (F-15C) with AIM-120C"
    assert friendly is False


def test_an_unresolvable_killer_falls_back_to_the_airframe() -> None:
    detail = {"initiator": "unknown", "initiator_type": "SA-11 Buk LN"}
    text, _ = _processor()._describe_killer(
        detail, _debriefing_with(None, killer_is_blue=False), True
    )
    assert text == "SA-11 Buk LN"


def test_a_killer_on_our_own_side_is_flagged() -> None:
    detail = {"initiator": "STAG|2|1|F-15C|", "initiator_type": "F-15C"}
    _, friendly = _processor()._describe_killer(
        detail, _debriefing_with("Maj Ruiz", killer_is_blue=True), True
    )
    assert friendly is True
