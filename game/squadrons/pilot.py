from __future__ import annotations

from dataclasses import dataclass, field
from enum import unique, Enum
from typing import Any

from faker import Faker

from game.squadrons.morale import MORALE_START, REFUSES_TO_FLY_AT


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
    #: He has had enough and walked away. Counted with the dead rather than the living:
    #: gone is gone, and the squadron has to replace him either way.
    Deserted = "Deserted"


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

    #: How he is holding up, 0 to 100. A campaign that has done nothing to him yet has
    #: no opinion about him, which is what 50 means -- and it is what a pilot from a
    #: save written before morale existed reads from the class.
    morale: int = field(default=MORALE_START)

    #: Turns of leave left, counted exactly like a wound.
    leave_turns: int = field(default=0)

    #: The turn leave was granted in, which does not count towards serving it.
    leave_on_turn: int = field(default=-1)

    #: Turns since he last had any. Starts at zero for everyone, including the pilots
    #: of a campaign that predates this, so nobody is punished for a rest they were
    #: never able to ask for.
    turns_since_leave: int = field(default=0)

    #: He has asked, and is waiting to be told yes or no.
    wants_leave: bool = field(default=False)

    #: Turns he has spent at rock bottom, before he stops coming back.
    turns_at_zero: int = field(default=0)

    def __setstate__(self, state: dict[str, Any]) -> None:
        state.setdefault("wounded_turns", 0)
        state.setdefault("wounded_on_turn", -1)
        state.setdefault("morale", MORALE_START)
        state.setdefault("leave_turns", 0)
        state.setdefault("leave_on_turn", -1)
        state.setdefault("turns_since_leave", 0)
        state.setdefault("wants_leave", False)
        state.setdefault("turns_at_zero", 0)
        self.__dict__.update(state)

    @property
    def alive(self) -> bool:
        return self.status not in (PilotStatus.Dead, PilotStatus.Deserted)

    @property
    def deserted(self) -> bool:
        return self.status is PilotStatus.Deserted

    @property
    def refuses_to_fly(self) -> bool:
        """Rock bottom. He is not offered for a sortie, the way a wounded man is not."""
        return self.morale <= REFUSES_TO_FLY_AT

    @property
    def on_leave(self) -> bool:
        return self.status is PilotStatus.OnLeave

    @property
    def wounded(self) -> bool:
        return self.status is PilotStatus.Wounded

    def send_on_leave(self, turns: int = 0, turn: int = -1) -> None:
        """Grant leave, for ``turns`` of them or open-ended when that is zero.

        Open-ended is how leave has always worked and how the Air Wing button still
        grants it: he stays out until the player fetches him. A granted request carries
        a length, and then it runs down on its own like a wound.
        """
        if self.status is not PilotStatus.Active:
            raise RuntimeError("Only active pilots may be sent on leave")
        self.status = PilotStatus.OnLeave
        self.leave_turns = turns
        self.leave_on_turn = turn
        self.wants_leave = False

    def serve_a_turn_of_leave(self, turn: int) -> None:
        """One turn of leave used up. Open-ended leave never runs out on its own."""
        if not self.leave_turns or turn == self.leave_on_turn:
            return
        self.leave_turns -= 1
        if self.leave_turns <= 0:
            self.return_from_leave()

    def return_from_leave(self) -> None:
        if self.status is not PilotStatus.OnLeave:
            raise RuntimeError("Only pilots on leave may be returned from leave")
        self.status = PilotStatus.Active
        self.leave_turns = 0
        self.leave_on_turn = -1
        self.turns_since_leave = 0

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

    def desert(self) -> None:
        """He has had enough."""
        self.status = PilotStatus.Deserted
        self.wounded_turns = 0
        self.wounded_on_turn = -1
        self.leave_turns = 0
        self.wants_leave = False

    @classmethod
    def random(cls, faker: Faker) -> Pilot:
        return Pilot(faker.name())
