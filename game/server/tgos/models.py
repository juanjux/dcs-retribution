from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import BaseModel

from game.data.groups import GroupTask
from game.server.leaflet import LeafletPoint

if TYPE_CHECKING:
    from game import Game
    from game.theater import TheaterGroundObject


class TgoJs(BaseModel):
    id: UUID
    name: str
    control_point_name: str
    category: str
    blue: bool
    position: LeafletPoint
    units: list[str]  # TODO: Event stream
    threat_ranges: list[float]  # TODO: Event stream
    detection_ranges: list[float]  # TODO: Event stream
    dead: bool  # TODO: Event stream
    # Whether the group can be rebuilt/repaired (SAM/EWR/armor). Non-purchasable
    # destroyed objects (buildings, ships, ...) are permanent losses; the map's
    # "destroyed (non-repairable)" layer uses this to decide what it may hide.
    purchasable: bool
    sidc: str  # TODO: Event stream
    task: Optional[GroupTask]

    class Config:
        title = "Tgo"

    @staticmethod
    def for_tgo(tgo: TheaterGroundObject) -> TgoJs:
        # Only include non-zero ranges: a zero-radius circle renders as a stray
        # dot (normally hidden under the unit icon, but visible once the icon is
        # hidden by the destroyed-object layers). Matches ControlPointJs.
        threat_ranges = [
            meters
            for meters in (group.max_threat_range().meters for group in tgo.groups)
            if meters > 0
        ]
        detection_ranges = [
            meters
            for meters in (group.max_detection_range().meters for group in tgo.groups)
            if meters > 0
        ]
        if tgo.control_point.captured.is_blue:
            blue = True
        else:
            blue = False
        return TgoJs(
            id=tgo.id,
            name=tgo.name,
            control_point_name=tgo.control_point.name,
            category=tgo.category,
            blue=blue,
            position=tgo.position.latlng(),
            units=[unit.display_name for unit in tgo.units],
            threat_ranges=threat_ranges,
            detection_ranges=detection_ranges,
            dead=tgo.is_dead,
            purchasable=tgo.purchasable,
            sidc=str(tgo.sidc()),
            task=tgo.groups[0].ground_object.task if tgo.groups else None,
        )

    @staticmethod
    def all_in_game(game: Game) -> list[TgoJs]:
        tgos = []
        for control_point in game.theater.controlpoints:
            for tgo in control_point.connected_objectives:
                if not tgo.is_control_point:
                    tgos.append(TgoJs.for_tgo(tgo))
        return tgos
