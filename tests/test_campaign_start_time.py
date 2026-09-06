"""The campaign clock: a start date and a start time are not interchangeable.

A campaign whose ``recommended_start_date`` carries a time of day hands Game two
separate values. The turn slots are computed from the sun, so the daytime map is
chosen by the *date* -- asking for the map of a *time* raised AttributeError before
the campaign ever opened. Only TblisiGap ships with a time in its start date, so
nothing caught it.
"""

from __future__ import annotations

import datetime
from typing import Any

import pytest

from game.game import time_of_day_offset
from game.theater.daytimemap import DaytimeMap
from game.timeofday import TimeOfDay

# Dawn 06:00, day 08:00, dusk 18:00, night 22:00.
MAP = DaytimeMap(
    dawn=(datetime.time(6), datetime.time(8)),
    day=(datetime.time(8), datetime.time(18)),
    dusk=(datetime.time(18), datetime.time(22)),
    night=(datetime.time(22), datetime.time(6)),
)


class _Theater:
    """Records what the daytime map was asked for."""

    def __init__(self) -> None:
        self.asked_for: Any = None

    def daytime_map_for(self, date: datetime.date) -> DaytimeMap:
        self.asked_for = date
        return MAP


def test_the_map_is_chosen_by_the_date_and_read_at_the_time() -> None:
    """TblisiGap starts at 1980-09-21 06:40, which is dawn."""
    theater = _Theater()
    offset = time_of_day_offset(
        theater,  # type: ignore[arg-type]
        datetime.datetime(1980, 9, 21, 6, 40),
        datetime.time(6, 40),
    )
    assert theater.asked_for == datetime.date(1980, 9, 21)
    assert list(TimeOfDay)[offset] is TimeOfDay.Dawn


def test_a_campaign_with_no_start_time_begins_in_daylight() -> None:
    theater = _Theater()
    offset = time_of_day_offset(
        theater, datetime.datetime(1980, 9, 21), None  # type: ignore[arg-type]
    )
    assert theater.asked_for is None  # the map is never consulted
    assert list(TimeOfDay)[offset] is TimeOfDay.Day


def test_a_time_of_day_has_no_date_to_give() -> None:
    """The shape of the original bug, so it cannot come back by another route."""
    with pytest.raises(AttributeError):
        datetime.time(6, 40).date()  # type: ignore[attr-defined]
