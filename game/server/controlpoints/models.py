from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.server.leaflet import LeafletPoint

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint


class ControlPointJs(BaseModel):
    id: UUID
    name: str
    blue: bool
    position: LeafletPoint
    mobile: bool
    destination: LeafletPoint | None
    sidc: str
    # Comms/nav summary for the hover tooltip. None when not applicable
    # (e.g. enemy control point, or no TACAN allocated yet).
    tacan: str | None
    atc_frequency: str | None
    units: list[str]
    threat_ranges: list[float]
    detection_ranges: list[float]

    class Config:
        title = "ControlPoint"

    @staticmethod
    def for_control_point(control_point: ControlPoint) -> ControlPointJs:
        destination = None
        if control_point.target_position is not None:
            destination = control_point.target_position.latlng()
        if control_point.captured.is_blue:
            blue = True
        else:
            blue = False
        tacan, atc_frequency = _comms_summary(control_point)

        # Carrier/LHA control points carry their ship groups (the carrier and
        # its escorts) as an is_control_point ground object that is
        # intentionally not emitted as a standalone TGO. Surface the surviving
        # units and their air-defense ranges on the control point itself so the
        # map can show the escort detail and threat rings the same way it does
        # for ordinary naval groups.
        units: list[str] = []
        threat_ranges: list[float] = []
        detection_ranges: list[float] = []
        for tgo in control_point.ground_objects:
            if not tgo.is_control_point:
                continue
            # Show every unit (display_name already tags dead ones with
            # " [DEAD]"), matching how ordinary naval groups list their losses.
            units.extend(unit.display_name for unit in tgo.units)
            for group in tgo.groups:
                threat = group.max_threat_range().meters
                if threat:
                    threat_ranges.append(threat)
                detection = group.max_detection_range().meters
                if detection:
                    detection_ranges.append(detection)

        return ControlPointJs(
            id=control_point.id,
            name=control_point.name,
            blue=blue,
            position=control_point.position.latlng(),
            mobile=control_point.moveable and control_point.captured.is_blue,
            destination=destination,
            sidc=str(control_point.sidc()),
            tacan=tacan,
            atc_frequency=atc_frequency,
            units=units,
            threat_ranges=threat_ranges,
            detection_ranges=detection_ranges,
        )

    @staticmethod
    def all_in_game(game: Game) -> list[ControlPointJs]:
        return [
            ControlPointJs.for_control_point(cp) for cp in game.theater.controlpoints
        ]


def _comms_summary(cp: ControlPoint) -> tuple[str | None, str | None]:
    """Return (tacan, atc_frequency) strings for the tooltip, or None if N/A.

    Only resolved for friendly (blue) airfields, since the tooltip shows our
    own bases' comms — enemy details are not exposed in planning.
    """
    from game.atcdata import AtcData
    from game.radio.TacanContainer import TacanContainer
    from game.theater.controlpoint import Airfield

    if not cp.captured.is_blue:
        return None, None

    tacan: str | None = None
    if isinstance(cp, TacanContainer) and cp.tacan is not None:
        if cp.tcn_name:
            tacan = f"{cp.tacan} ({cp.tcn_name})"
        else:
            tacan = str(cp.tacan)

    atc: str | None = None
    if isinstance(cp, Airfield):
        atc_radio = AtcData.from_pydcs(cp.airport)
        if atc_radio is not None and atc_radio.uhf is not None:
            atc = str(atc_radio.uhf)

    return tacan, atc
