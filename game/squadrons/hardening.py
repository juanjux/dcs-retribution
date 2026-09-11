"""How much a pilot has already been through, and what it is worth.

Morale is how he is this week. Hardening is what the bad weeks left behind: a point or
three for every turn he spends Shaken or worse, and **it never comes off**. A squadron
that has been through something is not the squadron that arrived, which is the whole
point of it -- a run of losses used to take a whole squadron to Broken together and
leave it there, each death landing on men who were already at the bottom.

What it buys is not cheerfulness. He feels the knocks exactly as often; they land
softer. He is likelier to walk away from a wreck, because he has been in one. And his
skin is thicker in both directions: a man who has watched enough people die keeps the
next one at arm's length, which is the price -- the rung of skill a crew that gets on
flies at is that much further away for a squadron that has been fed into a grinder --
and shrugs off what would have been an insult a year ago, which is not.

None of it is earned in a hospital bed or at home on leave. He may be lower there than
anywhere; this comes from turning up and doing it again.

The numbers below are defaults. Each carries the settings key that overrides it,
exactly as :mod:`game.squadrons.morale` and :mod:`game.squadrons.friendship` do.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from game.squadrons import morale as morale_rules

if TYPE_CHECKING:
    from game.squadrons.pilot import Pilot

#: The ends of the ruler. Nothing takes it back down: a man does not unlearn what a bad
#: month taught him, and a quiet spell is a rest rather than an education.
HARDENING_MIN = 0
HARDENING_MAX = 40

#: What one turn in each band leaves behind, by the state he *arrived* in. Only the
#: bands that cost him something are in it: a good week teaches nothing about surviving
#: a bad one.
SHAKEN = 1
SHATTERED = 2
BROKEN = 3

#: Which state each of those belongs to, and the settings key that sizes it.
HARDENING_BY_STATE: tuple[tuple[str, str, int], ...] = (
    ("Shaken", "hardening_shaken", SHAKEN),
    ("Shattered", "hardening_shattered", SHATTERED),
    ("Broken", "hardening_broken", BROKEN),
)

#: What the whole ruler is worth, as percentages reached at the top of it and scaled
#: straight down from there. Written as "what a man at the very top gets" rather than as
#: a rate per point, because that is the figure worth arguing about -- the rate falls
#: out of it and the ceiling together.
MORALE_RELIEF_FULL = 80
SURVIVAL_FULL = 20
FRIENDSHIP_DAMPING_FULL = 60


def _setting(settings: Any, key: str, default: Any) -> Any:
    return default if settings is None else getattr(settings, key, default)


def _percent(settings: Any, key: str, default: Any) -> float:
    return float(_setting(settings, key, default)) / 100.0


def in_play(settings: Any) -> bool:
    """Whether any of this is switched on.

    It rides on morale, not merely on Live Pilots: it is earned from the morale bands
    and most of what it does is to morale. With morale off there is nothing for a man
    to be hardened *by*.
    """
    return (
        bool(_setting(settings, "live_pilots_enabled", True))
        and bool(_setting(settings, "morale_enabled", True))
        and bool(_setting(settings, "hardening_enabled", True))
    )


def ceiling(settings: Any = None) -> int:
    return int(_setting(settings, "hardening_max", HARDENING_MAX))


def share(hardened: int, settings: Any = None) -> float:
    """How far along the ruler he is, 0 to 1. Everything else is priced off this."""
    top = ceiling(settings)
    if top <= 0:
        return 0.0
    return max(0.0, min(1.0, hardened / top))


# --- earning it ------------------------------------------------------------------


def gain_for(morale: int, settings: Any = None) -> int:
    """What a turn spent in this state is worth, and nothing for a good one."""
    if not in_play(settings):
        return 0
    state = morale_rules.morale_state(morale, settings).name
    for name, key, default in HARDENING_BY_STATE:
        if name == state:
            return int(_setting(settings, key, default))
    return 0


def harden(pilot: Pilot, morale: int, settings: Any = None) -> int:
    """A turn served in a bad place. Returns how far he moved, which is never down.

    ``morale`` is the figure he *arrived* with rather than the one he leaves with: the
    turn is judged on the state he spent it in, the same way the desertion roll is.

    A hospital bed and a week at home are not bad places in the sense that matters.
    He may be as low there as anywhere -- lower, often -- but this is earned by turning
    up and doing it again, not by feeling terrible somewhere safe.
    """
    if pilot.wounded or pilot.on_leave:
        return 0
    gained = gain_for(morale, settings)
    if not gained:
        return 0
    before = pilot.hardened
    pilot.hardened = min(ceiling(settings), before + gained)
    return pilot.hardened - before


# --- what it is worth ------------------------------------------------------------


def morale_relief(hardened: int, settings: Any = None) -> float:
    """How much of a knock he no longer feels, as a fraction of it.

    Knocks only. Nobody is too hardened to be pleased about a promotion, which is the
    same asymmetry rank already has in :func:`game.squadrons.morale.resistance`.
    """
    if not in_play(settings):
        return 0.0
    full = _percent(settings, "hardening_morale_relief_full", MORALE_RELIEF_FULL)
    return share(hardened, settings) * full


def survival_bonus(hardened: int, settings: Any = None) -> float:
    """What having been shot at before is worth when it happens again.

    Added to the roll that gets him out of the aircraft and to the one that has the
    medics reach him in time. He has done this before: he knows when to stop trying to
    save the jet.
    """
    if not in_play(settings):
        return 0.0
    full = _percent(settings, "hardening_survival_full", SURVIVAL_FULL)
    return share(hardened, settings) * full


def friendship_damping(hardened: int, settings: Any = None) -> float:
    """How much less of any of it he feels, as a fraction.

    Both ways, which is the whole of what a thick skin is: a man who has watched enough
    people go down does not get attached at the speed the new arrival does, and he does
    not take offence at that speed either. The first half is the price of hardening;
    the second is another thing it buys.
    """
    if not in_play(settings):
        return 0.0
    full = _percent(
        settings, "hardening_friendship_damping_full", FRIENDSHIP_DAMPING_FULL
    )
    return share(hardened, settings) * full


def feels(pilot: Pilot, amount: float, settings: Any = None) -> float:
    """How much of a movement in what he thinks of somebody actually lands on him.

    Only his own opinions: what everybody else makes of the hard old sergeant is
    nobody's business but theirs. Both directions, though -- he is slower to warm to
    the new arrival *and* slower to hold anything against him, because it is one skin
    and it is thick both ways.
    """
    if not amount:
        return amount
    return amount * (1.0 - friendship_damping(pilot.hardened, settings))
