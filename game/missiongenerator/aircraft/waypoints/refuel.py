from dcs.point import MovingPoint
from dcs.task import RefuelingTaskAction, ControlledTask

from game.ato.flighttype import FlightType
from .pydcswaypointbuilder import PydcsWaypointBuilder


class RefuelPointBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        if not self.ai_despawn(waypoint, True):
            refuel = ControlledTask(RefuelingTaskAction())
            refuel.start_if_lua_predicate(self._get_lua_predicate(0.2))
            refuel.stop_if_lua_predicate(self._get_lua_predicate(0.5))
            waypoint.add_task(refuel)
        # Stop jamming while refuelling (the split waypoint also stops it).
        settings = self.flight.coalition.game.settings
        ai_jammer = settings.plugin_option("ewrj.ai_jammer_enabled")
        dedicated_ew = self.flight.flight_type == FlightType.EWAR
        if settings.plugins.get("ewrj") and (ai_jammer or dedicated_ew):
            self.offensive_jamming(waypoint, "stop")
            self.defensive_jamming(waypoint, "stop")
        return super().add_tasks(waypoint)

    def _get_lua_predicate(self, fuel_level: float) -> str:
        return f"""
            local okfuel = true
            for i, unitObject in pairs(Group.getByName('{self.group.name}'):getUnits()) do
                --trigger.action.outText(tostring(Unit.getFuel(unitObject)), 15)
                if Unit.getFuel(unitObject) < {fuel_level} then okfuel = false; break end
            end
            return okfuel
            """
