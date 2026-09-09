"""Reading a tank's fuel out of what DCS says about it.

There is no fuel figure on a store, so it comes from the volume in the name, bounded
by the laden weight.
"""

from __future__ import annotations

from dcs.weapons_data import weapon_ids

from game.data.fueltanks import external_fuel

#: A tank whose stated volume can be checked by hand: 330 US gallons of jet fuel is
#: a bit over a ton.
HORNET_TANK = "FPU-8A Fuel Tank 330 gallons"
VIPER_TANK = "Fuel tank 370 gal"
LITRE_TANK = "1100L Tank"
NOT_FUEL = "Color Oil Tank"


def _clsid_named(name: str) -> str:
    for clsid, data in weapon_ids.items():
        if data.get("name") == name:  # type: ignore[attr-defined]
            return str(clsid)
    raise AssertionError(f"no weapon named {name}")


def test_a_tank_in_gallons() -> None:
    fuel = external_fuel(_clsid_named(HORNET_TANK))
    assert fuel is not None
    # 330 US gal of jet fuel is about 2,200 lb; the store weighs less than that laden,
    # so the answer is capped by the weight.
    assert 1900 < fuel.pounds < 2300


def test_a_tank_in_litres() -> None:
    fuel = external_fuel(_clsid_named(LITRE_TANK))
    assert fuel is not None
    assert 1800 < fuel.pounds < 2100


def test_never_more_fuel_than_the_store_weighs() -> None:
    """A tank cannot hold more than it weighs full, whatever its label claims."""
    for clsid, data in weapon_ids.items():
        fuel = external_fuel(str(clsid))
        if fuel is None:
            continue
        weight = data.get("weight")  # type: ignore[attr-defined]
        if weight is None:
            continue
        assert fuel.kgs <= float(weight), data.get("name")  # type: ignore[attr-defined]


def test_an_empty_tank_carries_nothing() -> None:
    for clsid, data in weapon_ids.items():
        name = str(data.get("name", ""))  # type: ignore[attr-defined]
        if "empty" not in name.lower():
            continue
        fuel = external_fuel(str(clsid))
        if fuel is not None:
            assert fuel.kgs == 0, name


def test_a_tank_of_something_else_is_not_fuel() -> None:
    assert external_fuel(_clsid_named(NOT_FUEL)) is None


def test_a_missile_is_not_a_tank() -> None:
    for clsid, data in weapon_ids.items():
        name = str(data.get("name", ""))  # type: ignore[attr-defined]
        if "AIM-120" in name or "AGM-88" in name:
            assert external_fuel(str(clsid)) is None, name
