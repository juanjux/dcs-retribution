"""Row painting for the ATO sidebar's packages and flights.

Both lists used to be four blocks of the same 10 pt text in a two-by-two grid — the
package's name and TOT on the left, "Player Slots: 2" and "Missing pilots: 1" on the
right — which reads as prose rather than a list you scan.

They are rows now, in the vocabulary the Air Wing list already taught: the task chip
first, the noun in the only large bold text, and the numbers in mono where they line up
column-wise. What needs a decision — a package with no flights, a flight with nobody in
it — is the one thing painted in amber.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from game.ato.flight import Flight
from game.ato.package import Package
from qt_ui.models import AtoModel, PackageModel
from qt_ui.widgets.squadrondelegate import (
    ACCENT,
    AMBER,
    CHIP_ON_SELECTED,
    HOVER_BAR,
    HOVER_FILL,
    SELECTED_FILL,
    SEPARATOR,
    TEXT_LABEL,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    chip_colours,
)

ROW_HEIGHT = 56
SEPARATOR_Y = 55

CHIP_X = 14
CHIP_Y = 9
CHIP_HEIGHT = 18
CHIP_RADIUS = 4
CHIP_PADDING = 8

#: Baselines from the top of the row.
LINE_1 = 24
LINE_2 = 44
MARGIN = 14

WARNING = "▲"


def _font(
    pixels: float, weight: QFont.Weight = QFont.Weight.Normal, mono: bool = False
):
    font = QFont("Consolas") if mono else QFont()
    font.setPixelSize(int(pixels))
    font.setWeight(weight)
    return font


class AtoRowDelegate(QStyledItemDelegate):
    """What the two rows share: the background, the chip and the eliding."""

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(0, ROW_HEIGHT)

    @staticmethod
    def _paint_background(
        painter: QPainter, width: int, selected: bool, hovered: bool
    ) -> None:
        if selected:
            painter.fillRect(0, 0, width, ROW_HEIGHT, SELECTED_FILL)
            painter.fillRect(0, 0, 3, ROW_HEIGHT, ACCENT)
        elif hovered:
            painter.fillRect(0, 0, width, ROW_HEIGHT, HOVER_FILL)
            painter.fillRect(0, 0, 3, ROW_HEIGHT, HOVER_BAR)
        painter.fillRect(0, SEPARATOR_Y, width, 1, SEPARATOR)

    @staticmethod
    def _paint_chip(
        painter: QPainter, x: int, task, selected: bool, label: Optional[str] = None
    ) -> int:
        """The task, in the same colour the Air Wing list gives it.

        Returns the x the chip ends at, so the caller can lay out after it.
        """
        text = label if label is not None else str(task)
        fill, ink = chip_colours(task)
        painter.setFont(_font(10, QFont.Weight.Bold))
        width = painter.fontMetrics().horizontalAdvance(text) + 2 * CHIP_PADDING
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(CHIP_ON_SELECTED if selected else fill)
        painter.drawRoundedRect(x, CHIP_Y, width, CHIP_HEIGHT, CHIP_RADIUS, CHIP_RADIUS)
        painter.setPen(ink)
        painter.drawText(
            QRect(x, CHIP_Y, width, CHIP_HEIGHT),
            Qt.AlignmentFlag.AlignCenter,
            text,
        )
        return x + width

    @staticmethod
    def _elided(painter: QPainter, text: str, room: int) -> str:
        return painter.fontMetrics().elidedText(
            text, Qt.TextElideMode.ElideRight, max(20, room)
        )

    def _paint_warning(self, painter: QPainter, width: int, note: str) -> int:
        """The one thing in the row that is amber, right-aligned on the first line."""
        painter.setFont(_font(11, QFont.Weight.DemiBold))
        text = f"{WARNING} {note}"
        room = painter.fontMetrics().horizontalAdvance(text)
        painter.setPen(AMBER)
        painter.drawText(width - MARGIN - room, LINE_1, text)
        return room


class PackageRowDelegate(AtoRowDelegate):
    """Task, target, then when it is over the target and how many flights."""

    @staticmethod
    def package(index: QModelIndex) -> Package:
        return index.data(AtoModel.PackageRole)

    @staticmethod
    def note_for(package: Package) -> Optional[str]:
        """Anything you would rather not find out at take-off."""
        if not package.flights:
            return "no flights"
        unassigned = sum(1 for f in package.flights if not f.count)
        if unassigned:
            return f"{unassigned} flight{'' if unassigned == 1 else 's'} unassigned"
        missing = sum(f.missing_pilots for f in package.flights)
        if missing:
            return f"{missing} missing pilot{'' if missing == 1 else 's'}"
        return None

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        package = self.package(index)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        with _painting(painter, option):
            width = option.rect.width()
            self._paint_background(painter, width, selected, hovered)

            note = self.note_for(package)
            taken = self._paint_warning(painter, width, note) + 10 if note else 0

            x = CHIP_X
            task = package.primary_task
            if task is not None:
                x = (
                    self._paint_chip(
                        painter, x, task, selected, package.package_description
                    )
                    + CHIP_PADDING
                )

            name = package.target.name
            if package.custom_name:
                name = f"{name} ({package.custom_name})"
            painter.setFont(_font(14, QFont.Weight.DemiBold))
            painter.setPen(TEXT_PRIMARY)
            painter.drawText(
                x, LINE_1, self._elided(painter, name, width - x - MARGIN - taken)
            )

            painter.setFont(_font(11, QFont.Weight.DemiBold))
            painter.setPen(TEXT_LABEL)
            painter.drawText(CHIP_X, LINE_2, "TOT")
            after_label = CHIP_X + painter.fontMetrics().horizontalAdvance("TOT") + 7

            painter.setFont(_font(12, mono=True))
            painter.setPen(TEXT_SECONDARY)
            time = f"{package.time_over_target:%H:%M:%S}"
            painter.drawText(after_label, LINE_2, time)
            after_time = (
                after_label + painter.fontMetrics().horizontalAdvance(time) + 12
            )

            painter.setFont(_font(11.5))
            painter.setPen(TEXT_TERTIARY)
            count = len(package.flights)
            painter.drawText(
                after_time, LINE_2, f"· {count} flight{'' if count == 1 else 's'}"
            )

            clients = sum(f.client_count for f in package.flights)
            if clients:
                painter.setFont(_font(11.5))
                _right_text(
                    painter, width, LINE_2, f"{clients} player slots", TEXT_LABEL
                )


class FlightRowDelegate(AtoRowDelegate):
    """Aircraft and how many, then who flies them and from where."""

    @staticmethod
    def _paint_player_chip(
        painter: QPainter, x: int, text: str, selected: bool
    ) -> None:
        width = painter.fontMetrics().horizontalAdvance(text) + 2 * CHIP_PADDING
        rect = QRect(x, LINE_2 - 11, width, 15)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(PLAYER_CHIP_BG_SELECTED if selected else PLAYER_CHIP_BG)
        painter.drawRoundedRect(rect, 3, 3)
        painter.setPen(PLAYER_CHIP_TEXT)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    @staticmethod
    def flight(index: QModelIndex) -> Flight:
        return index.data(PackageModel.FlightRole)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        flight = self.flight(index)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        with _painting(painter, option):
            width = option.rect.width()
            self._paint_background(painter, width, selected, hovered)

            # The chip sits on the right here: the aircraft is what you scan for in a
            # package whose task you already know from the row above.
            painter.setFont(_font(10, QFont.Weight.Bold))
            chip_width = (
                painter.fontMetrics().horizontalAdvance(str(flight.flight_type))
                + 2 * CHIP_PADDING
            )
            self._paint_chip(
                painter, width - MARGIN - chip_width, flight.flight_type, selected
            )

            painter.setFont(_font(14, QFont.Weight.DemiBold))
            painter.setPen(TEXT_PRIMARY)
            name = flight.unit_type.display_name
            room = width - CHIP_X - MARGIN - chip_width - 50
            painter.drawText(CHIP_X, LINE_1, self._elided(painter, name, room))
            after = CHIP_X + painter.fontMetrics().horizontalAdvance(
                self._elided(painter, name, room)
            )

            painter.setFont(_font(12, QFont.Weight.DemiBold, mono=True))
            painter.setPen(TEXT_LABEL)
            painter.drawText(after + 7, LINE_1, f"×{flight.count}")

            painter.setFont(_font(11.5))
            painter.setPen(TEXT_TERTIARY)
            where = f"{flight.squadron.name} · {flight.departure.name}"
            painter.drawText(
                CHIP_X, LINE_2, self._elided(painter, where, width - CHIP_X - 110)
            )

            # The package row says the package has player slots; this says which
            # flight they are in, which is the question you ask next.
            clients = flight.client_count
            if clients:
                seats = "seat" if clients == 1 else "seats"
                after_where = CHIP_X + painter.fontMetrics().horizontalAdvance(
                    self._elided(painter, where, width - CHIP_X - 110)
                )
                painter.setFont(_font(10, QFont.Weight.Bold))
                self._paint_player_chip(
                    painter, after_where + 8, f"{clients} player {seats}", selected
                )

            try:
                painter.setFont(_font(11.5, mono=True))
                painter.setPen(TEXT_LABEL)
                takeoff = f"dep {flight.flight_plan.takeoff_time():%H:%M}"
                room = painter.fontMetrics().horizontalAdvance(takeoff)
                painter.drawText(width - MARGIN - room, LINE_2, takeoff)
            except Exception:
                # A flight plan that cannot answer yet is not worth a broken row.
                pass


PLAYER_CHIP_BG = QColor("#2B4A66")
PLAYER_CHIP_BG_SELECTED = QColor("#3A5D7D")
PLAYER_CHIP_TEXT = QColor("#BEDCF6")


def _right_text(
    painter: QPainter, width: int, baseline: int, text: str, colour: QColor
) -> None:
    room = painter.fontMetrics().horizontalAdvance(text)
    painter.setPen(colour)
    painter.drawText(width - MARGIN - room, baseline, text)


class _painting:
    """save()/restore() around a row, with the origin moved to its top-left."""

    def __init__(self, painter: QPainter, option: QStyleOptionViewItem) -> None:
        self.painter = painter
        self.option = option

    def __enter__(self) -> QPainter:
        self.painter.save()
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.painter.setClipRect(self.option.rect)
        self.painter.translate(self.option.rect.topLeft())
        return self.painter

    def __exit__(self, *_: object) -> None:
        self.painter.restore()
