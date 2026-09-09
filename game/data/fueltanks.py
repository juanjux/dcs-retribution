"""How much fuel an external tank actually carries.

DCS has no "this is a fuel tank, holding N pounds" field: a store is a name, a CLSID
and a laden weight. So the fuel is read off the three things that are there, in
descending order of how much they can be trusted.

Wanted because the payload editor's fuel figure was internal only, which understates a
strike loadout by a third or more, and the flight plan's fuel estimate was reading the
same number -- the mission generator's own warning about running out already says
"this estimate does not account for external fuel tanks".
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional

from dcs.weapons_data import weapon_ids

from game.utils import Mass, kgs

if TYPE_CHECKING:
    from game.ato.loadouts import Loadout

#: Jet fuel at 15C. DCS models JP-8/F-34 at about this, and the tanks whose weights
#: can be checked against their stated volume agree to within a couple of per cent.
KG_PER_LITRE = 0.81
LITRES_PER_US_GALLON = 3.785412

#: Share of a tank's laden weight that is fuel, for the ones that state no volume and
#: ship no empty twin. Deliberately low: a tank is mostly fuel, but guessing high here
#: would flatter a loadout that cannot actually make it home.
ASSUMED_FUEL_SHARE = 0.85

_VOLUME = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:x\s*)?"
    r"(?:(?:u\.?\s*s\.?|us)\s*)?"
    r"(gal(?:lons?)?|lit(?:er|re)s?|l)\b",
    re.IGNORECASE,
)
_MASS = re.compile(r"(\d+(?:[.,]\d+)?)\s*kg\b", re.IGNORECASE)

#: Says "fuel" outright -- "AJS External-tank 1013kg fuel" never says "tank" next to
#: it -- or is a tank with a stated volume, which is how "1100L Tank" is spelled.
_SAYS_FUEL = re.compile(r"fuel|drop\s*tank|tip\s*tank", re.IGNORECASE)
_TANK = re.compile(r"\btanks?\b", re.IGNORECASE)
#: Tanks that hold something else. A "Color Oil Tank" is a tank and is not fuel.
_NOT_FUEL = re.compile(r"\boil\b|\bammo\b|\bwater\b|\bsmoke\b", re.IGNORECASE)


def _number(text: str) -> float:
    return float(text.replace(",", "."))


def external_fuel(clsid: str) -> Optional[Mass]:
    """The fuel in this store, or None when it is not a fuel tank."""
    data: Any = weapon_ids.get(clsid)
    if data is None:
        return None
    name = str(data.get("name", ""))
    if _NOT_FUEL.search(name):
        return None
    volume = _VOLUME.search(name)
    if not _SAYS_FUEL.search(name) and not (_TANK.search(name) and volume):
        return None
    if "empty" in name.lower():
        return kgs(0.0)

    weight = data.get("weight")
    carried = _carried(name, volume, weight)
    if carried is None:
        return None
    if weight is not None:
        # Never more than the store weighs. DCS's laden weights and its printed
        # volumes do not always agree, and one entry is a fuel QUANTITY rather than a
        # tank -- "Fuel 10940 kg", weighing 37 -- which the name alone cannot tell
        # apart from a very large tank.
        carried = min(carried, float(weight))
    return kgs(carried)


def _carried(
    name: str, volume: Optional[re.Match[str]], weight: Optional[float]
) -> Optional[float]:
    if volume is not None:
        amount = _number(volume.group(1))
        litres = (
            amount * LITRES_PER_US_GALLON
            if volume.group(2).lower().startswith("gal")
            else amount
        )
        return litres * KG_PER_LITRE
    mass = _MASS.search(name)
    if mass is not None:
        return _number(mass.group(1))
    if weight is None:
        return None
    empty = _empty_twin(name)
    if empty is not None:
        return max(0.0, float(weight) - empty)
    return float(weight) * ASSUMED_FUEL_SHARE


def _empty_twin(name: str) -> Optional[float]:
    """The laden weight of the same tank's "(Empty)" entry, when DCS ships one."""
    wanted = f"{name} (empty)".lower()
    for entry in weapon_ids.values():
        data: Any = entry
        if str(data.get("name", "")).lower() == wanted:
            weight = data.get("weight")
            return None if weight is None else float(weight)
    return None


def loadout_fuel(loadout: "Loadout") -> Mass:
    """Fuel in every external tank on this loadout."""
    total = 0.0
    for weapon in loadout.pylons.values():
        if weapon is None:
            continue
        carried = external_fuel(weapon.clsid)
        if carried is not None:
            total += carried.kgs
    return kgs(total)
