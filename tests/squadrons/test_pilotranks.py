"""Rank ladders, and the Cadet rung pydcs was missing."""

from typing import Optional

import pytest
from dcs.countries import country_dict
from dcs.country import Country
from dcs.unit import Skill

from game.dcs.skills import CADET_SKILL, SKILL_LADDER
from game.squadrons.pilotranks import (
    COUNTRY_RANKS,
    GENERIC_RANKS,
    RankLadder,
    rank_for_skill,
    ranks_for_country,
)


def _country(name: str) -> Country:
    for factory in country_dict.values():
        country = factory()
        if country.name == name:
            return country
    raise AssertionError(f"no such DCS country: {name}")


def test_cadet_reaches_the_mission_file() -> None:
    """DCS has five air skills; pydcs shipped four."""
    assert Skill("Cadet") is CADET_SKILL
    assert CADET_SKILL.value == "Cadet"


def test_the_ladder_runs_from_cadet_to_ace() -> None:
    assert [skill.value for skill in SKILL_LADDER] == [
        "Cadet",
        "Average",
        "Good",
        "High",
        "Excellent",
    ]


@pytest.mark.parametrize("ladder", [GENERIC_RANKS, *COUNTRY_RANKS.values()])
def test_every_ladder_has_one_rung_per_skill(ladder: RankLadder) -> None:
    assert len(ladder) == len(SKILL_LADDER)
    assert all(rank.abbreviation and rank.name for rank in ladder)


@pytest.mark.parametrize(
    "country_name,expected",
    [
        ("USA", ["2ndLt", "1stLt", "Capt", "Maj", "LtCol"]),
        ("UK", ["PltOff", "FgOff", "FltLt", "SqnLdr", "WgCdr"]),
        ("Russia", ["MlLt", "Lt", "StLt", "Kpt", "Mjr"]),
        ("Spain", ["Alf", "Tte", "Cap", "Cte", "Tcol"]),
    ],
)
def test_a_squadron_promotes_through_its_own_service(
    country_name: str, expected: list[str]
) -> None:
    country = _country(country_name)
    assert [
        rank_for_skill(skill, country).abbreviation for skill in SKILL_LADDER
    ] == expected


@pytest.mark.parametrize(
    "country_name", ["Combined Joint Task Forces Blue", "Insurgents"]
)
def test_countries_with_no_ladder_of_their_own_fall_back(country_name: str) -> None:
    assert ranks_for_country(_country(country_name)) == GENERIC_RANKS


def test_no_country_falls_back() -> None:
    assert ranks_for_country(None) == GENERIC_RANKS


def test_generic_ranks_can_be_asked_for_explicitly() -> None:
    """A player who does not want Hauptmanns gets the plain ladder."""
    country = _country("Germany")
    assert ranks_for_country(country) != GENERIC_RANKS
    assert ranks_for_country(country, use_country_ranks=False) == GENERIC_RANKS


@pytest.mark.parametrize("skill", [Skill.Random, Skill.Player, Skill.Client])
def test_a_skill_that_is_not_a_rung_reads_as_the_bottom(skill: Skill) -> None:
    """Random, Player and Client are skills to DCS but not steps of a career."""
    assert rank_for_skill(skill, None) == GENERIC_RANKS[0]


def test_ground_units_never_see_cadet() -> None:
    """Blue shares one setting between its pilots and its tanks."""
    from game.dcs.skills import ground_skill

    assert ground_skill(CADET_SKILL) is Skill.Average
    for skill in SKILL_LADDER[1:]:
        assert ground_skill(skill) is skill


def test_only_pilots_are_offered_cadet() -> None:
    from game.settings.skilloption import GROUND_SKILL_CHOICES, PILOT_SKILL_CHOICES

    assert PILOT_SKILL_CHOICES == ["Cadet", *GROUND_SKILL_CHOICES]
    assert "Cadet" not in GROUND_SKILL_CHOICES
