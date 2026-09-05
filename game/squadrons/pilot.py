from __future__ import annotations

from dataclasses import dataclass, field
from enum import unique, Enum
from typing import Any

from faker import Faker


@dataclass
class PilotRecord:
    missions_flown: int = field(default=0)

    #: What the pilot has earned in the air, which is what decides his rank. A plain
    #: default rather than a factory: dataclasses keep the former as a class attribute,
    #: so a pilot unpickled from a save written before this field reads 0 instead of
    #: raising.
    xp: int = field(default=0)

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Belt and braces for the same case: older saves carry no xp at all.
        state.setdefault("xp", 0)
        self.__dict__.update(state)


@unique
class PilotStatus(Enum):
    Active = "Active"
    OnLeave = "On leave"
    Dead = "Dead"
    #: Pulled out of the wreckage. Out of the roster until he has served his turns,
    #: which is the same unavailability as leave and needs no separate plumbing.
    Wounded = "Wounded"


@dataclass
class Pilot:
    name: str
    player: bool = field(default=False)
    status: PilotStatus = field(default=PilotStatus.Active)
    record: PilotRecord = field(default_factory=PilotRecord)

    #: Turns left in hospital. A plain default, so a pilot unpickled from a save
    #: written before wounds existed reads 0 from the class rather than raising.
    wounded_turns: int = field(default=0)

    #: The turn the wound was dealt in, which does not count towards serving it.
    wounded_on_turn: int = field(default=-1)

    def __setstate__(self, state: dict[str, Any]) -> None:
        state.setdefault("wounded_turns", 0)
        state.setdefault("wounded_on_turn", -1)
        self.__dict__.update(state)

    @property
    def alive(self) -> bool:
        return self.status is not PilotStatus.Dead

    @property
    def on_leave(self) -> bool:
        return self.status is PilotStatus.OnLeave

    @property
    def wounded(self) -> bool:
        return self.status is PilotStatus.Wounded

    def send_on_leave(self) -> None:
        if self.status is not PilotStatus.Active:
            raise RuntimeError("Only active pilots may be sent on leave")
        self.status = PilotStatus.OnLeave

    def return_from_leave(self) -> None:
        if self.status is not PilotStatus.OnLeave:
            raise RuntimeError("Only pilots on leave may be returned from leave")
        self.status = PilotStatus.Active

    def wound(self, turns: int, turn: int) -> None:
        """He was going to die. Instead he is out for the next ``turns`` of them."""
        self.status = PilotStatus.Wounded
        self.wounded_turns = turns
        self.wounded_on_turn = turn

    def serve_a_turn_wounded(self, turn: int) -> None:
        """One turn of the wound served. The last one puts him back on the roster.

        Not the turn he was hurt in. Wounds are dealt while a turn is being closed and
        the squadron serves them at that same close, so counting it would have him back
        a turn early -- the debriefing said four turns and the Air Wing showed three.
        """
        if turn == self.wounded_on_turn:
            return
        self.wounded_turns -= 1
        if self.wounded_turns <= 0:
            self.wounded_turns = 0
            self.wounded_on_turn = -1
            self.status = PilotStatus.Active

    def kill(self) -> None:
        self.status = PilotStatus.Dead
        self.wounded_turns = 0
        self.wounded_on_turn = -1

    @classmethod
    def random(cls, faker: Faker) -> Pilot:
        return Pilot(faker.name())
