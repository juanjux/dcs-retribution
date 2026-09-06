"""A ship group must not generate as N copies of one hull.

Naval layouts mix unit types inside a slot (see layout.NavalLayout), drawing the
extra hulls from the lead hull's own unit family so a screen can mix destroyers,
frigates and a cruiser while a speedboat never turns up in a cruiser's slot.
"""

from typing import Any, Type

import pytest
from dcs.unittype import ShipType
from dcs.ships import (
    KUZNECOW,
    Stennis,
    Type_052B,
    Type_052C,
    Type_054A,
    USS_Arleigh_Burke_IIa,
    speedboat,
)
from game import persistency
from game.armedforces.forcegroup import ForceGroup
from game.data.groups import GroupTask
from game.dcs.shipunittype import ShipUnitType
from game.layout import LAYOUTS
from game.layout.layout import MAX_MIXED_UNIT_TYPES, TgoLayout, TgoLayoutUnitGroup


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Layout/ForceGroup loading reads the DCS saved-game folder, which only
    # exists once the app boots. Point it at an empty temp dir so loading falls
    # back to the bundled resources/ presets.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def _force_group(*ship_types: Type[ShipType]) -> ForceGroup:
    units: list[Any] = [next(ShipUnitType.for_dcs_type(t)) for t in ship_types]
    return ForceGroup(
        name="test navy",
        units=units,
        statics=[],
        tasks=[GroupTask.NAVY],
        layouts=[LAYOUTS.by_name("Naval Two Ship")],
    )


def _slot(layout_name: str, slot_name: str) -> tuple[TgoLayout, TgoLayoutUnitGroup]:
    layout = LAYOUTS.by_name(layout_name)
    for unit_group in layout.all_unit_groups:
        if unit_group.name == slot_name:
            return layout, unit_group
    raise AssertionError(f"{layout_name} has no slot named {slot_name}")


def test_a_multi_hull_navy_generates_a_mixed_slot() -> None:
    layout, unit_group = _slot("Naval Two Ship", "Naval Two Ship")
    force_group = _force_group(Type_052B, Type_052C, Type_054A)
    assert layout.mixes_unit_types(unit_group)

    mixes = 0
    for _ in range(25):
        types = force_group.mixed_dcs_unit_types_for_group(unit_group, Type_052B, 2)
        assert len(types) == 2
        assert Type_052B in types
        assert all(t in (Type_052B, Type_052C, Type_054A) for t in types)
        if len(set(types)) > 1:
            mixes += 1
    # Every slot with alternatives available fields at least two hull types.
    assert mixes == 25


def test_a_single_hull_navy_still_generates_a_uniform_slot() -> None:
    _, unit_group = _slot("Naval Two Ship", "Naval Two Ship")
    force_group = _force_group(USS_Arleigh_Burke_IIa)
    types = force_group.mixed_dcs_unit_types_for_group(
        unit_group, USS_Arleigh_Burke_IIa, 4
    )
    assert types == [USS_Arleigh_Burke_IIa] * 4


def test_mixing_stays_inside_the_lead_hull_family() -> None:
    # A patrol boat has no surface-combatant siblings, so its slot stays uniform
    # rather than putting a destroyer alongside it.
    _, unit_group = _slot("Naval Two Ship", "Naval Two Ship")
    force_group = _force_group(speedboat, USS_Arleigh_Burke_IIa)
    types = force_group.mixed_dcs_unit_types_for_group(unit_group, speedboat, 2)
    assert types == [speedboat] * 2


def test_carriers_never_share_a_slot() -> None:
    # AircraftCarrier is its own family, so a two-carrier faction never doubles
    # up a hull the carrier CP resolves its flagship from.
    _, unit_group = _slot("Naval Two Ship", "Naval Two Ship")
    force_group = _force_group(Stennis, KUZNECOW, USS_Arleigh_Burke_IIa)
    types = force_group.mixed_dcs_unit_types_for_group(unit_group, Stennis, 2)
    assert types == [Stennis] * 2


def test_a_deep_roster_is_capped_at_a_task_group() -> None:
    _, unit_group = _slot("Naval Two Ship", "Naval Two Ship")
    force_group = _force_group(Type_052B, Type_052C, Type_054A, USS_Arleigh_Burke_IIa)
    for _ in range(25):
        types = force_group.mixed_dcs_unit_types_for_group(unit_group, Type_052B, 4)
        assert len(types) == 4
        assert len(set(types)) <= MAX_MIXED_UNIT_TYPES


def test_only_naval_layouts_mix_by_default() -> None:
    # A SAM site's launchers must stay one type; mixing is naval-only.
    for layout_name in ["4 Launcher Site (Circle)", "Armor Group"]:
        try:
            layout = LAYOUTS.by_name(layout_name)
        except KeyError:
            continue
        assert not layout.mix_unit_types, layout_name
        for unit_group in layout.all_unit_groups:
            assert not layout.mixes_unit_types(
                unit_group
            ), f"{layout_name} - {unit_group.name}"


def test_every_naval_layout_mixes() -> None:
    naval = [
        "Carrier Group",
        "Carrier Group with Frigate escort",
        "LHA Group",
        "LHA Group with Frigate escort",
        "Naval Group",
        "Naval Two Ship",
    ]
    for layout_name in naval:
        layout = LAYOUTS.by_name(layout_name)
        assert layout.mix_unit_types, layout_name


def test_the_carrier_screen_accepts_every_surface_combatant() -> None:
    # The screen used to be destroyers only, which both forced four identical
    # hulls and locked the layout out of frigate-only navies.
    _, escort = _slot("Carrier Group", "Carrier Group 1")
    classes = {unit_class.value for unit_class in escort.unit_classes}
    assert {"Destroyer", "Cruiser", "Frigate"} <= classes
