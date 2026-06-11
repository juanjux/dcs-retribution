from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from threading import Event, Thread
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from game.debriefing import Debriefing
    from game.sim import MissionSimulation


#: How often (seconds) we check state.json. DCS' export hook rewrites the
#: file every second once the mission has ended, so a short interval keeps
#: end-of-mission detection responsive without burning CPU.
POLL_INTERVAL_SECONDS = 2


class PollDebriefingFileThread(Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(
        self,
        callback: Callable[[Debriefing], None],
        mission_sim: MissionSimulation,
    ) -> None:
        super().__init__()
        self._stop_event = Event()
        self.callback = callback
        self.mission_sim = mission_sim

    def stop(self) -> None:
        self._stop_event.set()

    def stopped(self) -> bool:
        return self._stop_event.is_set()

    def run(self) -> None:
        # Treat any state.json newer than this mission's .miz as the current
        # mission's result; an older file is a stale leftover from a previous
        # mission and is ignored until DCS rewrites it.
        last_modified = self.mission_sim.miz_generated_at
        logging.info(
            "Watching state.json for writes after mission launch (mtime > %s)",
            last_modified,
        )
        while not self.stopped():
            try:
                if (
                    os.path.isfile("state.json")
                    and os.path.getmtime("state.json") > last_modified
                ):
                    debriefing = self.mission_sim.debrief_current_state(
                        Path("state.json")
                    )
                    self.callback(debriefing)
                    last_modified = os.path.getmtime("state.json")
                    if debriefing.state_data.mission_ended:
                        logging.info("Mission end detected; stopping poll")
                        break
            except (json.JSONDecodeError, OSError, ValueError, KeyError):
                logging.error(
                    "Failed to read state.json (likely read while DCS was "
                    "still writing it); will retry in %ss.",
                    POLL_INTERVAL_SECONDS,
                    exc_info=True,
                )
            time.sleep(POLL_INTERVAL_SECONDS)
