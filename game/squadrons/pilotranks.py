from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from dcs.country import Country
from dcs.unit import Skill

from game.dcs.skills import SKILL_LADDER


@dataclass(frozen=True)
class Rank:
    """One rung of the promotion ladder, in one nation's naming."""

    abbreviation: str
    name: str


# A ladder is always five rungs, one per DCS AI skill, ascending: see
# ``game.dcs.skills.SKILL_LADDER``. They are the OF-1 to OF-4 officer grades of a
# flying service -- roughly O-1 through O-5 in US terms -- which is the span a
# squadron pilot actually flies in.
RankLadder = tuple[Rank, Rank, Rank, Rank, Rank]

# Used when the country has no entry, and whenever the player asks for country-neutral
# naming. Deliberately the most widely recognised form rather than a NATO code, which
# nobody reads at a glance in a cockpit label.
GENERIC_RANKS: RankLadder = (
    Rank("2ndLt", "Second Lieutenant"),
    Rank("1stLt", "First Lieutenant"),
    Rank("Capt", "Captain"),
    Rank("Maj", "Major"),
    Rank("LtCol", "Lieutenant Colonel"),
)

USAF_RANKS: RankLadder = GENERIC_RANKS

# No ranks at all: the DCS skill levels themselves, for players who would rather
# read the mechanic than a fiction over it.
SKILL_NAME_RANKS: RankLadder = (
    Rank("Cdt", "Cadet"),
    Rank("Avg", "Average"),
    Rank("Gdd", "Good"),
    Rank("Hig", "High"),
    Rank("Exc", "Excellent"),
)

USN_RANKS: RankLadder = (
    Rank("ENS", "Ensign"),
    Rank("LTJG", "Lieutenant Junior Grade"),
    Rank("LT", "Lieutenant"),
    Rank("LCDR", "Lieutenant Commander"),
    Rank("CDR", "Commander"),
)

# The RAF pattern, shared across the Commonwealth air forces that kept it.
RAF_RANKS: RankLadder = (
    Rank("PltOff", "Pilot Officer"),
    Rank("FgOff", "Flying Officer"),
    Rank("FltLt", "Flight Lieutenant"),
    Rank("SqnLdr", "Squadron Leader"),
    Rank("WgCdr", "Wing Commander"),
)

# Soviet/Russian pattern, transliterated. The junior lieutenant grade gives this one a
# natural bottom rung where western ladders have to reach down to cadet.
VVS_RANKS: RankLadder = (
    Rank("MlLt", "Mladshiy Leytenant"),
    Rank("Lt", "Leytenant"),
    Rank("StLt", "Starshiy Leytenant"),
    Rank("Kpt", "Kapitan"),
    Rank("Mjr", "Mayor"),
)

FRENCH_RANKS: RankLadder = (
    Rank("SLt", "Sous-lieutenant"),
    Rank("Lt", "Lieutenant"),
    Rank("Cne", "Capitaine"),
    Rank("Cdt", "Commandant"),
    Rank("LCL", "Lieutenant-colonel"),
)

LUFTWAFFE_RANKS: RankLadder = (
    Rank("Lt", "Leutnant"),
    Rank("OLt", "Oberleutnant"),
    Rank("Hptm", "Hauptmann"),
    Rank("Maj", "Major"),
    Rank("OTL", "Oberstleutnant"),
)

SPANISH_RANKS: RankLadder = (
    Rank("Alf", "Alferez"),
    Rank("Tte", "Teniente"),
    Rank("Cap", "Capitan"),
    Rank("Cte", "Comandante"),
    Rank("Tcol", "Teniente Coronel"),
)

ITALIAN_RANKS: RankLadder = (
    Rank("Sten", "Sottotenente"),
    Rank("Ten", "Tenente"),
    Rank("Cap", "Capitano"),
    Rank("Magg", "Maggiore"),
    Rank("TenCol", "Tenente Colonnello"),
)

IDF_RANKS: RankLadder = (
    Rank("Sgm", "Segen Mishne"),
    Rank("Sgn", "Segen"),
    Rank("Srn", "Seren"),
    Rank("RvS", "Rav Seren"),
    Rank("SgA", "Sgan Aluf"),
)

# Keyed by the exact pydcs ``Country.name`` (see ``dcs.countries.country_dict``), the
# same key ``pilotnames.COUNTRY_FAKER_LOCALES`` uses. Anything unlisted -- including the
# multinational and irregular "countries" -- falls through to GENERIC_RANKS, so a
# missing entry can only ever make a label plainer, never break generation.
COUNTRY_RANKS: dict[str, RankLadder] = {
    # --- Anglosphere -------------------------------------------------------
    "USA": USAF_RANKS,
    "USAF Aggressors": USAF_RANKS,
    "UK": RAF_RANKS,
    "Canada": RAF_RANKS,
    "Australia": RAF_RANKS,
    "New Zealand": RAF_RANKS,
    # --- Western & Central Europe -----------------------------------------
    "France": FRENCH_RANKS,
    "Belgium": FRENCH_RANKS,
    "Germany": LUFTWAFFE_RANKS,
    "GDR": LUFTWAFFE_RANKS,
    "Third Reich": LUFTWAFFE_RANKS,
    "Austria": LUFTWAFFE_RANKS,
    "Switzerland": LUFTWAFFE_RANKS,
    "Italy": ITALIAN_RANKS,
    "Italian Social Republic": ITALIAN_RANKS,
    "Spain": SPANISH_RANKS,
    # --- The Soviet pattern ------------------------------------------------
    "Russia": VVS_RANKS,
    "USSR": VVS_RANKS,
    "Ukraine": VVS_RANKS,
    "Belarus": VVS_RANKS,
    "Kazakhstan": VVS_RANKS,
    "Georgia": VVS_RANKS,
    "Bulgaria": VVS_RANKS,
    "Poland": VVS_RANKS,
    "Czech Republic": VVS_RANKS,
    "Slovakia": VVS_RANKS,
    "Hungary": VVS_RANKS,
    "Romania": VVS_RANKS,
    "Serbia": VVS_RANKS,
    "Croatia": VVS_RANKS,
    # --- Middle East -------------------------------------------------------
    "Israel": IDF_RANKS,
}


# Stored in the campaign save, so these are a format: rename one and every campaign
# forgets which naming it was using.
RANK_NAMES_COUNTRY = "country"
RANK_NAMES_GENERIC = "generic"
RANK_NAMES_SKILL = "skill"
RANK_NAMES_CUSTOM = "custom"


def custom_ladder(names: Sequence[str]) -> RankLadder:
    """Five names typed by the player. A box left empty keeps its generic rung."""
    picked = []
    for index, generic in enumerate(GENERIC_RANKS):
        typed = names[index].strip() if index < len(names) else ""
        picked.append(Rank(typed, typed) if typed else generic)
    return (picked[0], picked[1], picked[2], picked[3], picked[4])


def ranks_for(
    source: str,
    country: Optional[Country] = None,
    custom_names: Sequence[str] = (),
) -> RankLadder:
    """Return the ladder a squadron promotes through under this naming choice.

    Any unknown source, and any country with no ladder of its own, resolves to the
    generic one: a naming that cannot be worked out should make a label plainer, never
    break mission generation.
    """
    if source == RANK_NAMES_SKILL:
        return SKILL_NAME_RANKS
    if source == RANK_NAMES_CUSTOM:
        return custom_ladder(custom_names)
    if source == RANK_NAMES_COUNTRY and country is not None:
        return COUNTRY_RANKS.get(country.name, GENERIC_RANKS)
    return GENERIC_RANKS


def rank_for_skill(skill: Skill, ladder: RankLadder) -> Rank:
    """Return the rung of ``ladder`` a pilot flying at ``skill`` stands on.

    An unrecognised skill -- Random, Player and Client are skills to DCS but not steps
    of a career -- reads as the bottom rather than raising: a label is never worth a
    failed mission generation.
    """
    try:
        return ladder[SKILL_LADDER.index(skill)]
    except ValueError:
        return ladder[0]
