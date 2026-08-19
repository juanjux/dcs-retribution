"""The weather the OPFOR planner sees.

Parity: the human reads the ceiling before choosing between a laser-guided bomb and a
JDAM, so the planner gets the same numbers. Frugality: everything that would say
"nothing to report" is omitted rather than sent as a zero, every turn, forever.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from dcs.weather import Weather as PydcsWeather, Wind

from game.agent import views
from game.utils import meters
from game.weather.clouds import Clouds
from game.weather.fog import Fog
from game.weather.wind import WindConditions


def _game(
    clouds: Optional[Clouds] = None,
    fog: Optional[Fog] = None,
    wind: Optional[WindConditions] = None,
    temperature: float = 21.4,
) -> Any:
    weather = SimpleNamespace(
        clouds=clouds,
        fog=fog,
        wind=wind or WindConditions(Wind(30, 5.66), Wind(30, 6.79), Wind(30, 8.49)),
        atmospheric=SimpleNamespace(temperature_celsius=temperature),
    )
    return SimpleNamespace(conditions=SimpleNamespace(weather=weather))


def _clouds(
    density: int = 0,
    base: int = 0,
    precipitation: PydcsWeather.Preceptions = PydcsWeather.Preceptions.None_,
    preset: Any = None,
) -> Clouds:
    return Clouds(
        base=base,
        density=density,
        thickness=0,
        precipitation=precipitation,
        preset=preset,
    )


def test_a_clear_sky_says_so_and_sends_nothing_else() -> None:
    weather = views.build_weather(_game())
    assert weather.clouds == "clear"
    assert weather.base_ft is None
    assert weather.precip is None
    assert weather.vis_nm is None


def test_a_ceiling_is_reported_in_feet_because_that_is_how_pilots_plan() -> None:
    weather = views.build_weather(_game(clouds=_clouds(density=5, base=900)))
    assert weather.base_ft == round(meters(900).feet)
    assert weather.clouds == "BKN"


def test_coverage_follows_density() -> None:
    for density, expected in ((0, "FEW"), (2, "SCT"), (5, "BKN"), (9, "OVC")):
        assert views.build_weather(_game(clouds=_clouds(density=density))).clouds == (
            expected
        )


def test_a_preset_is_named_not_coded() -> None:
    """The campaign's cloud packs carry a description the planner can actually read."""
    preset = SimpleNamespace(
        name="Preset10",
        description="09 ##Two Layer Broken/Scattered",
    )
    weather = views.build_weather(_game(clouds=_clouds(base=2000, preset=preset)))
    assert weather.clouds == "Two Layer Broken/Scattered"


def test_rain_is_worth_a_word_and_clear_air_is_not() -> None:
    rain = _clouds(density=6, precipitation=PydcsWeather.Preceptions.Rain)
    assert views.build_weather(_game(clouds=rain)).precip == "rain"
    assert views.build_weather(_game(clouds=_clouds(density=6))).precip is None


def test_fog_becomes_a_visibility_the_planner_can_act_on() -> None:
    weather = views.build_weather(
        _game(fog=Fog(visibility=meters(3000), thickness=200))
    )
    assert weather.vis_nm == round(meters(3000).nautical_miles)


def test_winds_are_direction_and_knots() -> None:
    weather = views.build_weather(_game())
    assert weather.wind_gl == "030/11"
    assert weather.wind_fl26 == "030/17"


def test_an_unremarkable_upper_wind_is_not_repeated() -> None:
    calm = WindConditions(Wind(90, 2.0), Wind(90, 2.0), Wind(90, 2.0))
    weather = views.build_weather(_game(wind=calm))
    assert weather.wind_gl == "090/4"
    assert weather.wind_fl26 is None


def test_temperature_is_a_whole_number() -> None:
    assert views.build_weather(_game(temperature=21.4)).temp_c == 21
