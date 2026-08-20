"""Every airframe offered a DEAD mission must be able to fly one.

A DEAD ingress tasks the group with ``AttackGroup`` (see deadingress.py), and only DCS
aircraft carrying SEAD, CAS, AFAC or Antiship Strike can execute that. Offering DEAD to
an aircraft without one of those tasks does not degrade gracefully: mission generation
raises at Take Off, after the player has planned the whole turn.

That is exactly what happened to the F-117A and both Tu-160s, whose DCS types know only
Pinpoint Strike. The data said they could fly DEAD; the generator could not build it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from dcs.task import AFAC, AntishipStrike, CAS, SEAD

from game import persistency
from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType

# What AircraftBehavior.configure_dead accepts, in its own order of preference.
DEAD_CAPABLE_DCS_TASKS = {SEAD, CAS, AFAC, AntishipStrike}


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # AircraftType loads the unit data files, which reach for the saved-games folder.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16885)


def test_no_aircraft_offers_dead_it_cannot_be_tasked_for() -> None:
    AircraftType._load_all()

    offending = sorted(
        f"{aircraft.display_name} (DCS tasks: "
        f"{[getattr(t, 'name', t) for t in aircraft.dcs_unit_type.tasks]})"
        for aircraft in AircraftType._by_name.values()
        if aircraft.capable_of(FlightType.DEAD)
        and not DEAD_CAPABLE_DCS_TASKS & set(aircraft.dcs_unit_type.tasks)
    )
    assert not offending, (
        "these airframes offer DEAD but cannot be given the AttackGroup task, so "
        "generating one raises at Take Off: " + "; ".join(offending)
    )
