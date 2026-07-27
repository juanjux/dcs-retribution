import pytest

from game import persistency
from game.data import radar_db
from game.data.groups import GroupRole
from game.data.units import UnitClass
from game.layout import LAYOUTS


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # ForceGroup/layout preset loading reads from the DCS saved-game folder,
    # which is only configured once the app boots. Point it at an empty temp
    # dir so loading falls back to the bundled resources/ presets.
    persistency.setup(
        str(tmp_path_factory.mktemp("saved_games")),
        prefer_liberation_payloads=False,
        port=0,
    )


# Every SAM layout must field TWO guidance radars so a single ARM cannot
# blind the whole site. The contract has two halves that must stay in
# lockstep: the layout YAML's unit_count asks for 2, and the shared .miz
# template actually carries >= 2 positions for the slot (generate_units
# raises LayoutException past the template's position count).
# The slot named here is the site's engagement/guidance radar: "Track Radar"
# for the generic and named battery layouts, "S-300 Site TR" on the S-300
# template, the SA-6's combined 1S91 STR (its "Search Radar" slot), the mixed
# site's SNR-75 (mapped to the "S-300 Site CP" slot), the Patriot-family
# STR ("Patriot Battery 0"), and the NASAMS Sentinel / Sky Sabre Giraffe
# ("Search Radar" - AMRAAM/CAMM engagement stops without them).
# Known limitation, deliberately out of scope: presets that route a lone
# search-track radar through a GENERIC layout's "Search Radar" slot
# (NASAMS-B/C, IRIS-T SLM, THAAD) keep a single engagement radar - doubling
# that slot would also double the pure search radars of every generic site.
GUIDANCE_RADAR_SLOTS = [
    ("2 Launcher Site", "Track Radar"),
    ("4 Launcher Site (Circle)", "Track Radar"),
    ("4 Launcher Site (Semicircle)", "Track Radar"),
    ("6 Launcher Site (Circle)", "Track Radar"),
    ("6 Launcher Site (Semicircle)", "Track Radar"),
    ("NASAMS 3 Site", "Track Radar"),
    ("NASAMS 3 Site", "Search Radar"),
    ("Sky Sabre Battery", "Search Radar"),
    ("S-350 Site", "Track Radar"),
    ("SA-2 Battery (4 Launcher Circle)", "Track Radar"),
    ("SA-2 Battery (4 Launcher Semicircle)", "Track Radar"),
    ("SA-2 Battery (6 Launcher Circle)", "Track Radar"),
    ("SA-2 Battery (6 Launcher Semicircle)", "Track Radar"),
    ("SA-3 Site (4 Launcher Circle)", "Track Radar"),
    ("SA-3 Site (4 Launcher Semicircle)", "Track Radar"),
    ("SA-5 Legacy Site (Circle)", "Track Radar"),
    ("SA-5 Legacy Site (Semicircle)", "Track Radar"),
    ("S-300 Site", "S-300 Site TR"),
    ("HQ-22 Battery", "S-300 Site TR"),
    ("SA-2/SA-3 Mixed Site", "S-300 Site TR"),
    ("SA-2/SA-3 Mixed Site", "S-300 Site CP"),
    ("SA-6 Reinforced Site (Circle)", "Search Radar"),
    ("SA-6 Reinforced Site (Semicircle)", "Search Radar"),
    ("Patriot Battery", "Patriot Battery 0"),
    ("MIM-104 Patriot Battery", "Patriot Battery 0"),
    ("LvS-103A Battery", "Patriot Battery 0"),
    ("LvS-103A Mobile Battery", "Patriot Battery 0"),
    ("LvS-103B Battery", "Patriot Battery 0"),
    ("LvS-103B Mobile Battery", "Patriot Battery 0"),
]


@pytest.mark.parametrize("layout_name,slot", GUIDANCE_RADAR_SLOTS)
def test_sam_layout_fields_two_guidance_radars(layout_name: str, slot: str) -> None:
    layout = LAYOUTS.by_name(layout_name)
    unit_groups = [ug for ug in layout.all_unit_groups if ug.name == slot]
    assert unit_groups, f"{layout_name} lost its '{slot}' slot"
    (unit_group,) = unit_groups
    assert unit_group.unit_count == [2], (
        f"{layout_name} '{slot}' must ask for exactly 2 guidance radars, "
        f"got unit_count={unit_group.unit_count}"
    )
    assert unit_group.max_size >= 2, (
        f"{layout_name} '{slot}' has only {unit_group.max_size} position(s) in "
        f"its .miz template; generate_units would raise LayoutException"
    )


# GUIDANCE_RADAR_SLOTS is a hand-maintained allowlist: it pins the guidance
# slots we know about, but a *new* SAM layout that ships a single engagement
# radar would simply not appear in it and pass CI silently. The companion guard
# below closes that hole by DISCOVERING every dedicated engagement radar from
# the layout data itself and asserting redundancy on each -- so a new
# single-radar site fails CI until it is either doubled or explicitly named as a
# deliberate single (see below), without anyone having to remember to extend the
# hand-list.
#
# A "dedicated engagement radar" is a group whose class is TrackRadar (the
# generic launcher-site layouts) or whose explicit units are in
# radar_db.TRACK_RADARS (the named battery layouts: S-300/Patriot/SA-6 etc.).
# TELAR systems (SA-11/17, Tor, Roland, Tunguska) are excluded by construction --
# their radar *is* the launcher, so there is no separate radar to blind, and they
# carry no TrackRadar group. Generic "Search Radar" slots (SearchRadar/
# SearchTrackRadar classes -- e.g. NASAMS-B/C, IRIS-T SLM, THAAD routed through a
# generic layout) are also out of scope, matching the documented limitation on
# GUIDANCE_RADAR_SLOTS.
#
# A deliberate single-radar layout (e.g. the regiment-by-authoring pattern:
# several single-radar battalions + a shared EWR) is single on purpose, not a
# redundancy gap. The convention is to name it with "Single Radar" -- the
# documented, self-describing escape hatch this guard honors.
_DELIBERATE_SINGLE_RADAR_MARKER = "Single Radar"

_AIR_DEFENSE_TASKS = set(GroupRole.AIR_DEFENSE.tasks)


def _dedicated_engagement_radar_slots() -> list[tuple[str, str, list[int]]]:
    slots: list[tuple[str, str, list[int]]] = []
    for layout in LAYOUTS.layouts:
        if not any(task in _AIR_DEFENSE_TASKS for task in layout.tasks):
            continue
        for unit_group in layout.all_unit_groups:
            is_track_class = UnitClass.TRACK_RADAR in unit_group.unit_classes
            is_track_typed = bool(set(unit_group.unit_types) & radar_db.TRACK_RADARS)
            if is_track_class or is_track_typed:
                slots.append((layout.name, unit_group.name, unit_group.unit_count))
    return slots


def test_no_engagement_radar_layout_escapes_the_redundancy_contract() -> None:
    """Every discovered dedicated engagement radar must field two radars, unless
    the layout is a deliberate single (named with "Single Radar"). Guards against
    a new SAM layout slipping a single guidance radar past the hand-maintained
    GUIDANCE_RADAR_SLOTS list."""
    single_radar_gaps = [
        (name, slot, count)
        for name, slot, count in _dedicated_engagement_radar_slots()
        if _DELIBERATE_SINGLE_RADAR_MARKER not in name and count != [2]
    ]
    assert not single_radar_gaps, (
        "These layouts field a single dedicated engagement radar, so one HARM "
        "blinds the whole site -- double the guidance slot to unit_count [2], or "
        f"if it is intentional, name the layout with "
        f"'{_DELIBERATE_SINGLE_RADAR_MARKER}': {single_radar_gaps}"
    )
