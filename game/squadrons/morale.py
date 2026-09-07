"""How a pilot is holding up, and what that is worth.

Morale runs 0 to 100 and starts at 50. It moves with what the campaign does to a man --
losing his aircraft, watching his squadron die, going a long time without leave -- and it
moves back with what goes well. Everything it reads is already in the debriefing; nothing
here needs the mission to report anything new.

The numbers below are the defaults. Each one has a settings key beside it so a campaign
can be tuned without editing code, exactly as :mod:`game.squadrons.experience` does for
the survival odds.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from dcs.task import OptReactOnThreat
from dcs.unit import Skill

from game.dcs.skills import SKILL_LADDER

if TYPE_CHECKING:
    from game.settings import Settings

MORALE_MIN = 0
MORALE_MAX = 100

#: Where a pilot starts, and where he drifts back to. A campaign that has done nothing
#: to a man yet should not have an opinion about him.
MORALE_START = 50


@dataclass(frozen=True)
class MoraleEvent:
    """One thing that moves a pilot, and how far.

    ``default`` is signed: negative for the things that wear him down. The settings key
    holds the same sign, so a campaign that wants a harder war only has to make the
    numbers bigger.
    """

    key: str
    default: int
    reason: str

    def amount(self, settings: Optional["Settings"] = None) -> int:
        if settings is None:
            return self.default
        return int(getattr(settings, self.key, self.default))


# --- what wears him down ----------------------------------------------------

#: He came home without the aircraft. The plugin does not report ejections, but a pilot
#: who lost his aircraft and lived is the same man in the same parachute.
LOST_AIRCRAFT = MoraleEvent("morale_lost_aircraft", -15, "lost his aircraft")

#: He flew a strike, a CAS or a SEAD and destroyed nothing at all.
ACHIEVED_NOTHING = MoraleEvent("morale_achieved_nothing", -5, "came home empty")

#: Per pilot of his own squadron killed. Friendship weighting is Tier IV.
SQUADRON_DEATH = MoraleEvent("morale_squadron_death", -8, "lost a squadron mate")

#: On top of the above, for the men who were in the same flight and watched it happen.
#: The squadron hears about it; the flight saw it.
FLIGHT_DEATH = MoraleEvent("morale_flight_death", -6, "watched his wingman go down")

#: Per turn a squadron mate will be in hospital, up to a cap. A wound is not a death,
#: but a man carried out for four turns is felt more than one back next week.
SQUADRON_WOUND = MoraleEvent("morale_squadron_wound", -2, "a squadron mate was wounded")

#: And again, extra, for the flight he was in.
FLIGHT_WOUND = MoraleEvent("morale_flight_wound", -2, "a man in his flight was hit")

#: However long the medics keep him, a wound is never felt as hard as a grave.
WOUND_TURNS_FELT = 3

#: A base of his coalition changed hands.
BASE_LOST = MoraleEvent("morale_base_lost", -6, "a base was lost")

#: Turns a pilot will go without leave before it starts to tell on him.
TURNS_BEFORE_LEAVE_IS_MISSED = 5

#: Per turn beyond the fifth without leave, and it keeps growing.
NO_LEAVE = MoraleEvent("morale_no_leave", -2, "no leave in a long time")

#: He asked for leave and was told no.
LEAVE_REFUSED = MoraleEvent("morale_leave_refused", -6, "leave refused")

#: He was on leave and was called back before it was up. Worse than never getting it:
#: he had it in his hand.
LEAVE_CANCELLED = MoraleEvent("morale_leave_cancelled", -10, "leave cut short")

# --- what builds him up -----------------------------------------------------

#: Per enemy aircraft shot down.
AIR_KILL = MoraleEvent("morale_air_kill", 10, "shot one down")

#: Per thing destroyed that was not what his package was sent for.
UNPLANNED_KILL = MoraleEvent("morale_unplanned_kill", 3, "took a target of opportunity")

#: He flew the sortie and brought the aircraft home.
MISSION_COMPLETE = MoraleEvent("morale_mission_complete", 4, "flew the mission")

#: His own promotion.
PROMOTED = MoraleEvent("morale_promoted", 12, "promoted")

#: Per turn of leave served.
ON_LEAVE = MoraleEvent("morale_on_leave", 8, "on leave")

#: Every event, for the settings page and for tests that check nothing was forgotten.
MORALE_EVENTS: tuple[MoraleEvent, ...] = (
    LOST_AIRCRAFT,
    ACHIEVED_NOTHING,
    SQUADRON_DEATH,
    FLIGHT_DEATH,
    SQUADRON_WOUND,
    FLIGHT_WOUND,
    BASE_LOST,
    NO_LEAVE,
    LEAVE_REFUSED,
    LEAVE_CANCELLED,
    AIR_KILL,
    UNPLANNED_KILL,
    MISSION_COMPLETE,
    PROMOTED,
    ON_LEAVE,
)


def wound_is_felt_for(turns: int) -> int:
    """How many times a wound of this length is counted against a squadron."""
    return max(1, min(WOUND_TURNS_FELT, turns))


def clamp(morale: int) -> int:
    return max(MORALE_MIN, min(MORALE_MAX, morale))


def drift(morale: int) -> int:
    """One step back towards the middle, from either side.

    Without this a pilot who had one very good or one very bad turn stays there for the
    rest of the campaign. It is applied once a turn, before anything else.

    A man at rock bottom is the exception: he does not mend on his own. He will not fly,
    so he can earn nothing back, and the only thing that lifts him is leave. That is what
    makes the warning on his row worth reading -- ignore it and he is gone.
    """
    if morale <= MORALE_MIN:
        return 0
    if morale > MORALE_START:
        return -1
    if morale < MORALE_START:
        return 1
    return 0


#: The rungs of the ladder, and so the number of stars a pilot can wear.
RANK_LEVELS = len(SKILL_LADDER)


def rank_level(skill: Skill) -> int:
    """Which rung he stands on, 1 to 5, for the stars on his row."""
    try:
        return SKILL_LADDER.index(skill) + 1
    except ValueError:
        return 1


def resistance(skill: Skill) -> float:
    """How much of a knock a pilot of this rank actually takes.

    Rank is armour: a squadron leader has seen it before. It only softens the falls --
    nobody is too senior to be pleased about a promotion.
    """
    try:
        rung = SKILL_LADDER.index(skill)
    except ValueError:
        rung = 0
    return 1.0 - 0.15 * rung


def apply(morale: int, event: MoraleEvent, skill: Skill, settings: Any = None) -> int:
    """Move a pilot by one event, softened by his rank if it is a knock."""
    amount = event.amount(settings)
    if amount < 0:
        amount = -max(1, round(-amount * resistance(skill)))
    return clamp(morale + amount)


#: The tasks a pilot can come home from having failed. A CAP that saw nobody has not
#: failed at anything; a strike that dropped on nothing has.
STRIKE_TASKS: frozenset[str] = frozenset(
    {
        "CAS",
        "BAI",
        "STRIKE",
        "DEAD",
        "SEAD",
        "SEAD_SWEEP",
        "OCA_RUNWAY",
        "OCA_AIRCRAFT",
        "ANTISHIP",
        "ARMED_RECON",
    }
)


# --- what it does -----------------------------------------------------------

#: Above the first he flies a rung better, below the second a rung worse.
SKILL_SHIFT_HIGH = 85
SKILL_SHIFT_LOW = 15


def skill_shift(morale: int, settings: Any = None) -> int:
    """-1, 0 or +1 rungs, from how he is holding up."""
    high = SKILL_SHIFT_HIGH
    low = SKILL_SHIFT_LOW
    if settings is not None:
        high = getattr(settings, "morale_skill_high", high)
        low = getattr(settings, "morale_skill_low", low)
    if morale > high:
        return 1
    if morale < low:
        return -1
    return 0


def shifted_skill(skill: Skill, morale: int, settings: Any = None) -> Skill:
    """The rung he will actually fly at, clamped to the ladder."""
    shift = skill_shift(morale, settings)
    if not shift:
        return skill
    try:
        rung = SKILL_LADDER.index(skill)
    except ValueError:
        return skill
    return SKILL_LADDER[max(0, min(len(SKILL_LADDER) - 1, rung + shift))]


@dataclass(frozen=True)
class MoraleState:
    """What a squadron commander would be told, rather than a number.

    ``floor`` is the bottom of the band, taken inclusively. ``severity`` is what the
    player should read into it: 0 nothing, 1 worth an eye, 2 do something about it now.
    """

    floor: int
    name: str
    severity: int


#: The figure itself is for the pilot dialog, the ledger and the API. Everywhere the
#: player looks he gets the name, exactly as a rank stands in for a skill level.
MORALE_STATES: tuple[MoraleState, ...] = (
    MoraleState(85, "Triumphant", 0),
    MoraleState(60, "Confident", 0),
    MoraleState(40, "Normal", 0),
    MoraleState(15, "Shaken", 1),
    MoraleState(1, "Shattered", 2),
    MoraleState(MORALE_MIN, "Broken", 2),
)


def morale_state(morale: int) -> MoraleState:
    for state in MORALE_STATES:
        if morale >= state.floor:
            return state
    return MORALE_STATES[-1]


#: Multiplier on everything a sortie pays. A band's number is its lower bound, taken
#: inclusively, so a pilot sitting exactly on a boundary gets the better of the two.
XP_MULTIPLIER_BANDS: tuple[tuple[int, float], ...] = (
    (81, 1.5),  # above 80
    (60, 1.2),
    (40, 1.0),
    (10, 0.8),
    (MORALE_MIN, 0.5),
)


def xp_multiplier(morale: int) -> float:
    """What a sortie is worth to a man in this state."""
    for floor, multiplier in XP_MULTIPLIER_BANDS:
        if morale >= floor:
            return multiplier
    return 1.0


#: What each rung of difference to the best pilot in the flight is worth to the others.
LEARNING_PER_RUNG = 0.1


def learning_bonus(own: Skill, best_in_flight: Skill) -> float:
    """Flying with somebody better than you is worth something.

    Only the best man in the formation counts, and only for the ones below him: he gets
    nothing out of it himself. A cadet on an Excellent's wing is four rungs down, so he
    learns four rungs' worth.
    """
    try:
        mine = SKILL_LADDER.index(own)
        theirs = SKILL_LADDER.index(best_in_flight)
    except ValueError:
        return 0.0
    return max(0, theirs - mine) * LEARNING_PER_RUNG


# --- how the flight behaves -------------------------------------------------

#: Below this the flight routes around what frightens it; below the second it turns for
#: home when the threat is serious. These are group options, so they follow the lead.
SHAKEN_BELOW = 20
BROKEN_BELOW = 10


def threat_reaction(morale: int) -> OptReactOnThreat.Values:
    """What the lead will let his flight do about a threat."""
    if morale < BROKEN_BELOW:
        return OptReactOnThreat.Values.AllowAbortMission
    if morale < SHAKEN_BELOW:
        return OptReactOnThreat.Values.ByPassAndEscape
    return OptReactOnThreat.Values.EvadeFire


def rtb_on_bingo(morale: int) -> bool:
    """The shaken flight goes home at bingo; the confident one presses on."""
    return morale < SHAKEN_BELOW


# --- the rest ---------------------------------------------------------------


#: A wound keeps a hollow man out longer and a cheerful one less.
def recovery_turns(turns: int, morale: int) -> int:
    if morale < SHAKEN_BELOW:
        return turns + 1
    if morale > SKILL_SHIFT_HIGH:
        return max(1, turns - 1)
    return turns


#: How much morale moves the survival roll, as a fraction added to the rank's chance.
def survival_modifier(morale: int) -> float:
    """The steady man gets out of the aircraft; the hollow one does not."""
    return (morale - MORALE_START) / 500.0  # +/- 10 points at the extremes


#: The turns of leave the dialog offers when a pilot has not named a number, and the
#: most the player can ever grant at once.
DEFAULT_LEAVE_TURNS = 2
MAX_LEAVE_TURNS = 6

#: How long a man asks for, by how he is holding up. Nobody asks for leave in the
#: abstract: he asks for a morning, a day, a week. The player can then grant less.
LEAVE_ASKED_FOR: tuple[tuple[int, int, int], ...] = (
    (40, 1, 2),  # Normal and better: a couple of days
    (15, 2, 3),  # Shaken
    (MORALE_MIN, 3, 4),  # Shattered or Broken: he wants out for a while
)


def requested_leave_turns(morale: int, roll: Optional[float] = None) -> int:
    """The number of turns this pilot asks for."""
    for floor, low, high in LEAVE_ASKED_FOR:
        if morale >= floor:
            span = high - low
            if roll is None:
                roll = random.random()
            return min(MAX_LEAVE_TURNS, low + int(roll * (span + 1)))
    return DEFAULT_LEAVE_TURNS


#: The window that counts as "lately" when deciding whether a man has had enough, and
#: how many turns of his flying is worth keeping to work it out.
RECENT_SORTIE_WINDOW = 5
SORTIE_HISTORY_LIMIT = 20


def workload_factor(flown: int, window: int = RECENT_SORTIE_WINDOW) -> float:
    """How hard he has been worked lately, as a multiplier on wanting a rest.

    A man who has flown every turn of the last five asks far more readily than one who
    has sat on the ground throughout -- and the one who flew twice sits between them.
    """
    if window <= 0:
        return 1.0
    return 0.6 + 0.8 * (max(0, min(window, flown)) / window)


def leave_request_chance(
    morale: int,
    base_percent: int,
    flown_recently: int = 0,
    window: int = RECENT_SORTIE_WINDOW,
) -> float:
    """How likely this pilot is to ask for leave this turn, 0 to 1.

    Two things decide it: how he is holding up, and how hard he has been worked. Never
    zero -- a contented, idle man still wants a week off now and then, he just does not
    need one.
    """
    factor = max(0.25, min(2.0, 2.0 - morale / (MORALE_START * 1.0)))
    factor *= workload_factor(flown_recently, window)
    return max(0.0, min(1.0, base_percent / 100.0 * factor))


#: A movement this big is worth telling the player about in the debriefing; smaller
#: ones are the ordinary churn of a campaign and only go to the ledger.
MORALE_WORTH_REPORTING = 10

#: The chance, per turn spent at rock bottom, that a pilot simply stops coming --
#: one entry per rung of the ladder, from cadet to squadron leader. Rank is what keeps
#: a man in his seat when nothing else does, so the veteran is the last to go.
DESERTION_CHANCE_BY_RUNG: tuple[float, ...] = (0.09, 0.07, 0.05, 0.03, 0.01)


def desertion_chance(skill: Skill) -> float:
    """How likely this pilot is to walk away this turn, 0 to 1."""
    try:
        rung = SKILL_LADDER.index(skill)
    except ValueError:
        rung = 0
    return DESERTION_CHANCE_BY_RUNG[min(rung, len(DESERTION_CHANCE_BY_RUNG) - 1)]


@dataclass(frozen=True)
class MoraleLogEntry:
    """One thing that moved a pilot, kept so it can be shown back to the player.

    The pilot dialog is where this is read; nothing in the campaign depends on it.
    """

    turn: int
    amount: int
    reason: str
    morale_after: int


#: How many entries a pilot carries. Enough for the dialog to show a campaign's worth
#: of a man's ups and downs without the roll of them bloating every save.
MORALE_HISTORY_LIMIT = 60

#: At or below this he will not fly at all.
REFUSES_TO_FLY_AT = 0
