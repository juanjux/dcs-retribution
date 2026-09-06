"""A TARCAP covers an attack; a BARCAP guards a base for hours.

They shared a number, and not even the one the player typed: TARCAP read
``doctrine.cap_duration``, a flat 30 minutes in all three doctrines.
``Doctrine.from_settings`` does map the BARCAP setting onto it, but nothing has ever
called that method, so the setting never arrived.
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

from game.ato.flightplans.tarcap import TarCapFlightPlan
from game.settings import Settings


def _plan(settings: Settings) -> Any:
    plan: Any = TarCapFlightPlan.__new__(TarCapFlightPlan)
    plan.flight = SimpleNamespace(
        coalition=SimpleNamespace(game=SimpleNamespace(settings=settings))
    )
    return plan


def test_it_reads_its_own_setting() -> None:
    settings = Settings()
    settings.desired_tarcap_mission_duration = timedelta(minutes=45)
    settings.desired_barcap_mission_duration = timedelta(minutes=120)
    assert _plan(settings).patrol_duration == timedelta(minutes=45)


def test_the_default_is_what_it_always_did() -> None:
    """Nobody's campaign changes until they touch the new box."""
    assert Settings().desired_tarcap_mission_duration == timedelta(minutes=30)


def test_the_barcap_setting_no_longer_decides_it() -> None:
    settings = Settings()
    settings.desired_barcap_mission_duration = timedelta(minutes=120)
    assert _plan(settings).patrol_duration != timedelta(minutes=120)
