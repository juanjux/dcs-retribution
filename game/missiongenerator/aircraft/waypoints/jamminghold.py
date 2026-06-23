from dcs.point import MovingPoint
from dcs.task import ControlledTask, OptFormation, OrbitAction

from game.utils import meters
from .pydcswaypointbuilder import PydcsWaypointBuilder


class JammingHoldBuilder(PydcsWaypointBuilder):
    """Standoff orbit for a dedicated EW jammer (FlightType.EWAR).

    Anchors the jammer at the ingress standoff and orbits there until the package
    actually egresses, instead of flying its target run on a fixed schedule and turning
    for home early (which left the package exposed if it was slow). The JOIN
    EscortTaskAction (HARM at SAM radars) and the offensive/defensive jamming scripts
    keep running while orbiting. The orbit breaks reactively on the split-<package>
    user flag -- set by the primary flight's SPLIT, the same flag the EscortTaskAction
    and the package-level AITaskPush already key off -- so player slippage is absorbed;
    there is deliberately no time-based stop.
    """

    def add_tasks(self, waypoint: MovingPoint) -> None:
        speed = self.flight.squadron.aircraft.preferred_patrol_speed(
            meters(waypoint.alt)
        )
        orbit = ControlledTask(
            OrbitAction(
                altitude=waypoint.alt,
                speed=speed.kph,
                pattern=OrbitAction.OrbitPattern.RaceTrack,
            )
        )
        orbit.stop_if_user_flag(f"split-{id(self.package)}", True)
        waypoint.add_task(orbit)
        if self.flight.is_helo:
            waypoint.add_task(OptFormation.rotary_column())
        else:
            waypoint.add_task(OptFormation.finger_four_open())
