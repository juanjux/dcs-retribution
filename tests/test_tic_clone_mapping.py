"""Tests for mapping TIC (Troops In Contact) clone deaths to campaign units.

The TIC script despawns each late-activated original frontline group and
respawns every unit as its own single-unit group via MOOSE SPAWN. MOOSE
renames the units, so the debriefing cannot find them in front_line_units;
UnitMap.front_line_unit_from_tic_clone recovers the original group name.
"""

from game.unitmap import TIC_CLONE_NAME, UnitMap


def clone_group_of(name: str) -> str | None:
    match = TIC_CLONE_NAME.match(name)
    return match.group("group") if match else None


def test_clone_name_first_generation() -> None:
    # GLSCO_SPAWN.DisjoinGroup: "<group>-<index>" + MOOSE "#NNN-UU" suffixes.
    assert clone_group_of("TIC:unit|2|14|3|-7#001-01") == "TIC:unit|2|14|3|"


def test_clone_name_infantry_formation_member() -> None:
    # Infantry groups already contain TIC's "#" bookend in their own name.
    assert (
        clone_group_of("TIC:unit|2|14|3|#infantry|2|5|200|-12#002-01")
        == "TIC:unit|2|14|3|#infantry|2|5|200|"
    )


def test_clone_name_respawn_generation() -> None:
    # Dismounted infantry respawns from the clone's name, nesting the suffix.
    assert clone_group_of("TIC:unit|2|14|3|-7#001-9#002-01") == "TIC:unit|2|14|3|"


def test_non_clone_names_do_not_match() -> None:
    assert clone_group_of("unit|2|14|3| Unit #1") is None
    assert clone_group_of("TIC:unit|2|14|3|") is None
    assert clone_group_of("Aerial-1-1") is None


def test_unit_map_lookup() -> None:
    unit_map = UnitMap()
    sentinel = object()
    unit_map.front_line_groups["TIC:unit|2|14|3|"] = sentinel  # type: ignore[assignment]
    assert (
        unit_map.front_line_unit_from_tic_clone("TIC:unit|2|14|3|-7#001-01") is sentinel
    )
    assert unit_map.front_line_unit_from_tic_clone("TIC:unit|9|9|9|-1#001-01") is None
    assert unit_map.front_line_unit_from_tic_clone("not a clone") is None


def test_unit_map_lookup_survives_old_pickles() -> None:
    # A UnitMap unpickled from an older save has no front_line_groups attr.
    unit_map = UnitMap()
    del unit_map.front_line_groups
    assert unit_map.front_line_unit_from_tic_clone("TIC:unit|2|1|1|-1#001-01") is None
