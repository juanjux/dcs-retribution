"""A base that cannot launch says WHY, because the three reasons differ in what to do.

A cratered runway is repairable and worth cratering on an enemy field. A sunk carrier
is neither. A FOB with no helipads has no runway at all — reporting it as "runway
damaged" invites an OCA/Runway package against something that cannot be cratered and
a wait for a repair that never comes.
"""

from __future__ import annotations

from typing import Any

from game.agent import views
from game.theater.controlpoint import Fob


class _Airfield:
    """Duck-typed airfield: destroyable runway, so a failure means it is damaged."""

    def runway_is_destroyable(self) -> bool:
        return True


class _Carrier:
    """A carrier's 'runway' dies with the hull, and is not destroyable on its own."""

    def runway_is_destroyable(self) -> bool:
        return False


def test_airfield_that_cannot_launch_is_a_damaged_runway() -> None:
    assert views._no_launch_reason(_Airfield()) == "runway_damaged"


def test_carrier_that_cannot_launch_has_lost_its_hull() -> None:
    assert views._no_launch_reason(_Carrier()) == "hull_sunk"


def test_fob_without_helipads_is_not_a_damaged_runway() -> None:
    """Fob.runway_is_operational() means 'has somewhere to launch from', not a runway
    state — a Fob has no runway and runway_is_destroyable() is False for it."""
    fob: Any = object.__new__(Fob)  # the real class; __init__ needs a whole theater
    assert views._no_launch_reason(fob) == "no_launch_facilities"
