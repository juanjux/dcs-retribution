from __future__ import annotations

import itertools
from collections.abc import Iterator

from typing_extensions import TYPE_CHECKING

from game.ato.flightstate import Uninitialized
from .simulationresults import SimulationResults

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight


class AircraftSimulation:
    def __init__(self, game: Game) -> None:
        self.game = game
        self.results = SimulationResults()

    def begin_simulation(self) -> None:
        self.reset()
        self.set_initial_flight_states()

    def set_initial_flight_states(self) -> None:
        now = self.game.conditions.start_time
        for flight in self.iter_flights():
            flight.state.reinitialize(now)

    def reset(self) -> None:
        for flight in self.iter_flights():
            flight.set_state(Uninitialized(flight, self.game.settings))

    def iter_flights(self) -> Iterator[Flight]:
        packages = itertools.chain(
            self.game.blue.ato.packages, self.game.red.ato.packages
        )
        for package in packages:
            yield from package.flights
