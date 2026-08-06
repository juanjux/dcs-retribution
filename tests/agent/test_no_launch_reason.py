"""A base that cannot launch says WHY, because the three reasons differ in what to do.

A cratered runway is repairable and worth cratering on an enemy field. A sunk carrier
is neither. A FOB with no helipads has no runway at all — reporting it as "runway
damaged" invites an OCA/Runway package against something that cannot be cratered and
a wait for a repair that never comes.

These build the REAL control-point classes (bypassing __init__, which wants a whole
theater) instead of duck-typed fakes. An earlier version of this file used fakes that
declared ``runway_is_destroyable`` as a method; the real one is a property, so the
tests passed while the live call raised TypeError and every turn_context 500'd.
A fake is only as good as its fidelity to the interface it stands in for.
"""

from __future__ import annotations

from typing import Any

from game.agent import views
from game.theater.controlpoint import Airfield, Carrier, Fob


def _bare(cls: type) -> Any:
    """An instance without running __init__, which needs a full campaign."""
    return object.__new__(cls)


def test_airfield_that_cannot_launch_is_a_damaged_runway() -> None:
    assert views._no_launch_reason(_bare(Airfield)) == "runway_damaged"


def test_carrier_that_cannot_launch_has_lost_its_hull() -> None:
    assert views._no_launch_reason(_bare(Carrier)) == "hull_sunk"


def test_fob_without_helipads_is_not_a_damaged_runway() -> None:
    assert views._no_launch_reason(_bare(Fob)) == "no_launch_facilities"


def test_runway_is_destroyable_is_a_property_on_every_control_point() -> None:
    """Guards the exact slip above: read as an attribute, never called."""
    for cls in (Airfield, Carrier, Fob):
        assert isinstance(
            getattr(cls, "runway_is_destroyable"), property
        ), f"{cls.__name__}.runway_is_destroyable is no longer a property"
