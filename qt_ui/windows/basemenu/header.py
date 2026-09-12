"""What the base menu says before you do anything: what is here, and does it work.

The window used to open with a 300 px photograph, then the base name in bold beside
four radio editors, then a paragraph of rich text holding the aircraft, the ground
units and the runway state, then a repair button. Everything weighed the same and
the three facts a player checks before fragging a strike -- is the runway up, is
there ammo, how much parking is left -- were the tail of the paragraph.

Here the name is the only large text, the kind and the owner are stated rather than
inferred from which tabs turned up, and the paragraph becomes figures.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from game.theater import ControlPoint, Fob, NavalControlPoint, ParkingType
from qt_ui.widgets.cards import CAPTION, card, make_transparent
from qt_ui.widgets.controls import KEY, VALUE, mono

#: The status of a thing that works, does not, or is being seen to.
GOOD = "#86C39A"
BAD = "#D9645E"
PENDING = "#E0A86B"
QUIET = "#8FA3BD"

#: Blue and red as the rest of the app paints them.
OWNER_BLUE = "#8FC3F0"
OWNER_RED = "#D9645E"

BANNER_HEIGHT = 132


def chip(text: str, colour: str, filled: bool = False) -> QLabel:
    """A word with a box around it: a state, not a control."""
    label = QLabel(text)
    if filled:
        style = (
            f"background: {colour}; color: #0F1922; font-weight: bold;"
            " border: none; border-radius: 3px; padding: 2px 8px; font-size: 11px;"
            " letter-spacing: 1px;"
        )
    else:
        style = (
            f"background: transparent; color: {colour}; border: 1px solid {colour};"
            " border-radius: 3px; padding: 2px 8px; font-size: 11px;"
        )
    label.setStyleSheet(style)
    return label


def figure(value: str, label: str, note: str = "", warn: bool = False) -> QWidget:
    """One cell of the figures strip: a number to read, and the breakdown under it."""
    column = QVBoxLayout()
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(2)

    name = QLabel(label.upper())
    name.setStyleSheet(
        f"font-size: 11px; font-weight: bold; letter-spacing: 1px; color: {CAPTION};"
        " background: transparent; border: none;"
    )
    column.addWidget(name)

    number = QLabel(value)
    number.setFont(mono(20))
    number.setStyleSheet(
        f"color: {PENDING if warn else VALUE}; background: transparent; border: none;"
    )
    column.addWidget(number)

    if note:
        detail = QLabel(note)
        detail.setStyleSheet(
            f"font-size: 11px; color: {QUIET}; background: transparent; border: none;"
        )
        column.addWidget(detail)

    holder = QWidget()
    make_transparent(holder)
    holder.setLayout(column)
    return holder


def kind_of(cp: ControlPoint) -> str:
    """What this base is, in the words the header states rather than implies."""
    if cp.is_carrier:
        return "CARRIER"
    if cp.is_lha:
        return "LHA"
    if isinstance(cp, Fob):
        return "HELIPORT" if cp.has_helipads and not cp.has_ground_spawns else "FOB"
    if isinstance(cp, NavalControlPoint):
        return "SHIP"
    return "AIRBASE"


class BaseHeader(QWidget):
    """The banner, the name, what it is, who holds it, and whether it works."""

    def __init__(self, cp: ControlPoint, game_model) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        self.cp = cp
        self.game_model = game_model

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._banner())
        layout.addWidget(self._identity())
        self.setLayout(layout)

    # -- the pieces ----------------------------------------------------------

    def _banner(self, image: Optional[str] = None) -> QWidget:
        """The photograph, cropped to a strip.

        It only ever said "this is an airbase" or "this is a carrier", which the chip
        beside the name now says in words -- but it says it faster, so it stays, at a
        height that does not cost the fold every time the window opens.
        """
        banner = QLabel()
        banner.setFixedHeight(BANNER_HEIGHT)
        banner.setScaledContents(False)
        if image is not None:
            pixmap = QPixmap(image)
            if not pixmap.isNull():
                banner.setPixmap(pixmap)
        banner.setStyleSheet("background: #0F1922; border: none;")
        return banner

    def _identity(self) -> QWidget:
        row = QHBoxLayout()
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(16)
        row.addLayout(self._name_and_state(), 1)
        comms = self._comms()
        if comms is not None:
            row.addWidget(comms)

        holder = QWidget()
        make_transparent(holder)
        holder.setLayout(row)
        return holder

    def _name_and_state(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(10)

        name = QLabel(self.cp.name)
        name.setStyleSheet(
            "font-size: 26px; font-weight: bold; color: #E8F0FB;"
            " background: transparent; border: none;"
        )
        title_row.addWidget(name)

        blue = self.cp.captured.is_blue
        owner = "BLUE" if blue else "RED"
        title_row.addWidget(
            chip(
                f"{kind_of(self.cp)} · {owner}",
                OWNER_BLUE if blue else OWNER_RED,
                filled=True,
            )
        )
        title_row.addStretch()
        column.addLayout(title_row)

        pills = QHBoxLayout()
        pills.setContentsMargins(0, 0, 0, 0)
        pills.setSpacing(8)
        for pill in self.status_pills():
            pills.addWidget(pill)
        pills.addStretch()
        column.addLayout(pills)
        return column

    def status_pills(self) -> list[QLabel]:
        """Runway, ammunition and industry: the three things checked before a strike."""
        pills: list[QLabel] = []
        status = self.cp.runway_status
        if status is not None:
            if status.damaged and status.repair_turns_remaining is not None:
                pills.append(
                    chip(
                        f"Runway damaged · repairs in {status.repair_turns_remaining}",
                        PENDING,
                    )
                )
            elif status.damaged:
                pills.append(chip("Runway damaged", BAD))
            else:
                pills.append(chip("Runway operational", GOOD))

        depots = self._ammo_depots()
        if depots is not None:
            alive, total = depots
            pills.append(
                chip(
                    f"Ammo depots {alive}/{total}",
                    GOOD if alive == total else PENDING,
                )
            )

        if self._has_factory():
            pills.append(chip("Factory producing", GOOD))
        return pills

    def _ammo_depots(self) -> Optional[tuple[int, int]]:
        depots = [go for go in self.cp.connected_objectives if go.category == "ammo"]
        if not depots:
            return None
        return sum(1 for go in depots if not go.is_dead), len(depots)

    def _has_factory(self) -> bool:
        return any(
            go.category == "factory" and not go.is_dead
            for go in self.cp.connected_objectives
        )

    def _comms(self) -> Optional[QWidget]:
        """Radio, TACAN, ICLS and Link 4, one row each, and only the ones it has.

        Built by whoever owns those widgets and handed here, so this module does not
        learn what a TACAN channel is.
        """
        rows = getattr(self, "comms_rows", None)
        if not rows:
            return None
        grid = QGridLayout()
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setSpacing(8)
        for index, (label, widget) in enumerate(rows):
            key = QLabel(label)
            key.setStyleSheet(
                f"font-size: 12px; color: {KEY}; background: transparent;"
                " border: none;"
            )
            grid.addWidget(key, index, 0)
            grid.addWidget(widget, index, 1)
        holder = card()
        holder.setLayout(grid)
        return holder


class FiguresStrip(QWidget):
    """Aircraft, ground units and money: the paragraph as three numbers.

    Budget belongs here rather than in the footer. It is a figure you read, not a
    button, and it sits beside the two numbers it constrains.
    """

    def __init__(self, cp: ControlPoint, game_model) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        self.cp = cp
        self.game_model = game_model

        row = QHBoxLayout()
        row.setContentsMargins(16, 10, 16, 10)
        row.setSpacing(28)
        for cell in self.cells():
            row.addWidget(cell)
        row.addStretch()

        holder = card()
        holder.setLayout(row)
        outer = QVBoxLayout()
        outer.setContentsMargins(16, 0, 16, 12)
        outer.addWidget(holder)
        self.setLayout(outer)

    def cells(self) -> list[QWidget]:
        if self.cp.captured.is_blue:
            return [self._aircraft(), self._ground(), self._budget()]
        return [self._aircraft(), self._ground()]

    def _aircraft(self) -> QWidget:
        every = ParkingType(fixed_wing=True, fixed_wing_stol=True, rotary_wing=True)
        allocation = self.cp.allocated_aircraft(every)
        parking = self.cp.total_aircraft_parking(every)
        present = allocation.total_present
        free = max(
            parking
            - present
            - allocation.total_transferring
            - allocation.total_ordered,
            0,
        )
        note = f"{free} free"
        if allocation.total_ordered:
            note += f" · {allocation.total_ordered} ordered"
        return figure(f"{present} / {parking}", "Aircraft", note)

    def _ground(self) -> QWidget:
        transfers = self.game_model.game.coalition_for(self.cp.captured).transfers
        allocation = self.cp.allocated_ground_units(transfers)
        limit = self.cp.frontline_unit_count_limit
        reserve = max(allocation.total_present - limit, 0)
        parts = [f"{reserve} reserve"]
        if allocation.total_transferring_out:
            parts.append(f"{allocation.total_transferring_out} transferring out")
        if allocation.total_ordered:
            parts.append(f"{allocation.total_ordered} ordered")
        return figure(f"{allocation.total_present}", "Ground units", " · ".join(parts))

    def _budget(self) -> QWidget:
        budget = self.game_model.game.blue.budget
        return figure(f"${budget:.2f}M", "Budget", "available to spend")
