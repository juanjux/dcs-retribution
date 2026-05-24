from typing import Any
from unittest.mock import MagicMock

from dcs.task import OptRTBOnOutOfAmmo

from game.missiongenerator.aircraft.aircraftbehavior import AircraftBehavior


def test_anti_ship_flights_rtb_when_out_of_anti_ship_missiles() -> None:
    """Anti-ship flights must RTB once their anti-ship missiles are spent.

    The AI behaviour (RTB on winchester) is DCS-side and not unit-testable, but
    the option we set on the flight is: without it the AttackGroup task on the
    ingress waypoint has no completion condition, and aircraft carrying only
    stand-off weapons (e.g. the S-3B) keep boring in on the fleet after firing.
    This guards against the RTB-on-winchester option being dropped.
    """
    # Bypass __init__ (it pulls a Flight/Settings); configure_anti_ship only
    # calls self.configure_task and self.configure_behavior, both mocked here.
    behavior: Any = object.__new__(AircraftBehavior)
    behavior.configure_task = MagicMock()
    behavior.configure_behavior = MagicMock()

    behavior.configure_anti_ship(group=MagicMock(), flight=MagicMock())

    behavior.configure_behavior.assert_called_once()
    assert (
        behavior.configure_behavior.call_args.kwargs["rtb_winchester"]
        == OptRTBOnOutOfAmmo.Values.Antiship
    )
