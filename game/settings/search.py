"""Finding a setting by typing part of what it is called.

There are two hundred-odd of them across six pages and twenty sections, and the
name a player remembers is rarely the one on the label -- they remember "napalm",
or "cadet", or that it was something about parking. So every token has to be able
to match anywhere: the label, the explanation under it, the page and section it
lives in, or the key it is stored under.

The matching is deliberately forgiving in one direction only. A token that is not a
substring anywhere still matches as a subsequence of the label ("frntline" finds
"Maximum frontline width"), but that is worth far less than a real hit, so a typo
never outranks the thing you actually typed.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any, Iterator, Optional

#: What a hit in each place is worth. A word the label starts with is what you meant;
#: a run of letters buried in the explanation probably is not.
SCORE_LABEL_WORD_START = 100
SCORE_LABEL = 60
#: A section whose name matches is offered as one row, not as every setting inside
#: it: "rank" used to answer with fifteen rows called Cadet, Good and High, which is
#: the section's name showing through each of its members.
SCORE_SECTION = 50
SCORE_DETAIL = 20
SCORE_KEY = 15
SCORE_SUBSEQUENCE = 8


def fold(text: str) -> str:
    """Lower case and without accents, so 'moral' finds 'Morale' either way."""
    stripped = unicodedata.normalize("NFD", text)
    return "".join(c for c in stripped if not unicodedata.combining(c)).lower()


#: How far a subsequence may spread before it stops being a typo and starts being a
#: coincidence. "frntline" inside "frontline" spans nine letters for eight typed and
#: is clearly meant; "napalm" scattered across "Enable per-squadron pilot limits" is
#: not, and without a limit almost every long label matches almost every word.
SUBSEQUENCE_SLACK = 3


def is_subsequence(needle: str, haystack: str) -> bool:
    """Every letter of needle, in order and close together. The typo net."""
    if len(needle) < 4:
        return False
    limit = len(needle) + SUBSEQUENCE_SLACK
    for start in range(len(haystack)):
        if haystack[start] != needle[0]:
            continue
        found = 1
        for position in range(start + 1, min(len(haystack), start + limit)):
            if haystack[position] == needle[found]:
                found += 1
                if found == len(needle):
                    return True
    return False


@dataclass(frozen=True)
class SettingHit:
    """One setting a query found, and where the player has to go to reach it."""

    key: str
    label: str
    page: str
    section: str
    subsection: Optional[str]
    score: int
    #: The hit is the section itself rather than a setting in it, so following it
    #: means opening that section and stopping there.
    is_section: bool = False
    #: Set when the hit is a plugin's option rather than a setting of the game's, in
    #: which case reaching it means opening that plugin's gear.
    plugin: Optional[str] = None

    @property
    def where(self) -> str:
        parts = [self.page, self.section]
        if self.subsection:
            parts.append(self.subsection)
        return " › ".join(parts)


def score_one(token: str, label: str, detail: str, key: str) -> int:
    """What this token is worth against one setting, or 0 if it is not there."""
    if token in label:
        starts = any(word.startswith(token) for word in label.split())
        return SCORE_LABEL_WORD_START if starts else SCORE_LABEL
    if token in detail:
        return SCORE_DETAIL
    # Only when it is plainly a key that is being typed. Otherwise an ordinary word
    # matches every setting whose key happens to contain it: "rank" found all ten
    # rank-name boxes through live_pilots_rank_good_short and the like, which is the
    # section's name showing through again.
    if "_" in token and token in key:
        return SCORE_KEY
    if is_subsequence(token, label):
        return SCORE_SUBSEQUENCE
    return 0


def search(query: str, settings: Any = None, limit: int = 40) -> list[SettingHit]:
    """Every setting that matches all of the words typed, best first.

    ``settings`` is only read to skip the options a campaign is not offering right
    now, so a search never sends anyone to a row that is not there.
    """
    from game.settings import Settings

    tokens = [fold(t) for t in query.split() if t.strip()]
    if not tokens:
        return []

    hits: list[SettingHit] = []
    for key, description in Settings.all_fields():
        if (
            settings is not None
            and description.visible_when is not None
            and not description.visible_when(settings)
        ):
            continue
        label = fold(description.text)
        detail = fold(description.detail or "")
        subsection = description.subsection
        folded_key = fold(key)

        total = 0
        for token in tokens:
            worth = score_one(token, label, detail, folded_key)
            if not worth:
                total = 0
                break
            total += worth
        if not total:
            continue
        # A short label matching is a better answer than a long one saying the same
        # thing further in.
        total = total * 100 - len(description.text)
        hits.append(
            SettingHit(
                key=key,
                label=description.text,
                page=description.page,
                section=description.section,
                subsection=subsection,
                score=total,
            )
        )

    hits.extend(_section_hits(tokens))
    hits.extend(_plugin_hits(tokens))
    hits.sort(key=lambda hit: (-hit.score, hit.label))
    return hits[:limit]


def _section_hits(tokens: list[str]) -> Iterator[SettingHit]:
    """One row per section whose name matches, instead of all of its contents."""
    from game.settings import Settings

    for page in Settings.pages():
        for section in Settings.sections(page):
            places = [(section, None)] + [
                (box, box) for box in Settings.subsections(page, section)
            ]
            for name, subsection in places:
                where = fold(f"{page} {section} {subsection or ''}")
                if not all(token in where for token in tokens):
                    continue
                yield SettingHit(
                    key="",
                    label=name,
                    page=page,
                    section=section,
                    subsection=subsection,
                    score=SCORE_SECTION * len(tokens) * 100 - len(name),
                    is_section=True,
                )


#: What the plugin page is called in the dialog's own list.
PLUGINS_PAGE = "Mission Plugins"


def _plugin_hits(tokens: list[str]) -> Iterator[SettingHit]:
    """The options behind the gears, which are options too.

    Splash Damage alone has sixty-five of them, and they are the ones hardest to
    find by clicking: nothing on the page says the word "napalm" until you have
    opened the right plugin.
    """
    from game.plugins import LuaPluginManager

    for plugin in LuaPluginManager.plugins():
        if not plugin.show_in_ui:
            continue
        for option in plugin.options:
            label = fold(option.name)
            key = fold(option.identifier)
            total = 0
            for token in tokens:
                worth = score_one(token, label, "", key)
                if not worth:
                    total = 0
                    break
                total += worth
            if not total:
                continue
            yield SettingHit(
                key=option.identifier,
                label=option.name,
                page=PLUGINS_PAGE,
                section=plugin.name,
                subsection=None,
                score=total * 100 - len(option.name),
                plugin=plugin.identifier,
            )
