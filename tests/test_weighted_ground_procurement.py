from __future__ import annotations

import collections
from types import SimpleNamespace
from typing import Any

from game.procurement import ProcurementAi
from game.data.units import UnitClass


class _Unit:
    """The two attributes the buy actually reads."""

    def __init__(self, name: str, price: int) -> None:
        self.name = name
        self.price = price
        self.unit_class = UnitClass.TANK

    def __repr__(self) -> str:
        return self.name


def _ai(weighted: bool, units: list[Any]) -> ProcurementAi:
    ai = ProcurementAi.__new__(ProcurementAi)
    ai.game = SimpleNamespace(  # type: ignore[assignment]
        settings=SimpleNamespace(weighted_ground_procurement=weighted)
    )
    ai.faction = SimpleNamespace(  # type: ignore[assignment]
        frontline_units=units, artillery_units=[]
    )
    return ai


def _draws(ai: ProcurementAi, times: int = 4000) -> collections.Counter[str]:
    picks: collections.Counter[str] = collections.Counter()
    for _ in range(times):
        picked = ai.affordable_ground_unit_of_class(1000, UnitClass.TANK)
        picks[picked.name] += 1  # type: ignore[union-attr]
    return picks


def test_the_expensive_unit_is_bought_more_often() -> None:
    """Price is the capability proxy: a modern MBT should outnumber the gun truck."""
    ai = _ai(True, [_Unit("MBT", 90), _Unit("gun truck", 10)])
    picks = _draws(ai)
    assert picks["MBT"] > picks["gun truck"] * 3


def test_the_cheap_unit_is_never_locked_out() -> None:
    """A weighting, not a maximum -- variety has to survive."""
    ai = _ai(True, [_Unit("MBT", 90), _Unit("gun truck", 10)])
    assert _draws(ai)["gun truck"] > 0


def test_off_is_the_old_uniform_roll() -> None:
    ai = _ai(False, [_Unit("MBT", 90), _Unit("gun truck", 10)])
    picks = _draws(ai)
    assert 0.4 < picks["MBT"] / sum(picks.values()) < 0.6


def test_nothing_affordable_buys_nothing() -> None:
    ai = _ai(True, [_Unit("MBT", 9000)])
    assert ai.affordable_ground_unit_of_class(10, UnitClass.TANK) is None


def test_a_free_unit_does_not_break_the_weighting() -> None:
    """A price of 0 would make random.choices raise on an all-zero weight vector."""
    ai = _ai(True, [_Unit("free", 0)])
    assert ai.affordable_ground_unit_of_class(10, UnitClass.TANK) is not None
