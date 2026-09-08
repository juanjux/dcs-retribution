"""How the settings dialog is laid out, as the settings themselves describe it.

Three things the pages rely on and nothing else enforces: a section a switch owns is
not also listed as a section of its own, a box within a section does not leak into
the section's own rows, and neither trick hides a setting from anything reading them
all -- the API among them.
"""

from __future__ import annotations

from game.settings import Settings
from game.settings.settings import (
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
