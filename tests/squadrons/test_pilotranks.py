"""Rank ladders, the naming choices, and the Cadet rung pydcs was missing."""

from typing import List

import pytest
from dcs.countries import country_dict
from dcs.country import Country
from dcs.unit import Skill

from game.dcs.skills import CADET_SKILL, SKILL_LADDER, ground_skill
from game.settings import ChoicesOption, Settings
from game.settings.skilloption import GROUND_SKILL_CHOICES, PILOT_SKILL_CHOICES
from game.squadrons.pilotranks import (
    COUNTRY_RANKS,
    GENERIC_RANKS,
    RANK_NAMES_COUNTRY,
    RANK_NAMES_CUSTOM,
    RANK_NAMES_GENERIC,
    RANK_NAMES_SKILL,
    RankLadder,
    rank_for_skill,
    ranks_for,
)


def _country(name: str) -> Country:
    for factory in country_dict.values():
        country = factory()
        if country.name == name:
            return country
    raise AssertionError(f"no such DCS country: {name}")


def _abbreviations(ladder: RankLadder) -> List[str]:
    return [rank.abbreviation for rank in ladder]


# --- the engine ------------------------------------------------------------


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


def test_ground_units_never_see_cadet() -> None:
    """Blue shares one setting between its pilots and its tanks."""
    assert ground_skill(CADET_SKILL) is Skill.Average
    for skill in SKILL_LADDER[1:]:
        assert ground_skill(skill) is skill


def test_only_pilots_are_offered_cadet() -> None:
    assert PILOT_SKILL_CHOICES == ["Cadet", *GROUND_SKILL_CHOICES]
    assert "Cadet" not in GROUND_SKILL_CHOICES


# --- the ladders -----------------------------------------------------------


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
    country_name: str, expected: List[str]
) -> None:
    ladder = ranks_for(RANK_NAMES_COUNTRY, _country(country_name))
    assert _abbreviations(ladder) == expected


@pytest.mark.parametrize(
    "country_name", ["Combined Joint Task Forces Blue", "Insurgents"]
)
def test_countries_with_no_ladder_of_their_own_fall_back(country_name: str) -> None:
    assert ranks_for(RANK_NAMES_COUNTRY, _country(country_name)) == GENERIC_RANKS


def test_no_country_falls_back() -> None:
    assert ranks_for(RANK_NAMES_COUNTRY, None) == GENERIC_RANKS


def test_generic_ranks_can_be_asked_for_explicitly() -> None:
    """A player who does not want Hauptmanns gets the plain ladder."""
    germany = _country("Germany")
    assert ranks_for(RANK_NAMES_COUNTRY, germany) != GENERIC_RANKS
    assert ranks_for(RANK_NAMES_GENERIC, germany) == GENERIC_RANKS


def test_skill_names_are_the_dcs_levels() -> None:
    ladder = ranks_for(RANK_NAMES_SKILL, _country("Germany"))
    assert _abbreviations(ladder) == ["Cdt", "Avg", "Gdd", "Hig", "Exc"]
    assert [rank.name for rank in ladder] == [skill.value for skill in SKILL_LADDER]


def test_custom_names_are_used_as_typed() -> None:
    ladder = ranks_for(
        RANK_NAMES_CUSTOM, None, ["Novato", "Piloto", "Veterano", "Jefe", "As"]
    )
    assert _abbreviations(ladder) == ["Novato", "Piloto", "Veterano", "Jefe", "As"]


def test_a_blank_custom_box_keeps_its_generic_rung() -> None:
    ladder = ranks_for(RANK_NAMES_CUSTOM, None, ["Novato", "  ", "", "Jefe", "As"])
    assert _abbreviations(ladder) == ["Novato", "1stLt", "Capt", "Jefe", "As"]


def test_an_unknown_naming_falls_back_rather_than_raising() -> None:
    assert ranks_for("something a future version wrote", None) == GENERIC_RANKS


@pytest.mark.parametrize("skill", [Skill.Random, Skill.Player, Skill.Client])
def test_a_skill_that_is_not_a_rung_reads_as_the_bottom(skill: Skill) -> None:
    """Random, Player and Client are skills to DCS but not steps of a career."""
    assert rank_for_skill(skill, GENERIC_RANKS) == GENERIC_RANKS[0]


# --- the settings ----------------------------------------------------------


def test_the_setting_offers_exactly_the_namings_that_exist() -> None:
    """settings.py cannot import the constants without a cycle, so pin them here."""
    (description,) = [
        d
        for n, d in Settings.fields("Live Pilots", "General")
        if n == "live_pilots_rank_names"
    ]
    assert isinstance(description, ChoicesOption)
    assert list(description.choices.values()) == [
        RANK_NAMES_COUNTRY,
        RANK_NAMES_GENERIC,
        RANK_NAMES_SKILL,
        RANK_NAMES_CUSTOM,
    ]


def test_the_custom_boxes_are_hidden_until_they_apply() -> None:
    settings = Settings()
    fields = list(Settings.fields("Live Pilots", "Custom Rank Names"))
    assert len(fields) == len(SKILL_LADDER)

    for _, description in fields:
        assert description.visible_when is not None
        assert not description.visible_when(settings)

    settings.live_pilots_enabled = True
    settings.live_pilots_rank_names = RANK_NAMES_CUSTOM
    for _, description in fields:
        assert description.visible_when is not None
        assert description.visible_when(settings)


def test_the_custom_boxes_start_filled_with_the_generic_ladder() -> None:
    settings = Settings()
    assert [
        settings.live_pilots_rank_cadet,
        settings.live_pilots_rank_average,
        settings.live_pilots_rank_good,
        settings.live_pilots_rank_high,
        settings.live_pilots_rank_excellent,
    ] == _abbreviations(GENERIC_RANKS)
