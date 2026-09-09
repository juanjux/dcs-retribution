"""What the settings search finds, and what it refuses to.

The refusing is the harder half. A forgiving matcher over two hundred long labels
matches almost everything: before the subsequence was made to stay tight, "napalm"
found "Enable per-squadron pilot limits", which is worse than finding nothing.
"""

from __future__ import annotations

from game.settings import Settings
from game.settings.search import SettingHit, fold, is_subsequence, search


def keys(query: str) -> list[str]:
    return [hit.key for hit in search(query)]


def test_a_word_from_the_label_finds_it() -> None:
    assert "use_auto_fog" in keys("fog")
    assert "perf_skynet_iads_radius" in keys("skynet radius")


def test_every_word_has_to_match() -> None:
    """Words narrow the search; they do not widen it."""
    assert keys("skynet"), "the premise"
    assert not keys("skynet marzipan")


def test_the_page_and_the_section_are_searchable_too() -> None:
    """You remember it was something under Live Pilots before you remember what."""
    assert any(hit.page == "Live Pilots" for hit in search("live pilots"))


def test_the_stored_key_is_searchable() -> None:
    """For when the name in a bug report is the Python one."""
    assert "never_delay_player_flights" in keys("never_delay")


def test_a_typo_still_finds_it_but_ranks_below_the_real_thing() -> None:
    assert "max_frontline_width" in keys("frntline")
    real = search("frontline")
    typo = search("frntline")
    assert real[0].score > typo[-1].score


def test_a_subsequence_scattered_over_a_long_label_is_not_a_match() -> None:
    """The bug this rule exists for: it used to answer with pilot limits."""
    assert not is_subsequence("napalm", fold("Enable per-squadron pilot limits"))
    assert is_subsequence("frntline", fold("Maximum frontline width (km)"))


def test_a_short_word_never_matches_by_subsequence() -> None:
    """Three letters land inside almost any sentence in the right order."""
    assert not is_subsequence("air", "a big irregular")


def test_nothing_typed_finds_nothing() -> None:
    assert search("") == []
    assert search("   ") == []


def test_accents_are_ignored_both_ways() -> None:
    assert fold("Morále") == fold("morale")


def test_the_plugins_own_options_are_searchable() -> None:
    """They are the hardest to find by clicking: nothing says "napalm" until you
    have opened the right plugin's gear."""
    hits = search("napalm")
    assert hits, "Splash Damage carries seven of them"
    assert all(hit.plugin == "splashdamage3" for hit in hits)
    assert all(hit.page == "Mission Plugins" for hit in hits)


def test_a_hit_says_where_it_lives() -> None:
    (hit,) = [h for h in search("skynet radius") if h.key == "perf_skynet_iads_radius"]
    assert hit.where == "Mission Generator › Performance"


def test_a_setting_in_a_box_names_the_box() -> None:
    (hit,) = [
        h for h in search("morale_state_shaken") if h.key == "morale_state_shaken"
    ]
    assert hit.where.endswith("Morale › Morale States")


def test_a_setting_the_campaign_is_not_offering_is_not_offered_here() -> None:
    """visible_when hides rows on the page; the search must not route around it."""
    hidden = [
        name
        for name, description in Settings.all_fields()
        if description.visible_when is not None
    ]
    assert hidden, "the premise: something is conditional"
    settings = Settings()
    for name in hidden:
        description = dict(Settings.all_fields())[name]
        if description.visible_when is not None and not description.visible_when(
            settings
        ):
            assert name not in [h.key for h in search(name, settings)]
            return


def test_a_shorter_label_wins_when_both_match() -> None:
    hits = search("cadet")
    assert hits[0].label == "Cadet"


def test_the_hit_is_what_the_dialog_needs_to_navigate() -> None:
    (hit,) = [h for h in search("skynet radius") if h.key == "perf_skynet_iads_radius"]
    assert isinstance(hit, SettingHit)
    assert hit.page in list(Settings.pages())
    assert hit.section in list(Settings.sections(hit.page))
