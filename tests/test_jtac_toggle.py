"""Turning the faction's JTAC off without starting a new campaign.

The JTAC aircraft spawns from the FACTION's has_jtac flag, whose only control was the
checkbox on the new-game wizard's faction page, so a running campaign could not switch
it off. The CTLD plugin's options only change what the JTAC does once it is there.
"""

from __future__ import annotations

from game.settings import Settings


def test_the_jtac_is_on_by_default() -> None:
    """Off by default would silently drop the JTAC from every existing campaign."""
    assert Settings().use_jtac


def test_a_save_written_before_the_option_still_gets_its_jtac() -> None:
    """__setstate__ fills a setting the pickle never had, and the fill must be True."""
    old = Settings()
    state = dict(old.__dict__)
    del state["use_jtac"]

    restored = Settings.__new__(Settings)
    restored.__setstate__(state)

    assert restored.use_jtac


def test_it_sits_on_the_mission_generator_page() -> None:
    import dataclasses

    from game.settings.optiondescription import SETTING_DESCRIPTION_KEY

    (field,) = [f for f in dataclasses.fields(Settings) if f.name == "use_jtac"]
    option = field.metadata[SETTING_DESCRIPTION_KEY]
    assert option.page == "Mission Generator"
    assert option.section == "General"
