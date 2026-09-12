"""A buy list: rows you can read at a glance, and the figures pinned above them.

Buying was three group boxes in a grid -- a name with "2 (2 idle)" beside it, a price,
and a minus/plus pair -- and the numbers that decide whether an order is a good idea
were somewhere else entirely: parking in a paragraph at the top of the window, budget
in the footer. Ordering six aircraft meant scrolling up to see whether they fitted,
then down to the row, then up again to check the money.

So the row carries what the Air Wing list already carries -- the aircraft's own
silhouette, the type, what it flies, the squadron -- and the summary stays fixed above
the scroll, saying what the order leaves you with and turning amber the moment it
cannot be paid for.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from qt_ui.widgets.cards import CAPTION, CARD_BORDER, make_transparent
from qt_ui.widgets.controls import mono

if TYPE_CHECKING:
    from qt_ui.windows.basemenu.UnitTransactionFrame import UnitTransactionFrame

#: The colours the rest of the app already uses for these four meanings.
BRIGHT = "#F2F7FA"
QUIET = "#7C8B99"
AMBER = "#E0A86B"
GREEN = "#86C39A"
ROW_BG_ORDERED = "#182430"

#: Column widths, so every row lines up under the header without a table.
ICON_WIDTH = 91
ICON_HEIGHT = 24
PRESENT_WIDTH = 96
PRICE_WIDTH = 70
ROW_HEIGHT = 56
SUMMARY_HEIGHT = 40


@dataclass(frozen=True)
class Figure:
    """A number and what it means, for the summary bar."""

    caption: str
    value: str
    note: str = ""
    warn: bool = False


def _text(text: str, size: float, colour: str, bold: bool = False) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(
        f"font-size: {size}px; color: {colour}; background: transparent; border: none;"
        f" font-weight: {'600' if bold else 'normal'};"
    )
    return label


def _mono(text: str, size: int, colour: str) -> QLabel:
    label = QLabel(text)
    label.setFont(mono(size))
    label.setStyleSheet(
        f"color: {colour}; background: transparent; border: none; font-weight: 600;"
    )
    return label


def chip(text: str, fill: str, ink: str) -> QLabel:
    """A task chip, in the Air Wing list's colours."""
    label = QLabel(text.upper())
    label.setStyleSheet(
        f"background: {fill}; color: {ink}; border: none; border-radius: 4px;"
        " padding: 1px 8px; font-size: 10px; font-weight: bold; letter-spacing: 0.8px;"
    )
    label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return label


class OrderSummary(QWidget):
    """What this base's order leaves you with, pinned above the list it applies to.

    It is the arithmetic the player does in his head today by scrolling back up, and
    the one place an order that cannot be paid for can say so before it is placed.
    """

    def __init__(
        self,
        title: str,
        figures: Callable[[], list[Figure]],
        clear: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self._read_figures = figures
        self._clear = clear

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("orderSummary")
        self.setStyleSheet(
            "#orderSummary { background: #1B2732;"
            f" border-bottom: 1px solid {CARD_BORDER}; }}"
        )
        self.setFixedHeight(SUMMARY_HEIGHT)

        self._row = QHBoxLayout()
        self._row.setContentsMargins(14, 0, 14, 0)
        self._row.setSpacing(18)
        self.setLayout(self._row)

        self._title = _text(title.upper(), 10.5, CAPTION, bold=True)
        self._title.setStyleSheet(self._title.styleSheet() + " letter-spacing: 1px;")
        self._title.setParent(self)
        self.refresh()

    def refresh(self) -> None:
        """Rebuilt rather than updated: the cells themselves change with the order."""
        while self._row.count():
            taken = self._row.takeAt(0)
            widget = taken.widget()
            if widget is not None and widget is not self._title:
                widget.deleteLater()

        self._row.addWidget(self._title)
        for figure in self._read_figures():
            self._row.addWidget(self._figure(figure))
        self._row.addStretch()

        if self._clear is not None:
            link = _text("Clear order", 11, "#8FC3F0")
            link.setCursor(Qt.CursorShape.PointingHandCursor)
            link.mousePressEvent = lambda _event: self._clear()  # type: ignore[assignment,misc,union-attr]
            self._row.addWidget(link)

    def _figure(self, figure: Figure) -> QWidget:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        row.addWidget(_text(figure.caption, 11, QUIET))
        row.addWidget(_mono(figure.value, 12, AMBER if figure.warn else BRIGHT))
        if figure.note:
            row.addWidget(_text(figure.note, 11, AMBER if figure.warn else QUIET))

        holder = QWidget()
        make_transparent(holder)
        holder.setLayout(row)
        return holder


class PurchaseRow(QWidget):
    """One thing you can buy: what it is, what you have, what it costs, and the order.

    Everything on it comes from the frame that owns it, so this class never learns what
    a squadron is.
    """

    def __init__(self, item: object, frame: UnitTransactionFrame) -> None:
        super().__init__()
        self.item = item
        self.frame = frame

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName(f"buyRow{id(self)}")
        self.setFixedHeight(ROW_HEIGHT)

        row = QHBoxLayout()
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(10)
        row.addWidget(self._icon())
        row.addLayout(self._identity(), 1)
        row.addWidget(self._present())
        row.addWidget(self._price())
        row.addWidget(frame.order_control(item))
        self.setLayout(row)
        self.refresh()

    # -- the pieces ----------------------------------------------------------

    def _icon(self) -> QWidget:
        label = QLabel()
        label.setFixedSize(ICON_WIDTH, ICON_HEIGHT)
        pixmap: Optional[QPixmap] = self.frame.row_icon(self.item)
        if pixmap is not None:
            label.setPixmap(
                pixmap.scaled(
                    ICON_WIDTH,
                    ICON_HEIGHT,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        label.setStyleSheet("background: transparent; border: none;")
        return label

    def _identity(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)

        name, variant = self.frame.row_title(self.item)
        title = QHBoxLayout()
        title.setContentsMargins(0, 0, 0, 0)
        title.setSpacing(8)
        heading = _text(name, 14, BRIGHT, bold=True)
        if self.frame.supports_item_dialog():
            heading.setCursor(Qt.CursorShape.PointingHandCursor)
            heading.mousePressEvent = (  # type: ignore[assignment,misc,union-attr]
                lambda _event: self.frame.on_item_clicked(self.item)
            )
        title.addWidget(heading)
        if variant:
            title.addWidget(_text(variant, 12, QUIET))
        for text, fill, ink in self.frame.row_chips(self.item):
            title.addWidget(chip(text, fill, ink))
        title.addStretch()
        column.addLayout(title)

        self._subtitle = _text("", 11.5, QUIET)
        column.addWidget(self._subtitle)
        return column

    def _present(self) -> QWidget:
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)

        first = QHBoxLayout()
        first.setContentsMargins(0, 0, 0, 0)
        first.setSpacing(4)
        self._count = _mono("", 14, BRIGHT)
        self._of = _text("", 11, QUIET)
        self._pending = _text("", 11, AMBER)
        first.addWidget(self._count)
        first.addWidget(self._of)
        first.addWidget(self._pending)
        first.addStretch()
        column.addLayout(first)

        self._idle = _text("", 11, GREEN)
        column.addWidget(self._idle)

        holder = QWidget()
        make_transparent(holder)
        holder.setFixedWidth(PRESENT_WIDTH)
        holder.setLayout(column)
        return holder

    def _price(self) -> QWidget:
        self._price_label = _mono("", 13, BRIGHT)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._price_label)
        layout.addStretch()

        holder = QWidget()
        make_transparent(holder)
        holder.setFixedWidth(PRICE_WIDTH)
        holder.setLayout(layout)
        return holder

    # -- what changes when an order is placed --------------------------------

    def refresh(self) -> None:
        counts = self.frame.row_counts(self.item)
        self._count.setText(str(counts.present))
        self._of.setText(f"/ {counts.capacity} max" if counts.capacity else "")
        if counts.pending > 0:
            self._pending.setText(f"+{counts.pending}")
        elif counts.pending < 0:
            self._pending.setText(str(counts.pending))
        else:
            self._pending.setText("")
        self._idle.setText("" if counts.idle is None else f"{counts.idle} idle")
        self._price_label.setText(f"${self.frame.price_of(self.item)}M")

        subtitle = self.frame.row_subtitle(self.item)
        warning = self.frame.row_warning(self.item)
        if warning:
            # Amber, and on the row rather than in a tooltip: an order that will be
            # refused should say so before it is placed, not after it fails.
            self._subtitle.setText(
                f"{subtitle} · ▲ {warning}" if subtitle else f"▲ {warning}"
            )
            colour = AMBER
        else:
            self._subtitle.setText(subtitle)
            colour = QUIET
        self._subtitle.setStyleSheet(
            f"font-size: 11.5px; color: {colour}; background: transparent;"
            " border: none;"
        )

        # An ordered row is tinted and given an amber bar, so what is on order can be
        # found in a long list without reading every count.
        background = ROW_BG_ORDERED if counts.pending else "transparent"
        bar = AMBER if counts.pending else "transparent"
        self.setStyleSheet(
            f"#{self.objectName()} {{ background: {background};"
            f" border: none; border-bottom: 1px solid {CARD_BORDER};"
            f" border-left: 3px solid {bar}; }}"
        )
