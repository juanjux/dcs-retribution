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


@dataclass
class Pilot:
    name: str
    player: bool = field(default=False)
    status: PilotStatus = field(default=PilotStatus.Active)
    record: PilotRecord = field(default_factory=PilotRecord)

    @property
    def alive(self) -> bool:
        return self.status is not PilotStatus.Dead

    @property
    def on_leave(self) -> bool:
        return self.status is PilotStatus.OnLeave

    def send_on_leave(self) -> None:
        if self.status is not PilotStatus.Active:
            raise RuntimeError("Only active pilots may be sent on leave")
        self.status = PilotStatus.OnLeave

    def return_from_leave(self) -> None:
        if self.status is not PilotStatus.OnLeave:
            raise RuntimeError("Only pilots on leave may be returned from leave")
        self.status = PilotStatus.Active

    def kill(self) -> None:
        self.status = PilotStatus.Dead

    @classmethod
    def random(cls, faker: Faker) -> Pilot:
        return Pilot(faker.name())
