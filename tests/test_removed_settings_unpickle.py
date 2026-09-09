"""A save still names the classes a removed feature stored in it.

An enum member is pickled by reference -- module plus class name -- so deleting the
class stops every campaign that ever stored one from loading at all, not just the
setting it belonged to. Fast forward's two enums were in every save written before
they went, which is a whole campaign that will not open.
"""

from __future__ import annotations

import io

from game.persistency import MigrationUnpickler, REMOVED_CLASSES, RemovedEnum


def test_the_removed_classes_are_named_where_the_unpickler_looks() -> None:
    assert {"FastForwardStopCondition", "CombatResolutionMethod"} <= REMOVED_CLASSES


def test_a_save_that_names_a_removed_enum_still_loads() -> None:
    """The value is thrown away; what matters is that it resolves to something."""
    for name in REMOVED_CLASSES:
        resolved = MigrationUnpickler(io.BytesIO(b"")).find_class(
            "game.settings.settings", name
        )
        assert resolved is RemovedEnum
        # An enum member unpickles by calling the class with its value.
        assert isinstance(resolved("Player startup time"), RemovedEnum)


def test_a_class_that_still_exists_is_left_alone() -> None:
    from game.settings.settings import NightMissions

    resolved = MigrationUnpickler(io.BytesIO(b"")).find_class(
        "game.settings.settings", "NightMissions"
    )
    assert resolved is NightMissions
