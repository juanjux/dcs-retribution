"""A pilot's rank drawn as stars.

Rank is the one thing about a pilot that only goes one way, so five fixed slots read as
a bar you can scan down a list rather than a title you have to parse. The empty slots
stay faintly visible: a one-star pilot should not look like a row with a missing field.

The name is never dropped -- eleven national ladders call the same rung Captain,
Lieutenant, Flight Lieutenant, Starshiy Leytenant or Capitaine, and that is worth
reading. The stars sit in front of it.

Everything that shows a rank uses this, so the list and the pilot selector can never
drift apart.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QFont, QPainter

from game.squadrons.morale import RANK_LEVELS

FILLED = "★"
EMPTY = "☆"

#: The gold of a star he has earned, and the ghost of one he has not.
STAR_FILLED = "#E0C070"
STAR_EMPTY = "#3A4B5C"

#: On a selected row, where the background is lighter.
STAR_FILLED_SELECTED = "#F0D48A"
STAR_EMPTY_SELECTED = "#4F6B85"

#: On the roll of the fallen, where nothing should compete with the living.
STAR_FILLED_DIMMED = "#8A7A55"
STAR_EMPTY_DIMMED = "#2A3641"

#: A star is drawn at this size, with a hair of air between them.
STAR_SIZE = 11
STAR_TRACKING = 1


def star_font(size: int = STAR_SIZE) -> QFont:
    font = QFont()
    font.setPixelSize(size)
    return font


def stars_width(painter: QPainter, size: int = STAR_SIZE) -> float:
    """How much room the five slots take, whatever the rank."""
    metrics = painter.fontMetrics()
    return RANK_LEVELS * (metrics.horizontalAdvance(FILLED) + STAR_TRACKING)


def paint_rank_stars(
    painter: QPainter,
    x: float,
    baseline: float,
    level: int,
    filled: str = STAR_FILLED,
    empty: str = STAR_EMPTY,
    size: int = STAR_SIZE,
) -> float:
    """Draw the five slots from ``x`` and return the width used.

    Always five, whatever the rank: the columns only line up if every row spends the
    same width on them.
    """
    painter.save()
    painter.setFont(star_font(size))
    metrics = painter.fontMetrics()
    step = metrics.horizontalAdvance(FILLED) + STAR_TRACKING
    filled_pen = QColor(filled)
    empty_pen = QColor(empty)
    for slot in range(RANK_LEVELS):
        painter.setPen(filled_pen if slot < level else empty_pen)
        painter.drawText(
            QRectF(x + slot * step, baseline - size, step, size + 4),
            0,
            FILLED if slot < level else EMPTY,
        )
    painter.restore()
    return RANK_LEVELS * step


def rank_stars_text(level: Optional[int]) -> str:
    """The same five slots as plain text, for a combo box that cannot be painted.

    One colour rather than two, which is the price of putting them somewhere Qt draws
    the text itself.
    """
    if level is None:
        return ""
    level = max(0, min(RANK_LEVELS, level))
    return FILLED * level + EMPTY * (RANK_LEVELS - level)
