"""Toolbar and column header around the Air Wing squadron list.

The list answers "which squadron flies the E-2C?" by eye now, but at forty rows
the honest answer to "do I have tanker coverage?" is a filter box, so the list
gained one, plus a sort order and a running count of what is on screen.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from game.squadrons import Squadron
from qt_ui.models import AirWingModel

TOOLBAR_HEIGHT = 54
FIELD_HEIGHT = 30
HEADER_HEIGHT = 26

#: Matches the delegate's columns so the labels sit over what they name.
COL_TYPE_X = 120
COL_BASE_X = 460
COL_CHIP_X = 730
RIGHT_MARGIN = 14

HEADER_FILL = QColor("#26343F")
HEADER_TEXT = QColor("#6B7A87")

SORT_ORDERS = [
    ("Aircraft type", "type"),
    ("Squadron", "squadron"),
    ("Base", "base"),
    ("Aircraft count", "aircraft"),
]


class SquadronFilterProxy(QSortFilterProxyModel):
    """Live filter over type, squadron or base, plus the sort order."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.needle = ""
        self.order = "type"
        self.setDynamicSortFilter(True)

    def set_needle(self, needle: str) -> None:
        self.needle = needle.strip().lower()
        self.invalidateFilter()

    def set_order(self, order: str) -> None:
        self.order = order
        self.invalidate()
        self.sort(0, Qt.SortOrder.AscendingOrder)

    def _squadron(self, index: QModelIndex) -> Squadron | None:
        squadron = index.data(AirWingModel.SquadronRole)
        return squadron if isinstance(squadron, Squadron) else None

    def filterAcceptsRow(self, row: int, parent: QModelIndex) -> bool:
        if not self.needle:
            return True
        source = self.sourceModel()
        squadron = self._squadron(source.index(row, 0, parent))
        if squadron is None:
            return True
        haystack = " ".join(
            [
                squadron.aircraft.display_name,
                squadron.name,
                squadron.nickname or "",
                squadron.location.name,
            ]
        ).lower()
        return self.needle in haystack

    def _key(self, squadron: Squadron) -> Any:
        if self.order == "squadron":
            return (squadron.name.lower(), squadron.aircraft.display_name.lower())
        if self.order == "base":
            return (
                squadron.location.name.lower(),
                squadron.aircraft.display_name.lower(),
            )
        if self.order == "aircraft":
            # Most aircraft first: the question behind this sort is what you have.
            return (-squadron.owned_aircraft, squadron.aircraft.display_name.lower())
        return (squadron.aircraft.display_name.lower(), squadron.name.lower())

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        first, second = self._squadron(left), self._squadron(right)
        if first is None or second is None:
            return False
        return self._key(first) < self._key(second)


class ColumnHeader(QWidget):
    """Four labels painted at the delegate's own column offsets."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(HEADER_HEIGHT)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), HEADER_FILL)
        font = QFont(self.font())
        font.setPixelSize(10)
        font.setWeight(QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        painter.setFont(font)
        painter.setPen(HEADER_TEXT)
        baseline = 17
        painter.drawText(COL_TYPE_X, baseline, "AIRCRAFT TYPE / SQUADRON")
        painter.drawText(COL_BASE_X, baseline, "BASE")
        painter.drawText(COL_CHIP_X, baseline, "ROLE")
        painter.drawText(
            self.rect().adjusted(0, 0, -RIGHT_MARGIN, 0),
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            "STRENGTH",
        )
        painter.end()


class SquadronPanel(QWidget):
    """The squadron list with its filter, sort order and totals."""

    def __init__(self, squadron_list: QWidget, proxy: SquadronFilterProxy) -> None:
        super().__init__()
        self.proxy = proxy

        self.filter_field = QLineEdit()
        self.filter_field.setPlaceholderText("Filter by type, squadron or base...")
        self.filter_field.setClearButtonEnabled(True)
        self.filter_field.setFixedSize(340, FIELD_HEIGHT)
        self.filter_field.textChanged.connect(self.on_filter_changed)

        self.sort_combo = QComboBox()
        self.sort_combo.setFixedHeight(FIELD_HEIGHT)
        for label, key in SORT_ORDERS:
            self.sort_combo.addItem(f"Sort: {label}", key)
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)

        self.totals = QLabel()
        self.totals.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 12, 12, 12)
        toolbar.setSpacing(12)
        toolbar.addWidget(self.filter_field)
        toolbar.addWidget(self.sort_combo)
        toolbar.addStretch()
        toolbar.addWidget(self.totals)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(toolbar)
        layout.addWidget(ColumnHeader())
        layout.addWidget(squadron_list)
        self.setLayout(layout)

        self.proxy.set_order("type")
        self.update_totals()

    def on_filter_changed(self, needle: str) -> None:
        self.proxy.set_needle(needle)
        self.update_totals()

    def on_sort_changed(self, _index: int) -> None:
        self.proxy.set_order(self.sort_combo.currentData())

    def update_totals(self) -> None:
        shown = self.proxy.rowCount()
        total = self.proxy.sourceModel().rowCount()
        aircraft = 0
        for row in range(shown):
            squadron = self.proxy.index(row, 0).data(AirWingModel.SquadronRole)
            if isinstance(squadron, Squadron):
                aircraft += squadron.owned_aircraft
        counted = f"{shown} of {total}" if shown != total else str(total)
        self.totals.setText(f"{counted} squadrons · {aircraft} aircraft")
