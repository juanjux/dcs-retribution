"""How the settings dialog is laid out, as the settings themselves describe it.

Three things the pages rely on and nothing else enforces: a section a switch owns is
not also listed as a section of its own, a box within a section does not leak into
the section's own rows, and neither trick hides a setting from anything reading them
all -- the API among them.
"""

from __future__ import annotations

from game.settings import Settings
from game.settings.settings import (
    BUILDING_REPAIR_TUNING_SECTION,
    CAMPAIGN_MANAGEMENT_PAGE,
    GROUND_OBJECT_REPAIR_TUNING_SECTION,
    HQ_AUTOMATION_SECTION,
    LIVE_PILOTS_MORALE_EVENTS_SECTION,
    LIVE_PILOTS_MORALE_SECTION,
    LIVE_PILOTS_PAGE,
)


def test_a_section_a_switch_owns_is_not_listed_on_its_page() -> None:
    """It is reached from the gear on the switch, so listing it offers it twice."""
    assert GROUND_OBJECT_REPAIR_TUNING_SECTION not in list(
        Settings.sections(CAMPAIGN_MANAGEMENT_PAGE)
    )
    assert (
        GROUND_OBJECT_REPAIR_TUNING_SECTION in Settings.sections_opened_from_a_switch()
    )
    assert list(
        Settings.fields(CAMPAIGN_MANAGEMENT_PAGE, GROUND_OBJECT_REPAIR_TUNING_SECTION)
    ), "and it still has its settings"


def test_the_switch_that_owns_it_says_so() -> None:
    owners = [
        name
        for name, description in Settings.fields(
            CAMPAIGN_MANAGEMENT_PAGE, HQ_AUTOMATION_SECTION
        )
        if description.opens_section == GROUND_OBJECT_REPAIR_TUNING_SECTION
    ]
    assert owners == ["automate_ground_object_repairs"]


def test_a_box_within_a_section_is_not_one_of_its_rows() -> None:
    own = [
        name
        for name, _ in Settings.fields(LIVE_PILOTS_PAGE, LIVE_PILOTS_MORALE_SECTION)
    ]
    assert own == ["morale_enabled"]

    box = [
        name
        for name, _ in Settings.fields(
            LIVE_PILOTS_PAGE,
            LIVE_PILOTS_MORALE_SECTION,
            LIVE_PILOTS_MORALE_EVENTS_SECTION,
        )
    ]
    assert "morale_lost_aircraft" in box
    assert "morale_state_shaken" in box
    assert not set(own) & set(box)


def test_the_boxes_are_listed_in_the_order_they_are_declared() -> None:
    assert list(Settings.subsections(LIVE_PILOTS_PAGE, LIVE_PILOTS_MORALE_SECTION)) == [
        LIVE_PILOTS_MORALE_EVENTS_SECTION
    ]


def test_nothing_is_hidden_from_a_reader_that_wants_everything() -> None:
    """all_fields is what the API walks, and it must see the whole of it."""
    every = {name for name, _ in Settings.all_fields()}
    for name in ("sam_repair_budget_fraction", "morale_state_shaken", "morale_enabled"):
        assert name in every

    by_page = {
        name
        for page in Settings.pages()
        for section in Settings.sections(page)
        for name, _ in Settings.fields(page, section)
    }
    assert by_page < every, "the page walk is the smaller of the two, on purpose"


def test_both_repair_tuning_sections_are_behind_their_own_switch() -> None:
    listed = list(Settings.sections(CAMPAIGN_MANAGEMENT_PAGE))
    owned = Settings.sections_opened_from_a_switch()
    for section in (
        GROUND_OBJECT_REPAIR_TUNING_SECTION,
        BUILDING_REPAIR_TUNING_SECTION,
    ):
        assert section not in listed
        assert section in owned


def test_a_setting_another_one_takes_over_says_who_decides() -> None:
    """enabled_when is what greys a setting out; nothing else knows to."""
    settings = Settings()
    by_name = dict(Settings.all_fields())

    levelling = by_name["ai_pilot_levelling"].enabled_when
    assert levelling is not None
    settings.live_pilots_enabled = False
    assert levelling(settings), "his own switch while Live Pilots is off"
    settings.live_pilots_enabled = True
    assert not levelling(settings), "and Live Pilots levels them instead"

    budget = by_name["building_repair_budget_percent"].enabled_when
    assert budget is not None
    settings.automate_building_repairs = False
    assert not budget(settings)
    settings.automate_building_repairs = True
    assert budget(settings)

    assert (
        by_name["building_repair_turns"].enabled_when is None
    ), "your own repairs take the same turns, so it stands whoever ordered them"


def test_the_settings_that_cost_frames_live_with_the_other_ones() -> None:
    performance = {
        name for name, _ in Settings.fields("Mission Generator", "Performance")
    }
    for name in (
        "max_frontline_width",
        "ground_start_scenery_remove_triggers",
        "ground_start_trucks",
        "ground_start_trucks_roadbase",
        "ground_start_ground_power_trucks",
        "ground_start_ground_power_trucks_roadbase",
        "ground_start_airbase_statics_farps_remove",
    ):
        assert name in performance


def test_naming_the_pilots_is_not_a_switch_of_its_own() -> None:
    """It is most of what Live Pilots is for, so it rides on it."""
    assert "live_pilots_show_names" not in dict(Settings.all_fields())
