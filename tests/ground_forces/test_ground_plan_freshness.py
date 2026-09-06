"""The ground war must be planned from what a base owns now, not at turn start.

Ordering a transfer debits the origin the moment it is created. A plan cached at the
start of the turn therefore deploys units the campaign no longer owns: the player
watches his army hold the line on the map and loses the ground war for being absent,
because the battle is resolved from the books rather than from the mission.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

from game.data.units import UnitClass
from game.dcs.groundunittype import GroundUnitType
from game.ground_forces.ai_ground_planner import GroundPlanner
from game.missiongenerator.missiongenerator import MissionGenerator


def _unit() -> MagicMock:
    u = MagicMock(spec=GroundUnitType)
    u.unit_class = UnitClass.TANK
    return u


def _cp(armor: dict[MagicMock, int]) -> Any:
    # Identity-distinct sentinels: SimpleNamespace() compares equal by content, which
    # would make the "is this an enemy" gate vacuously false.
    enemy = SimpleNamespace(captured=object(), id="enemy", name="Enemy Base")
    return SimpleNamespace(
        captured=object(),
        id="own",
        name="Own Base",
        connected_points=[enemy],
        frontline_unit_count_limit=8,
        base=SimpleNamespace(armor=armor, total_armor=sum(armor.values())),
        stances={},
    )


def test_a_base_that_owns_nothing_deploys_nothing() -> None:
    """The armor dict keeps its unit types after a transfer empties the counts."""
    cp = _cp({_unit(): 0, _unit(): 0})
    planner = GroundPlanner(cast(Any, cp), MagicMock())
    planner.plan_groundwar()
    assert not any(planner.units_per_cp.values())


def test_a_base_that_owns_tanks_deploys_them() -> None:
    cp = _cp({_unit(): 4})
    planner = GroundPlanner(cast(Any, cp), MagicMock())
    planner.plan_groundwar()
    assert sum(len(groups) for groups in planner.units_per_cp.values()) > 0


def test_the_mission_replans_the_ground_war_before_using_it() -> None:
    """Not reused from turn start: the player has had a whole turn to move units."""
    generator = MissionGenerator.__new__(MissionGenerator)
    game = MagicMock()
    game.theater.conflicts.return_value = []
    generator.game = game

    generator.generate_ground_conflicts()

    game.plan_ground_war.assert_called_once_with()
