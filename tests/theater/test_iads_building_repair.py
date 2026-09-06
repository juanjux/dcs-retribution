"""Unit tests for the rebuild price of IADS infrastructure.

Comms towers, power stations and command centres produce no income, so they have no
REWARDS entry, and BuildingGroundObject.repair_cost() derives its price from income.
That left them unrepairable for the rest of the campaign once bombed. They are priced
directly instead -- rebuildable, still earning nothing.
"""

from types import SimpleNamespace
from typing import Any

import pytest

from game.config import IADS_REPAIR_COST, REWARDS
from game.theater.theatergroundobject import BuildingGroundObject


def _building(category: str) -> Any:
    """Stand-in for a BuildingGroundObject.

    repair_cost only reads self.category, self.control_point (for the settings) and the
    is_ammo_depot / is_factory flags, so a namespace is enough and keeps the test free
    of a whole Game. Typed Any so the unbound calls below type-check against it.
    """
    settings = SimpleNamespace(
        building_repair_income_multiplier=2.0,
        building_repair_ammo_bonus=8.0,
        building_repair_factory_bonus=10.0,
    )
    return SimpleNamespace(
        category=category,
        control_point=SimpleNamespace(
            coalition=SimpleNamespace(game=SimpleNamespace(settings=settings))
        ),
        is_ammo_depot=category == "ammo",
        is_factory=category == "factory",
    )


def _cost(category: str) -> float:
    return BuildingGroundObject.repair_cost(_building(category))


def _repairable(category: str) -> bool:
    building = _building(category)
    # repairable reads self.repair_cost(), so give the stand-in one.
    building.repair_cost = lambda: BuildingGroundObject.repair_cost(building)
    return bool(BuildingGroundObject.repairable.fget(building))  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "category,expected",
    [("power", 15.0), ("commandcenter", 10.0), ("comms", 5.0)],
)
def test_iads_buildings_have_a_flat_rebuild_price(
    category: str, expected: float
) -> None:
    assert _cost(category) == expected
    assert _repairable(category)


@pytest.mark.parametrize("category", ["power", "commandcenter", "comms"])
def test_iads_buildings_still_earn_nothing(category: str) -> None:
    # The price must not come from REWARDS, or these would start generating income.
    assert category not in REWARDS


def test_income_buildings_are_unchanged() -> None:
    # income * multiplier, plus the category bonus where there is one.
    assert _cost("oil") == pytest.approx(REWARDS["oil"] * 2.0)
    assert _cost("ammo") == pytest.approx(REWARDS["ammo"] * 2.0 + 8.0)
    assert _cost("factory") == pytest.approx(REWARDS["factory"] * 2.0 + 10.0)


def test_a_category_with_neither_price_nor_income_stays_unrepairable() -> None:
    assert "village" in REWARDS
    assert "armor" not in REWARDS
    assert "armor" not in IADS_REPAIR_COST
    assert _cost("armor") == 0.0
    assert not _repairable("armor")
