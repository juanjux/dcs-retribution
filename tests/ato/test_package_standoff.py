from types import SimpleNamespace

from game.ato.package import Package
from game.utils import nautical_miles


def _fake_package(waypoints: object, standoff: object) -> Package:
    # waypoints_need_regeneration/max_standoff_range only touch these attributes, so a
    # lightweight stand-in avoids building a whole campaign just to exercise the logic.
    return SimpleNamespace(  # type: ignore[return-value]
        waypoints=waypoints,
        max_standoff_range=lambda: standoff,
    )


def test_waypoints_regenerate_when_never_built() -> None:
    package = _fake_package(waypoints=None, standoff=nautical_miles(160))
    assert Package.waypoints_need_regeneration(package) is True


def test_waypoints_kept_when_standoff_range_unchanged() -> None:
    waypoints = SimpleNamespace(standoff_range=nautical_miles(160))
    package = _fake_package(waypoints=waypoints, standoff=nautical_miles(160))
    assert Package.waypoints_need_regeneration(package) is False


def test_waypoints_regenerate_when_standoff_range_changes() -> None:
    # Payload swapped from a Kh-22 (160nm) loadout to short-range bombs.
    waypoints = SimpleNamespace(standoff_range=nautical_miles(160))
    package = _fake_package(waypoints=waypoints, standoff=None)
    assert Package.waypoints_need_regeneration(package) is True

    # And the reverse: unranged loadout swapped up to a stand-off weapon.
    waypoints = SimpleNamespace(standoff_range=None)
    package = _fake_package(waypoints=waypoints, standoff=nautical_miles(160))
    assert Package.waypoints_need_regeneration(package) is True
