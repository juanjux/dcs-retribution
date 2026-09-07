"""Unit tests for the Skynet IADS radius.

Skynet is handed every SAM site, EWR, comms tower and power station on the map, for
both coalitions, and its cost grows with what it manages. The radius hands it only what
is near the fighting.

The point that needs guarding is what happens to what is left out. It is *not* removed
from the mission -- that is perf_culling's job, a different setting -- so a flight that
strays off the planned route still meets it. But Retribution generates ground SAMs at
alarm state green when perf_red_alert_state is off, on the assumption that Skynet will
wake them; a site nobody is going to wake has to come up red instead, or the radius
would quietly disarm the map.
"""

from types import SimpleNamespace
from typing import Any

from dcs.task import OptAlarmState

from game.game import Game
from game.missiongenerator.tgogenerator import GroundObjectGenerator

ALARM_STATE_RED = 2
ALARM_STATE_GREEN = 1


class _Zone:
    """Stands in for a culling zone. skynet_culled only measures distance to one."""

    def __init__(self, distance: float) -> None:
        self.distance = distance

    def distance_to_point(self, _position: Any) -> float:
        return self.distance


def _game(radius: int, *distances: float) -> Any:
    game = SimpleNamespace(settings=SimpleNamespace(perf_skynet_iads_radius=radius))
    # Name-mangled: the attribute Game.skynet_culled reads is _Game__culling_zones.
    setattr(game, "_Game__culling_zones", [_Zone(d) for d in distances])
    return game


def _culled(radius: int, *distances: float) -> bool:
    tgo: Any = SimpleNamespace(position=None)
    return Game.skynet_culled(_game(radius, *distances), tgo)


def test_a_radius_of_zero_leaves_the_whole_map_in_the_network() -> None:
    """The default. Nothing changes for a campaign that never touches the setting."""
    assert not _culled(0, 5_000_000.0)


def test_with_no_conflict_located_nothing_is_culled() -> None:
    """An empty zone list would otherwise cull everything and hand Skynet nothing."""
    assert not _culled(100)


def test_a_site_inside_the_radius_stays_in_the_network() -> None:
    assert not _culled(100, 99_000.0)


def test_a_site_outside_every_zone_is_left_out() -> None:
    assert _culled(100, 150_000.0, 200_000.0)


def test_one_zone_in_reach_is_enough() -> None:
    """Near the front but far from every package target is still near the fighting."""
    assert not _culled(100, 400_000.0, 12_000.0)


def _alarm_state(
    *, radius: int, distance: float, red_alert: bool, skynet: bool = True
) -> int:
    """The alarm state a ground SAM outside/inside the radius is generated at."""
    game = _game(radius, distance)
    game.settings.perf_red_alert_state = red_alert
    game.settings.plugin_option = lambda name: skynet and name == "skynetiads"
    game.skynet_culled = lambda tgo: Game.skynet_culled(game, tgo)

    generator: Any = GroundObjectGenerator.__new__(GroundObjectGenerator)
    generator.game = game
    # Not an EwrGroundObject, so the EWR branch does not decide this for us.
    generator.ground_object = SimpleNamespace(position=None)

    group: Any = SimpleNamespace(points=[SimpleNamespace(tasks=[])])
    GroundObjectGenerator.set_alarm_state(generator, group)
    task = group.points[0].tasks[0]
    assert isinstance(task, OptAlarmState)
    return int(task.value)


def test_a_site_left_out_of_the_network_comes_up_red() -> None:
    """The whole point: nobody is coming to wake it, so it wakes itself."""
    assert (
        _alarm_state(radius=100, distance=500_000.0, red_alert=False) == ALARM_STATE_RED
    )


def test_a_site_inside_the_network_still_starts_dark() -> None:
    """Skynet is going to drive it, so the perf toggle keeps its meaning."""
    assert (
        _alarm_state(radius=100, distance=10_000.0, red_alert=False)
        == ALARM_STATE_GREEN
    )


def test_the_radius_does_not_arm_anything_when_skynet_is_off() -> None:
    """With no IADS plugin there is no network to be outside of."""
    assert (
        _alarm_state(radius=100, distance=500_000.0, red_alert=False, skynet=False)
        == ALARM_STATE_GREEN
    )
