"""Target selection for missile sites (Scud, ATACMS, Iskander).

A control point's position is a campaign-map coordinate, so firing at it dropped every
salvo in whatever field sat at the middle of the airfield. These cover the preference
for real objectives and the range bounds -- including the minimum, which several of
these launchers have and none of this used to respect.
"""

from types import SimpleNamespace
from typing import Any, List, Tuple

from dcs.mapping import Point

from game.missiongenerator.tgogenerator import MissileSiteGenerator


class _Generator(MissileSiteGenerator):
    """A generator with just the attributes the target search reads.

    The ranges are derived from the generated DCS group, which needs a whole mission to
    exist; the ranges themselves are not what these tests are about.
    """

    def __init__(
        self, ground_object: Any, game: Any, site_range: int, site_min: int = 0
    ) -> None:
        self.ground_object = ground_object
        self.game = game
        self._site_range = site_range
        self._site_min = site_min

    @property
    def missile_site_range(self) -> int:
        return self._site_range

    @property
    def missile_site_min_range(self) -> int:
        return self._site_min


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


def _generator(
    cps: List[Any], site_range: int = 100000, site_min: int = 0
) -> _Generator:
    site = SimpleNamespace(
        position=Point(0, 0, None),  # type: ignore[arg-type]
        control_point=SimpleNamespace(captured=False),
    )
    game = SimpleNamespace(theater=SimpleNamespace(controlpoints=cps))
    return _Generator(site, game, site_range, site_min)


def _coords(targets: List[Any]) -> List[Tuple[float, float]]:
    return sorted((t.position.x, t.position.y) for t in targets)


def test_it_aims_at_real_objectives() -> None:
    cp = _control_point(
        50000, 0, blue=True, tgos=[_tgo(50500, 0), _tgo(49500, 0, category="fuel")]
    )
    assert _coords(_generator([cp]).possible_missile_targets()) == [
        (49500.0, 0.0),
        (50500.0, 0.0),
    ]


def test_a_bare_base_offers_nothing_to_shoot_at() -> None:
    """Its map coordinate is not a target, and firing at it was the whole bug."""
    cp = _control_point(50000, 0, blue=True, tgos=[])
    assert _generator([cp]).possible_missile_targets() == []


def test_it_skips_dead_objectives_and_ships() -> None:
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


def test_it_ignores_friendly_control_points() -> None:
    cp = _control_point(50000, 0, blue=False, tgos=[_tgo(50500, 0)])
    assert _generator([cp]).possible_missile_targets() == []


def test_range_is_measured_to_the_objective_not_the_base() -> None:
    """The far depot is out of reach even though its base's centre is not."""
    cp = _control_point(50000, 0, blue=True, tgos=[_tgo(55000, 0), _tgo(90000, 0)])
    assert _coords(_generator([cp], site_range=80000).possible_missile_targets()) == [
        (55000.0, 0.0)
    ]


def test_it_will_not_shoot_inside_its_minimum_range() -> None:
    """An ATACMS battery cannot engage inside 75 km, however inviting the target."""
    cp = _control_point(
        50000, 0, blue=True, tgos=[_tgo(40000, 0), _tgo(80000, 0), _tgo(90000, 0)]
    )
    targets = _generator([cp], site_range=140000, site_min=75000)
    assert _coords(targets.possible_missile_targets()) == [
        (80000.0, 0.0),
        (90000.0, 0.0),
    ]


def test_a_minimum_that_swallows_everything_leaves_the_site_silent() -> None:
    """The DF-21D declares a 300 km floor; a site with nothing beyond it holds fire."""
    cp = _control_point(50000, 0, blue=True, tgos=[_tgo(50000, 0)])
    assert (
        _generator([cp], site_range=1000000, site_min=300000).possible_missile_targets()
        == []
    )


def test_it_does_not_shoot_at_the_last_metre_of_its_envelope() -> None:
    """An ATACMS fired at 296 of its nominal 300 km came down 18 km past the aimpoint."""
    cp = _control_point(50000, 0, blue=True, tgos=[_tgo(99000, 0)])
    assert _generator([cp], site_range=100000).possible_missile_targets() == []


def test_the_salvo_is_aimed_at_the_objective_itself() -> None:
    """A CEP offset was moving the whole crater trail off the target.

    Three launchers fire at one point and DCS walks the rounds along the firing line
    for about a kilometre on its own, so there is no dispersion left for us to add --
    only a target left to miss.
    """
    import inspect

    from game.missiongenerator import tgogenerator

    source = inspect.getsource(tgogenerator.MissileSiteGenerator.plan_fire_mission)
    assert "FireAtPoint(target.position)" in source
    assert not hasattr(tgogenerator.MissileSiteGenerator, "aimpoint_error")
    assert not hasattr(tgogenerator, "MISSILE_SITE_CEP_M")
