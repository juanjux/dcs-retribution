"""Aimpoint selection for missile sites (Scud, ATACMS).

A control point's position is a campaign-map coordinate, so firing at it dropped
every salvo in whatever field sat at the middle of the airfield. These cover the
preference for real ground objects and the fallback that keeps a bare base from
silently losing its fire task.
"""

from types import SimpleNamespace
from typing import Any, List, Tuple

from dcs.mapping import Point

from game.missiongenerator.tgogenerator import MissileSiteGenerator


class _Generator(MissileSiteGenerator):
    """A generator with just the attributes the aimpoint search reads.

    ``missile_site_range`` is derived from the generated DCS group, which needs a
    whole mission to exist; the range itself is not what these tests are about.
    """

    def __init__(
        self, ground_object: Any, game: Any, site_range: int, mission: Any = None
    ) -> None:
        self.ground_object = ground_object
        self.game = game
        self.m = mission
        self._site_range = site_range

    @property
    def missile_site_range(self) -> int:
        return self._site_range


def _tgo(x: float, y: float, *, category: str = "ammo", dead: bool = False) -> Any:
    return SimpleNamespace(
        position=Point(x, y, None),  # type: ignore[arg-type]
        category=category,
        is_dead=dead,
    )


def _control_point(x: float, y: float, *, blue: bool, tgos: List[Any]) -> Any:
    return SimpleNamespace(
        position=Point(x, y, None),  # type: ignore[arg-type]
        captured=blue,
        ground_objects=tgos,
    )


def _generator(cps: List[Any], site_range: int = 100000) -> _Generator:
    site = SimpleNamespace(
        position=Point(0, 0, None),  # type: ignore[arg-type]
        control_point=SimpleNamespace(captured=False),
    )
    game = SimpleNamespace(theater=SimpleNamespace(controlpoints=cps))
    return _Generator(site, game, site_range)


def _coords(points: List[Point]) -> List[Tuple[float, float]]:
    return sorted((p.x, p.y) for p in points)


def test_prefers_real_ground_objects_over_the_map_coordinate() -> None:
    cp = _control_point(
        50000, 0, blue=True, tgos=[_tgo(50500, 0), _tgo(49500, 0, category="fuel")]
    )
    assert _coords(_generator([cp]).possible_missile_targets()) == [
        (49500.0, 0.0),
        (50500.0, 0.0),
    ]


def test_falls_back_to_the_map_coordinate_when_the_base_is_bare() -> None:
    cp = _control_point(50000, 0, blue=True, tgos=[])
    assert _coords(_generator([cp]).possible_missile_targets()) == [(50000.0, 0.0)]


def test_skips_dead_objects_and_ships() -> None:
    cp = _control_point(
        50000,
        0,
        blue=True,
        tgos=[
            _tgo(50100, 0, dead=True),
            _tgo(50200, 0, category="ship"),
            _tgo(50300, 0, category="fuel"),
        ],
    )
    assert _coords(_generator([cp]).possible_missile_targets()) == [(50300.0, 0.0)]


def test_a_base_of_only_wrecks_and_ships_still_falls_back() -> None:
    cp = _control_point(
        50000,
        0,
        blue=True,
        tgos=[_tgo(50100, 0, dead=True), _tgo(50200, 0, category="ship")],
    )
    assert _coords(_generator([cp]).possible_missile_targets()) == [(50000.0, 0.0)]


def test_ignores_friendly_control_points() -> None:
    cp = _control_point(50000, 0, blue=False, tgos=[_tgo(50500, 0)])
    assert _generator([cp]).possible_missile_targets() == []


def test_range_is_measured_to_the_aimpoint_not_the_base() -> None:
    """The far depot is out of reach even though its base's centre is not."""
    cp = _control_point(50000, 0, blue=True, tgos=[_tgo(55000, 0), _tgo(70000, 0)])
    assert _coords(_generator([cp], site_range=60000).possible_missile_targets()) == [
        (55000.0, 0.0)
    ]


def _mission_holding(unit_types: List[str]) -> Any:
    group = SimpleNamespace(units=[SimpleNamespace(type=t) for t in unit_types])

    def find_group(name: str) -> Any:
        return group

    return SimpleNamespace(find_group=find_group)


def _error_for(*unit_types: str) -> int:
    site = SimpleNamespace(
        position=Point(0, 0, None),  # type: ignore[arg-type]
        control_point=SimpleNamespace(captured=False),
        groups=[SimpleNamespace(group_name="site")],
    )
    game = SimpleNamespace(theater=SimpleNamespace(controlpoints=[]))
    generator = _Generator(site, game, 100000, _mission_holding(list(unit_types)))
    return generator.aimpoint_error


def test_a_scud_misses_by_a_quarter_kilometre() -> None:
    """450 m CEP, doubled: an inertial missile from the sixties."""
    assert _error_for("Scud_B") == 900


def test_an_atacms_lands_near_where_it_was_pointed() -> None:
    """25 m CEP, doubled: eighteen times better than the Scud."""
    assert _error_for("CH_M270A1_ATACMS") == 50


def test_an_unlisted_launcher_takes_the_default() -> None:
    assert _error_for("SomeModdedLauncher") == 300


def test_the_least_accurate_launcher_sets_the_error() -> None:
    assert _error_for("CH_M270A1_ATACMS", "Scud_B") == 900


def test_support_vehicles_do_not_drag_a_site_to_the_default() -> None:
    """A Scud site is a Scud site even though its fuel truck is in no table."""
    assert _error_for("Scud_B", "Ural-375") == 900
