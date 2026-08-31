import logging

from dcs.point import MovingPoint
from dcs.task import ControlledTask, OptFormation, OrbitAction

from game.ato.flightplans.loiter import LoiterFlightPlan
from game.utils import meters
from ._helper import create_stop_orbit_trigger
from .pydcswaypointbuilder import PydcsWaypointBuilder


class HoldPointBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        speed = self.flight.squadron.aircraft.preferred_patrol_speed(
            meters(waypoint.alt)
        )
        loiter = ControlledTask(
            OrbitAction(
                altitude=waypoint.alt,
                speed=speed.kph,
                pattern=OrbitAction.OrbitPattern.Circle,
            )
        )
        if not isinstance(self.flight.flight_plan, LoiterFlightPlan):
            flight_plan_type = self.flight.flight_plan.__class__.__name__
            logging.error(
                f"Cannot configure hold for for {self.flight} because "
                f"{flight_plan_type} does not define a push time. AI will push "
                "immediately and may flight unsuitable speeds."
            )
            return
        push_time = self.flight.flight_plan.push_time
        self.waypoint.departure_time = push_time
        elapsed = int((push_time - self.now).total_seconds()) - 60
        if elapsed < 0:
            # The package's TOT is earlier than this flight can physically reach it, so
            # the push time lands before the mission even starts. Emitted as-is, the
            # release below becomes a trigger scheduled for a NEGATIVE mission time,
            # which DCS never fires -- and since the native stop-after-time is already
            # unreliable (that is what the trigger hotfix underneath is for), the
            # flight can sit in its hold for the whole mission. Release immediately
            # instead: it cannot make the TOT either way, but it does fly the mission.
            logging.warning(
                f"{self.flight} cannot reach its target by the package TOT "
                f"({-elapsed}s short); releasing the hold at mission start."
            )
            elapsed = 0
        loiter.stop_after_time(elapsed)
        # What follows is some code to cope with the broken 'stop after time' condition
        create_stop_orbit_trigger(loiter, self.group.id, self.mission, elapsed)
        # end of hotfix
        waypoint.add_task(loiter)
        if self.flight.is_helo:
            waypoint.add_task(OptFormation.rotary_column())
        else:
            waypoint.add_task(OptFormation.finger_four_open())
