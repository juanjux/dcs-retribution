"""What a sortie is worth, and what it costs to be promoted.

Experience is awarded from the debriefing rather than from a counter, so a pilot is paid
for what he did: who he shot down, what he destroyed, and whether he brought the aircraft
home. The rank that buys is defined in :mod:`game.dcs.skills`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from dcs.unit import Skill

from game.config import REWARDS

#: An enemy aircraft.
XP_AIR_KILL = 500

#: Flying the sortie and coming back from it. Losing the aircraft forfeits this.
XP_MISSION_COMPLETE = 500

#: A vehicle: a tank, a SAM launcher, a convoy truck, a front line gun.
XP_GROUND_KILL = 200

#: A hull. Flat, because 91 of the 110 ships shipped with Retribution are priced at zero
#: -- a Ticonderoga is worth nothing to `unit_type.price`, so value would score it as
#: nothing. Pricing the fleet properly is a separate job.
XP_SHIP_KILL = 300

#: Buildings are paid by what they are worth. REWARDS is income per turn per element, in
#: millions, so an oil platform at 10 pays 500 and a warehouse at 2 pays 100.
XP_PER_BUILDING_MILLION = 50

#: Something destroyed that has no entry anywhere: still worth flying out for.
XP_UNKNOWN_KILL = 100


def building_xp(category: Optional[str]) -> int:
    """What one element of a ``category`` objective is worth."""
    if category is None:
        return XP_UNKNOWN_KILL
    reward = REWARDS.get(category)
    if reward is None:
        return XP_UNKNOWN_KILL
    return max(1, round(reward * XP_PER_BUILDING_MILLION))


#: How likely a pilot is to walk away from a combat loss, by the rung he flies at. A cadet
#: usually does not; a squadron leader usually does.
SURVIVAL_BY_SKILL: dict[Skill, float] = {
    Skill.Average: 0.35,
    Skill.Good: 0.50,
    Skill.High: 0.65,
    Skill.Excellent: 0.80,
}

#: Cadet is injected into pydcs' enum at import time, so it cannot be a literal above.
SURVIVAL_CADET = 0.20


def survival_chance(skill: Skill) -> float:
    return SURVIVAL_BY_SKILL.get(skill, SURVIVAL_CADET)


@dataclass
class PilotDeath:
    """A pilot who did not come back, and what is known about who did it."""

    pilot_name: str
    squadron: str
    aircraft: str
    #: Already-formatted attribution: a roster pilot, a human's name, an airframe type,
    #: "a crash", or a friendly-fire note. None when nothing at all is known.
    killed_by: Optional[str] = None
    friendly_fire: bool = False


@dataclass
class PilotPromotion:
    pilot_name: str
    squadron: str
    from_rank: str
    to_rank: str


@dataclass
class PilotOutcomes:
    """What became of the aircrew this mission, for the debriefing to read.

    Built where the decisions are made -- promotions as experience is awarded, the other
    two as losses are committed -- and carried on the Debriefing, which the results
    processor always finishes with before the window is shown.
    """

    promotions: list[PilotPromotion] = field(default_factory=list)
    survivors: list[PilotDeath] = field(default_factory=list)
    deaths: list[PilotDeath] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.promotions or self.survivors or self.deaths)
