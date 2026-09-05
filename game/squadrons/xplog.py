"""TEMPORARY instrumentation: a written record of every experience point awarded.

Live Pilots decides promotions from numbers nobody can see, so this writes each turn
out in one block -- who was paid, how much, for what, and what he held before and
after -- to ``logs/live_pilots_xp.log`` as well as to the normal log, where the prefix
below makes it greppable.

Delete this module and its call sites in ``MissionResultsProcessor`` once the ladder
has been watched for a few turns and is trusted.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any, Iterable, Optional

LOG_PATH = Path("logs") / "live_pilots_xp.log"
PREFIX = "LIVE PILOTS XP"


class XpLog:
    """One turn's awards, held until the whole picture can be written at once."""

    def __init__(self, turn: Any) -> None:
        self.turn = turn
        self._awards: dict[int, list[str]] = {}
        self._lines: list[str] = []

    def award(self, pilot: Any, xp: int, verb: str, victim: Any, target: str) -> None:
        """One thing destroyed or damaged, held until its pilot's line is written."""
        what = type(victim).__name__ if victim is not None else "unresolved"
        self._awards.setdefault(id(pilot), []).append(
            f'    {xp:<+6} {verb:<9} {what} "{target}"'
        )

    @staticmethod
    def _who(pilot: Any, squadron: Any, aircraft: Any) -> str:
        return f"{pilot.name} ({squadron}, {aircraft})"

    def fate(
        self,
        pilot: Any,
        squadron: Any,
        aircraft: Any,
        rank: Any,
        chance: float,
        outcome: str,
    ) -> None:
        """A pilot who lost his aircraft, and what the dice made of it.

        One line for the whole business, written once both rolls are settled: saying
        "died" and then "was wounded" two lines later read as a contradiction.
        """
        where = getattr(rank, "abbreviation", None) or "no rank"
        self._lines.append(
            f"  {self._who(pilot, squadron, aircraft)} lost his aircraft as {where}, "
            f"{chance:.0%} to walk away -- {outcome}"
        )

    def collected(
        self,
        pilot: Any,
        squadron: Any,
        aircraft: Any,
        before: int,
        after: int,
        extras: Iterable[tuple[str, str, int]],
        promotion: Optional[str],
    ) -> None:
        breakdown = self._awards.pop(id(pilot), [])
        for verb, detail, xp in extras:
            if xp:
                breakdown.append(f"    {xp:<+6} {verb:<9} {detail}")
        self._lines.append(
            f"  {self._who(pilot, squadron, aircraft)}: "
            f"{before} -> {after} (+{after - before})"
        )
        self._lines.extend(breakdown)
        if promotion is not None:
            self._lines.append(f"    promoted: {promotion}")

    def uncollected(self, pilot: Any, squadron: Any, aircraft: Any, xp: int) -> None:
        """He earned it and did not live to collect it."""
        breakdown = self._awards.pop(id(pilot), [])
        if not breakdown and not xp:
            return
        self._lines.append(
            f"  {self._who(pilot, squadron, aircraft)}: killed in action, "
            f"{xp} earned and not collected"
        )
        self._lines.extend(breakdown)

    def write(self) -> None:
        if not self._lines and not self._awards:
            return
        block = [
            f"=== turn {self.turn} :: {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ===",
            *self._lines,
        ]
        orphans = [line for lines in self._awards.values() for line in lines]
        if orphans:
            # A pilot credited with a kill whom no package in either ATO reached: he
            # was not flying a planned sortie, or his flight was gone by the time the
            # results were processed.
            block.append("  paid to a pilot no ATO package accounted for:")
            block.extend(orphans)
        for line in block:
            logging.info(f"{PREFIX}: {line}")
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(block) + "\n\n")
        except OSError as ex:
            logging.warning(f"Could not write {LOG_PATH}: {ex}")
