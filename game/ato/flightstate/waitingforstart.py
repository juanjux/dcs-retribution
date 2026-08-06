from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from game.ato.starttype import StartType
from .atdeparture import AtDeparture
from .flightstate import FlightState
from .navigating import Navigating
from .startup import StartUp
from .takeoff import Takeoff
from .taxi import Taxi

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.settings import Settings
    from game.sim.gameupdateevents import GameUpdateEvents


class WaitingForStart(AtDeparture):
    def __init__(
        self,
        flight: Flight,
        settings: Settings,
        start_time: datetime,
    ) -> None:
        super().__init__(flight, settings)
        self.start_time = start_time

    @property
    def start_type(self) -> StartType:
        return self.flight.start_type

    def on_game_tick(
        self, events: GameUpdateEvents, time: datetime, duration: timedelta
    ) -> None:
        if time < self.start_time:
            return

        new_state: FlightState
        if self.start_type is StartType.COLD:
            new_state = StartUp(self.flight, self.settings, time)
        elif self.start_type is StartType.WARM:
            new_state = Taxi(self.flight, self.settings, time)
        elif self.start_type is StartType.RUNWAY:
            new_state = Takeoff(self.flight, self.settings, time)
        else:
            new_state = Navigating(self.flight, self.settings, waypoint_index=0)
        self.flight.set_state(new_state)

        # Opt-in halt requested before run_to_first_contact (set by the
        # pre-launch mismatch dialog when the user chose "halt at this
        # flight's start" instead of changing the flight's start_type).
        # Halt now that the flight has reached its actual spawn state.
        if getattr(self.flight, "halt_sim_on_spawn", False):
            self.flight.halt_sim_on_spawn = False
            logging.info(
                "Halting fast-forward at %s spawn for %s (start type %s) "
                "as requested by the pre-launch mismatch dialog.",
                new_state.description,
                self.flight,
                self.start_type.name,
            )
            events.complete_simulation()

    @property
    def is_waiting_for_start(self) -> bool:
        return True

    def time_remaining(self, time: datetime) -> timedelta:
        return self.start_time - time

    @property
    def spawn_type(self) -> StartType:
        return self.flight.start_type

    @property
    def description(self) -> str:
        if self.start_type is StartType.COLD:
            start_type = "startup"
        elif self.start_type is StartType.WARM:
            start_type = "taxi"
        elif self.start_type is StartType.RUNWAY:
            start_type = "takeoff"
        elif self.start_type is StartType.IN_FLIGHT:
            start_type = "air start"
        else:
            raise ValueError(f"Unhandled StartType: {self.start_type}")
        return f"Waiting for {start_type} at {self.start_time:%H:%M:%S}"
