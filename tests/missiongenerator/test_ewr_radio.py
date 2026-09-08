"""An EWR site is generated with a radio, so the F10 menu entry can be answered.

DCS puts any group carrying the EWR enroute task into the "AWACS" radio menu,
with the full Declare / Picture / Vector submenu -- but a vehicle group has no
radio unless the mission gives it one, so the entry had nobody behind it. These
tests pin the radio and the briefing/kneeboard record that goes with it.
"""

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.missiondata import MissionData
from game.missiongenerator.tgogenerator import EwrGenerator
from game.radio.radios import RadioRegistry
from game.theater.player import Player
from game.theater.theatergroundobject import EwrGroundObject


def _tgo(side: Player = Player.BLUE) -> Any:
    # Built without EwrGroundObject.__init__, which needs a whole ControlPoint
    # graph; the generator only reads the name, the owner and the runtime type.
    tgo = object.__new__(EwrGroundObject)
    tgo.name = "WYVERN"
    tgo.control_point = SimpleNamespace(captured=side, name="Batumi")  # type: ignore[assignment]
    return tgo


def _group() -> Any:
    return SimpleNamespace(
        name="0011 | WYVERN (EWR)",
        points=[SimpleNamespace(tasks=[])],
        units=[SimpleNamespace(type="FPS-117")],
        communication=False,
        modulation=0,
        frequency=None,
    )


def _generator(tgo: Any, mission_data: MissionData) -> EwrGenerator:
    game = SimpleNamespace(
        settings=SimpleNamespace(
            perf_red_alert_state=False,
            plugin_option=lambda name: False,
        ),
        skynet_culled=lambda t: False,
    )
    return EwrGenerator(
        tgo,
        None,  # type: ignore[arg-type]
        game,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        RadioRegistry(),
        mission_data,
    )


def test_ewr_group_gets_a_tunable_radio() -> None:
    group = _group()
    mission_data = MissionData()
    _generator(_tgo(), mission_data).enable_ewr(group)

    assert group.communication is True
    assert group.frequency is not None
    # pydcs only writes communication/frequency/modulation for a vehicle group
    # when `communication` is set, and the UHF pool it comes from is AM.
    assert group.modulation == 0
    assert 225 <= group.frequency <= 400


def test_ewr_is_published_for_the_briefing_and_kneeboard() -> None:
    group = _group()
    mission_data = MissionData()
    _generator(_tgo(), mission_data).enable_ewr(group)

    (ewr,) = mission_data.ewrs
    assert ewr.callsign == "WYVERN"
    # The label the F10 menu shows, not the DCS type id.
    assert ewr.unit_type == "EWR AN/FPS-117 Radar"
    assert ewr.location == "Batumi"
    assert ewr.blue is Player.BLUE
    assert ewr.freq.mhz == group.frequency


def test_enroute_task_is_still_applied() -> None:
    """The radio is added on top of the EWR task, never instead of it."""
    from dcs.task import EWR

    group = _group()
    _generator(_tgo(), MissionData()).enable_ewr(group)

    assert [type(t) for t in group.points[0].tasks] == [EWR]


def test_neutral_site_gets_no_radio_and_no_entry() -> None:
    group = _group()
    mission_data = MissionData()
    _generator(_tgo(Player.NEUTRAL), mission_data).enable_ewr(group)

    assert group.communication is False
    assert mission_data.ewrs == []


def test_each_site_gets_its_own_channel() -> None:
    mission_data = MissionData()
    registry = RadioRegistry()
    groups = []
    for _ in range(5):
        group = _group()
        generator = _generator(_tgo(), mission_data)
        generator.radio_registry = registry
        generator.enable_ewr(group)
        groups.append(group)

    frequencies = [g.frequency for g in groups]
    assert len(set(frequencies)) == len(frequencies)
