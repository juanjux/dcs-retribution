"""Turn times taken from the sun rather than from a fixed table.

The `daytime` table in each theater's info.yaml gives one window per slot for the
whole year, which cannot be right everywhere at once: Kola's `dawn: [3, 9]` is a
reasonable spread in June and pitch dark for all six hours in December, and its
`day: [9, 18]` puts a "day" mission well after sunset in midwinter. Deriving the
four slots from the theater's latitude and the campaign date keeps each one
meaning what its name says, and leaves the tables as an opt-in override.
"""

from __future__ import annotations

import datetime
import logging

from dcs.mapping import LatLng
from suntime import Sun, SunTimeException  # type: ignore

from .daytimemap import DaytimeMap

# Every slot is one anchor hour with an hour of slack either side, so turns still
# vary without wandering into a different part of the day.
JITTER = datetime.timedelta(hours=1)

# Civil dawn is too dark to fly into, so the dawn slot sits an hour after the sun
# is properly up. Dusk starts while there is still light and goes dark during the
# mission. Night waits for the afterglow to clear.
DAWN_AFTER_SUNRISE = datetime.timedelta(hours=1)
DUSK_BEFORE_SUNSET = datetime.timedelta(hours=1)
NIGHT_AFTER_SUNSET = datetime.timedelta(hours=2)

# Used where the sun never crosses the horizon. Everything hangs off solar noon,
# which is the brightest moment of a polar night and the highest sun of a polar
# day, and night hangs off solar midnight. A dark "day" slot north of the arctic
# circle in December is the correct answer, not a bug to work around.
POLAR_DAWN_BEFORE_NOON = datetime.timedelta(hours=5)
POLAR_DUSK_AFTER_NOON = datetime.timedelta(hours=5)
POLAR_NIGHT_AFTER_NOON = datetime.timedelta(hours=12)


def _hour_range(anchor: datetime.datetime) -> tuple[datetime.time, datetime.time]:
    """The whole-hour window around an anchor.

    DaytimeMap only accepts whole hours, and mission generation picks a random
    hour inside the window, so an anchor of 07:40 becomes 07:00-09:00.
    """
    hour = (anchor + datetime.timedelta(minutes=30)).hour
    begin = (hour - int(JITTER.total_seconds() // 3600)) % 24
    end = (hour + int(JITTER.total_seconds() // 3600)) % 24
    return datetime.time(hour=begin), datetime.time(hour=end)


def solar_noon(
    longitude: float, tz: datetime.timezone, date: datetime.date
) -> datetime.datetime:
    """Local solar noon, near enough.

    The equation of time moves this by up to a quarter of an hour over the year,
    which does not matter for picking the hour a midday mission starts in.
    """
    noon_utc = datetime.datetime.combine(
        date, datetime.time(hour=12), tzinfo=datetime.timezone.utc
    ) - datetime.timedelta(hours=longitude / 15)
    return noon_utc.astimezone(tz)


def _sun_times(
    latitude: float, longitude: float, tz: datetime.timezone, date: datetime.date
) -> tuple[datetime.datetime, datetime.datetime] | None:
    """Local sunrise and sunset, or None where the sun does not cross the horizon.

    suntime answers in UTC for a UTC day. The local sunrise of a far-eastern
    theater falls on the previous UTC day and the local sunset of a far-western
    one on the next, so each event gets its own UTC date derived from a
    representative local hour.
    """
    sun = Sun(latitude, longitude)
    sunrise_local = datetime.datetime(date.year, date.month, date.day, 6, tzinfo=tz)
    sunset_local = datetime.datetime(date.year, date.month, date.day, 18, tzinfo=tz)
    try:
        sunrise = sun.get_sunrise_time(
            datetime.datetime.combine(
                sunrise_local.astimezone(datetime.timezone.utc).date(),
                datetime.time(),
            )
        )
        sunset = sun.get_sunset_time(
            datetime.datetime.combine(
                sunset_local.astimezone(datetime.timezone.utc).date(), datetime.time()
            )
        )
    except SunTimeException:
        return None
    return sunrise.astimezone(tz), sunset.astimezone(tz)


def solar_daytime_map(
    position: LatLng, tz: datetime.timezone, date: datetime.date
) -> DaytimeMap:
    """The four turn slots for this place on this date."""
    times = _sun_times(position.lat, position.lng, tz, date)
    if times is None:
        noon = solar_noon(position.lng, tz, date)
        logging.info(
            "The sun does not rise or set at %.1f on %s; anchoring turn times to "
            "solar noon at %s",
            position.lat,
            date,
            noon.time(),
        )
        return DaytimeMap(
            dawn=_hour_range(noon - POLAR_DAWN_BEFORE_NOON),
            day=_hour_range(noon),
            dusk=_hour_range(noon + POLAR_DUSK_AFTER_NOON),
            night=_hour_range(noon + POLAR_NIGHT_AFTER_NOON),
        )

    sunrise, sunset = times
    # Solar noon comes from the longitude rather than the midpoint of sunrise and
    # sunset: those two are computed on their own UTC days, so their midpoint is
    # half a day out whenever they fall on different ones.
    return DaytimeMap(
        dawn=_hour_range(sunrise + DAWN_AFTER_SUNRISE),
        day=_hour_range(solar_noon(position.lng, tz, date)),
        dusk=_hour_range(sunset - DUSK_BEFORE_SUNSET),
        night=_hour_range(sunset + NIGHT_AFTER_SUNSET),
    )
