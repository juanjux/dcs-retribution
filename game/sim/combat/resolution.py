"""How a combat between two flights would be settled.

It was a setting -- "Resolve combat when fast forwarding by" -- and it lived in
:mod:`game.settings.settings`. Fast forward is gone, so nothing constructs a combat
any more and nothing reads this; it stays with the classes that take it as a
parameter, rather than in the settings, where it would look like a choice the player
still has.
"""

from enum import Enum, unique


@unique
class CombatResolutionMethod(Enum):
    PAUSE = "Pause simulation"
    RESOLVE = "Resolve combat"
    SKIP = "Skip combat"
