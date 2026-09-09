"""An EWR marker must honour a campaign's ground_forces pin.

Every other air-defence band asks get_unit_group_for_task, which reads the campaign's
override before falling back to a random roll. generate_ewrs went straight to the
random roll, so a pin onto an EWR marker was parsed, matched the marker's task, passed
the faction gate -- and was then ignored, with nothing logged. That is the whole path
the GPS jamming feature depends on, since a jamming site is pinned onto an EWR marker.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock

from game.data.groups import GroupTask
from game.theater.start_generator import AirbaseGroundObjectGenerator


def _generator_with_one_ewr_marker(marker: Any) -> AirbaseGroundObjectGenerator:
    generator = object.__new__(AirbaseGroundObjectGenerator)
    control_point = MagicMock()
    control_point.preset_locations.ewrs = [marker]
    generator.control_point = control_point
    # armed_forces is a property reading through the game, so it is reached that way
    # rather than assigned.
    generator.game = MagicMock()
    return generator


def test_an_ewr_marker_is_offered_to_the_override() -> None:
    marker = MagicMock()
    generator = _generator_with_one_ewr_marker(marker)
    pinned = MagicMock()
    generator.get_unit_group_for_task = MagicMock(return_value=pinned)  # type: ignore[method-assign]
    generator.generate_ground_object_from_group = MagicMock()  # type: ignore[method-assign]

    generator.generate_ewrs()

    generator.get_unit_group_for_task.assert_called_once_with(
        marker, GroupTask.EARLY_WARNING_RADAR
    )
    generator.generate_ground_object_from_group.assert_called_once_with(
        pinned, marker, GroupTask.EARLY_WARNING_RADAR
    )
    # The random roll is what get_unit_group_for_task falls back to; reaching for it
    # here would mean the override was skipped again.
    coalition_for = cast(MagicMock, generator.game.coalition_for)
    coalition_for.return_value.armed_forces.random_group_for_task.assert_not_called()


def test_nothing_generates_when_the_faction_has_no_ewr_at_all() -> None:
    generator = _generator_with_one_ewr_marker(MagicMock())
    generator.get_unit_group_for_task = MagicMock(return_value=None)  # type: ignore[method-assign]
    generator.generate_ground_object_from_group = MagicMock()  # type: ignore[method-assign]

    generator.generate_ewrs()

    generator.generate_ground_object_from_group.assert_not_called()
