import logging
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest
from dcs.task import AttackGroup

from game.missiongenerator.aircraft.waypoints.antishipingress import (
    AntiShipIngressBuilder,
)
from game.theater import NavalControlPoint, TheaterGroundObject


def _model_group(name: str) -> MagicMock:
    group = MagicMock()
    group.group_name = name
    return group


def _build_builder(target: Any, find_group: Callable[[str], Any]) -> tuple[Any, Any]:
    # Bypass __init__ (it needs a full mission/flight); only add_tasks() and the
    # few collaborators it consults are exercised. Typed as Any so the mocks can
    # stand in for the real, strongly-typed attributes.
    builder: Any = object.__new__(AntiShipIngressBuilder)
    builder.register_special_ingress_points = MagicMock()
    builder.package = MagicMock()
    builder.package.target = target
    builder.flight = MagicMock()
    builder.mission = MagicMock()
    builder.mission.find_group.side_effect = find_group
    waypoint = MagicMock()
    waypoint.tasks = []
    return builder, waypoint


def test_naval_control_point_targets_main_tgo_not_first_ground_object() -> None:
    """Regression test: the carrier group must come from find_main_tgo().

    A NavalControlPoint can own several ground objects; ground_objects[0] is
    not necessarily the carrier (it may be a sunk group that never spawns).
    The attack task must target the group the flight plan routes to.
    """
    carrier_group = _model_group("carrier-group")
    main_tgo = MagicMock()
    main_tgo.groups = [carrier_group]

    wrong_group = _model_group("wrong-group")
    wrong_tgo = MagicMock()
    wrong_tgo.groups = [wrong_group]

    target = MagicMock(spec=NavalControlPoint)
    target.find_main_tgo.return_value = main_tgo
    target.ground_objects = [wrong_tgo]  # ground_objects[0] is the wrong group

    miz_group = MagicMock()
    miz_group.id = 42

    def find_group(name: str) -> Any:
        return miz_group if name == "carrier-group" else None

    builder, waypoint = _build_builder(target, find_group)
    builder.add_tasks(waypoint)

    queried = [call.args[0] for call in builder.mission.find_group.call_args_list]
    assert "carrier-group" in queried
    assert "wrong-group" not in queried

    attacks = [task for task in waypoint.tasks if isinstance(task, AttackGroup)]
    assert attacks, "expected at least one AttackGroup task"
    assert all(task.params["groupId"] == 42 for task in attacks)


def test_warns_when_no_attackable_group(caplog: pytest.LogCaptureFixture) -> None:
    """A target whose groups are not in the mission yields a clear warning."""
    group = _model_group("missing-group")
    target = MagicMock(spec=TheaterGroundObject)
    target.groups = [group]

    builder, waypoint = _build_builder(target, lambda name: None)

    with caplog.at_level(logging.WARNING):
        builder.add_tasks(waypoint)

    assert not [t for t in waypoint.tasks if isinstance(t, AttackGroup)]
    assert any("no attackable target group" in rec.message for rec in caplog.records)
