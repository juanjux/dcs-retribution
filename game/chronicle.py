"""The mission chronicle: what happened out there, written as prose.

The Mission Log plugin prints events as they happen and records them as flat
facts. This turns those facts into an account of the mission -- who did what to
whom, in order, with the moments that deserve emphasis given it and the rest
left plain.

The restraint is the point. A chronicle that shouts at every kill says nothing;
one that shouts only when an A-10 downs a fighter, or when the same pilot takes
two inside a minute, or when somebody flies into a hill with nobody shooting,
reads like somebody was actually watching.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence

if TYPE_CHECKING:
    from game.debriefing import Debriefing

#: DCS coalition id for blue, which in Retribution is always the player's side.
PLAYER_SIDE = 2

#: A gap this long means the next thing that happened is a new part of the
#: story, not the same one continuing. Taken from the events rather than fixed
#: clock times so a quiet mission does not get padded into four empty acts.
ACT_GAP_SECONDS = 240.0

#: Two kills closer together than this by one pilot is a run, not a coincidence.
STREAK_SECONDS = 120.0

#: Aircraft that have no business winning a dogfight. Matched as a prefix of the
#: type name, so "A-10C Thunderbolt II (Suite 7)" counts.
MUD_MOVERS = ("A-10", "AV-8B", "Su-25", "OV-10", "L-39", "C-101", "Yak-52")


@dataclass(frozen=True)
class LogEvent:
    """One thing that happened, as the Lua side recorded it."""

    t: float
    kind: str
    side: int
    actor_type: Optional[str] = None
    actor_pilot: Optional[str] = None
    target_type: Optional[str] = None
    target_pilot: Optional[str] = None
    weapon: Optional[str] = None
    count: int = 1
    scenery: bool = False
    place: Optional[str] = None
    source: Optional[str] = None

    @property
    def actor(self) -> str:
        """The subject of the sentence: the pilot if we know one, else the type."""
        if self.actor_pilot:
            return self.actor_pilot
        return self.actor_type or "somebody"

    @property
    def target(self) -> str:
        if self.target_pilot and self.target_type:
            return f"{self.target_pilot}'s {self.target_type}"
        if self.target_type:
            # No pilot known -- an AI wingman, or a mission where the roster was
            # never seeded. It still needs an article to sit in a sentence.
            return f"{_article(self.target_type)} {self.target_type}"
        return "something"

    @property
    def with_weapon(self) -> str:
        return f" with {self.weapon}" if self.weapon else ""

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> Optional[LogEvent]:
        """Builds an event, or None if the record is not one we understand.

        Records come from a Lua table serialised by a third-party encoder and
        may predate any field added since. Nothing here is worth raising over.
        """
        kind = raw.get("kind")
        if not isinstance(kind, str):
            return None
        try:
            t = float(raw.get("t", 0.0))
            side = int(raw.get("side", 0))
        except (TypeError, ValueError):
            return None

        def text(key: str) -> Optional[str]:
            value = raw.get(key)
            return value if isinstance(value, str) and value else None

        try:
            count = int(raw.get("count", 1))
        except (TypeError, ValueError):
            count = 1

        return cls(
            t=t,
            kind=kind,
            side=side,
            actor_type=text("actor_type"),
            actor_pilot=text("actor_pilot"),
            target_type=text("target_type"),
            target_pilot=text("target_pilot"),
            weapon=text("weapon"),
            count=max(1, count),
            scenery=bool(raw.get("scenery", False)),
            place=text("place"),
            source=text("source"),
        )


def _clock(seconds: float) -> str:
    """Mission time as h:mm, which is how a debrief talks about it."""
    return f"{int(seconds) // 3600:d}:{(int(seconds) % 3600) // 60:02d}"


def _pick(options: Sequence[str], seed: int) -> str:
    """Deterministic variety.

    Chosen by position rather than at random so that reopening the debrief
    gives the same chronicle -- a report that rewords itself every time you
    look at it is not a report.
    """
    return options[seed % len(options)]


#: Letters whose spoken name starts with a vowel, so "an F-15" but "a MiG-29".
_SPOKEN_VOWEL = set("AEFHILMNORSX")


def _article(name: Optional[str]) -> str:
    """ "a" or "an" for an aircraft designation.

    The vowel rule alone gets this wrong: "F-15" is spoken "eff fifteen" and
    takes "an", while "MiG-29" is spoken as a word and takes "a". The tell is
    whether the first letter stands alone -- "F-15" and "A-10" are initialisms,
    "MiG" and "Su" are not.
    """
    if not name:
        return "a"
    first = name[0].upper()
    initialism = len(name) > 1 and not name[1].isalpha()
    if initialism:
        return "an" if first in _SPOKEN_VOWEL else "a"
    return "an" if first in "AEIOU" else "a"


def _is_mud_mover(type_name: Optional[str]) -> bool:
    if not type_name:
        return False
    return any(type_name.startswith(prefix) for prefix in MUD_MOVERS)


def is_upset(event: LogEvent) -> bool:
    """An attack aircraft shooting down something that flies."""
    return event.kind == "airkill" and _is_mud_mover(event.actor_type)


def is_own_goal(event: LogEvent, events: Sequence[LogEvent]) -> bool:
    """A crash with nobody shooting: the aircraft simply lost the argument."""
    if event.kind != "crash":
        return False
    return not any(
        other.kind == "defending"
        and other.actor_pilot == event.actor_pilot
        and 0 <= event.t - other.t <= 60
        for other in events
    )


def streak_positions(events: Sequence[LogEvent]) -> Dict[int, int]:
    """Index of each air kill within its pilot's run, for kills that form one.

    Only runs of two or more inside the window are listed, so an ordinary
    single kill is never announced as "his first".
    """
    by_pilot: Dict[str, List[int]] = {}
    for index, event in enumerate(events):
        if event.kind == "airkill" and event.actor_pilot:
            by_pilot.setdefault(event.actor_pilot, []).append(index)

    positions: Dict[int, int] = {}
    for indices in by_pilot.values():
        run: List[int] = []
        for index in indices:
            if run and events[index].t - events[run[-1]].t > STREAK_SECONDS:
                run = []
            run.append(index)
            if len(run) > 1:
                for place, member in enumerate(run, start=1):
                    positions[member] = place
    return positions


def survived_defence(event: LogEvent, events: Sequence[LogEvent]) -> bool:
    """Somebody was shot at and is not among the losses that follow."""
    if event.kind != "defending" or not event.actor_pilot:
        return False
    return not any(
        other.kind in ("crash", "ejection")
        and other.actor_pilot == event.actor_pilot
        and other.t >= event.t
        for other in events
    )


def _capitalised(sentence: str) -> str:
    """Some phrasings lead with the target ("the factory WILDEBEEST took...").

    Fixing it here rather than in each template keeps the templates free to
    start with whatever reads best. Digits are untouched by upper(), so "3
    T-72B destroyed" survives.
    """
    return sentence[:1].upper() + sentence[1:] if sentence else sentence


def _ordinal(n: int) -> str:
    return {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}.get(
        n, f"{n}th"
    )


def _sentence(
    event: LogEvent, index: int, events: Sequence[LogEvent], streaks: Dict[int, int]
) -> Optional[str]:
    """One event as one sentence, or None for events not worth narrating."""
    if event.kind == "airkill":
        if is_upset(event):
            return _pick(
                [
                    f"{event.actor}, flying an attack jet, took {event.target} "
                    f"out of the sky{event.with_weapon}. Nobody will believe it.",
                    f"And then the improbable: {event.actor} downed "
                    f"{event.target}{event.with_weapon} — in "
                    f"{_article(event.actor_type)} {event.actor_type}.",
                ],
                index,
            )
        line = _pick(
            [
                f"{event.actor} downed {event.target}{event.with_weapon}.",
                f"{event.actor} put {event.weapon or 'a burst'} into "
                f"{event.target}, and that was that.",
                f"{event.target} fell to {event.actor}{event.with_weapon}.",
            ],
            index,
        )
        place = streaks.get(index)
        if place and place > 1:
            line += f" That is {event.actor}'s {_ordinal(place)} in short order."
        return line

    if event.kind == "groundkills":
        what = (
            f"the {event.target_type}"
            if event.scenery
            else (
                f"{event.count} {event.target_type}"
                if event.count > 1
                else f"the {event.target_type}"
            )
        )
        if event.scenery:
            return _pick(
                [
                    f"{event.actor} worked over {what}{event.with_weapon}.",
                    f"{what} took a serious beating from "
                    f"{event.actor}{event.with_weapon}.",
                ],
                index,
            )
        return _pick(
            [
                f"{event.actor} destroyed {what}{event.with_weapon}.",
                f"{what} stopped being a problem, courtesy of "
                f"{event.actor}{event.with_weapon}.",
            ],
            index,
        )

    if event.kind == "defending":
        line = _pick(
            [
                f"{event.weapon or 'A missile'} off the rail at {event.actor}, "
                f"launched by {event.target}.",
                f"{event.target} loosed {event.weapon or 'a missile'} at "
                f"{event.actor}.",
            ],
            index,
        )
        if survived_defence(event, events):
            line += " " + _pick(
                ["It went wide.", "He is still flying.", "No joy for the shooter."],
                index,
            )
        return line

    if event.kind == "ejection":
        return f"{event.actor} got out."

    if event.kind == "crash":
        if is_own_goal(event, events):
            return _pick(
                [
                    f"{event.actor} flew a perfectly good "
                    f"{event.actor_type} into the ground, unassisted.",
                    f"No one was shooting at {event.actor}. "
                    f"The {event.actor_type} went in anyway.",
                ],
                index,
            )
        return f"{event.actor} went down."

    if event.kind == "intercept":
        return (
            f"{event.actor} turned to intercept {event.target}"
            f"{', ' + event.source if event.source else ''}."
        )

    # takeoff, land and damage are texture, not story.
    return None


def _acts(events: Sequence[LogEvent]) -> List[List[LogEvent]]:
    """Splits the timeline where it goes quiet."""
    acts: List[List[LogEvent]] = []
    current: List[LogEvent] = []
    for event in events:
        if current and event.t - current[-1].t > ACT_GAP_SECONDS:
            acts.append(current)
            current = []
        current.append(event)
    if current:
        acts.append(current)
    return acts


def chronicle_from_events(
    raw_events: Iterable[Dict[str, Any]],
    *,
    side: int = PLAYER_SIDE,
    title: str = "Mission chronicle",
    subtitle: str = "",
) -> str:
    """The chronicle as markdown. Empty string when there is nothing to tell."""
    parsed = [LogEvent.from_raw(raw) for raw in raw_events]
    events = sorted(
        (event for event in parsed if event is not None and event.side == side),
        key=lambda event: event.t,
    )
    if not events:
        return ""

    streaks = streak_positions(events)
    lines: List[str] = [f"# {title}", ""]
    if subtitle:
        lines += [f"*{subtitle}*", ""]

    index = 0
    wrote_something = False
    for act in _acts(events):
        sentences: List[str] = []
        for event in act:
            sentence = _sentence(event, index, events, streaks)
            index += 1
            if sentence:
                sentences.append(_capitalised(sentence))
        if not sentences:
            continue
        lines.append(f"**{_clock(act[0].t)}** — " + " ".join(sentences))
        lines.append("")
        wrote_something = True

    if not wrote_something:
        return ""
    return "\n".join(lines).rstrip() + "\n"


def build_chronicle(debriefing: Debriefing) -> str:
    """The chronicle for a flown mission, or empty if the log recorded nothing."""
    events = debriefing.state_data.mission_log_events
    if not events:
        return ""
    game = debriefing.game
    when = getattr(game, "date", None)
    subtitle = f"Turn {game.turn}"
    if isinstance(when, datetime.date):
        subtitle += f", {when:%d %B %Y}"
    return chronicle_from_events(
        events,
        title=str(getattr(game, "campaign_name", "Mission chronicle")),
        subtitle=subtitle,
    )


def write_chronicle(debriefing: Debriefing, archived_miz: Path) -> Optional[Path]:
    """Writes the chronicle beside its archived mission, sharing the stem.

    Returns the path, or None when there was nothing to tell or the write
    failed. Never raises: the campaign has already been debriefed by the time
    this runs, and losing a keepsake must not cost the turn.
    """
    text = build_chronicle(debriefing)
    if not text:
        return None
    path = archived_miz.with_suffix(".md")
    try:
        path.write_text(text, encoding="utf-8")
    except OSError:
        logging.warning("Could not write chronicle %s", path, exc_info=True)
        return None
    logging.info("Wrote mission chronicle %s", path)
    return path
