from __future__ import annotations

import logging
from typing import Type

from game.theater.theatergroundobject import (
    EwrGroundObject,
    SamGroundObject,
)
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .invalidobjectivelocation import InvalidObjectiveLocation
from ..flightwaypointtype import FlightWaypointType


class DeadFlightPlan(FormationAttackFlightPlan):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder


class Builder(FormationAttackBuilder[DeadFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        location = self.package.target

        if not isinstance(location, (EwrGroundObject, SamGroundObject)):
            logging.exception(
                f"Invalid Objective Location for DEAD flight {self.flight=} at "
                f"{location=}"
            )
            raise InvalidObjectiveLocation(self.flight.flight_type, location)

        return self._build(
            FlightWaypointType.INGRESS_DEAD, self.strike_targets_for(location)
        )

    def build(self, dump_debug_info: bool = False) -> DeadFlightPlan:
        return DeadFlightPlan(self.flight, self.layout())
