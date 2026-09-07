"""The pilots who have asked for a rest, and your answer.

Shown once at the end of a turn, after the debriefing, when anybody asked. A pilot asks
more often the worse he is holding up, but a contented one asks now and then too. Saying
yes costs you the man for the turns you grant; saying no costs him morale.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from game.squadrons import morale as morale_rules
from game.squadrons.pilot import Pilot

if TYPE_CHECKING:
    from game.game import Game
    from game.squadrons.squadron import Squadron


def spare_pilots(squadron: "Squadron", excluding: Optional[Pilot] = None) -> int:
    """Who would still be available if this man went.

    Not the wounded, not the ones already resting, and not the ones who have asked and
    are waiting on the same answer -- granting them all is the mistake this is here to
    stop.
    """
    return sum(
        1
        for pilot in squadron.current_roster
        if pilot is not excluding
        and pilot.alive
        and not pilot.wounded
        and not pilot.on_leave
        and not pilot.wants_leave
    )


def pending_leave_requests(game: "Game") -> list[tuple["Squadron", Pilot]]:
    """Everyone on the player's side waiting to be told yes or no."""
    requests: list[tuple[Squadron, Pilot]] = []
    for squadron in game.blue.air_wing.iter_squadrons():
        for pilot in squadron.current_roster:
            # Active only: a man already in a bed cannot be asking for a rest, whatever
            # a save from before that rule may hold.
            if pilot.wants_leave and pilot.status.value == "Active":
                requests.append((squadron, pilot))
    # The one in the worst state first: he is the one the answer matters most to.
    requests.sort(key=lambda pair: pair[1].morale)
    return requests


class LeaveRequestsDialog(QDialog):
    def __init__(self, game: "Game", requests: list[tuple["Squadron", Pilot]]) -> None:
        super().__init__()
        self.game = game
        self.requests = requests
        self.rows: list[tuple[Squadron, Pilot, QCheckBox, QSpinBox]] = []

        self.setModal(True)
        self.setWindowTitle("Leave requests")
        self.setWindowIcon(QIcon("./resources/icon.png"))
        self.setMinimumWidth(940)

        outer = QVBoxLayout()
        self.setLayout(outer)
        outer.addWidget(
            QLabel(
                "<b>These pilots have asked for leave.</b><br>"
                "Grant it and they are off the roster for the turns you set, coming "
                "back steadier. Refuse and they take it badly."
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        scroll.setWidget(body)
        grid = QGridLayout()
        body.setLayout(grid)
        outer.addWidget(scroll, 1)

        for column, heading in enumerate(
            (
                "Pilot",
                "Squadron",
                "Aircraft",
                "Morale",
                "Cover left",
                "Asked",
                "Grant",
            )
        ):
            grid.addWidget(QLabel(f"<b>{heading}</b>"), 0, column)

        for row, (squadron, pilot) in enumerate(requests, start=1):
            rank = squadron.pilot_rank(pilot)
            name = pilot.name if rank is None else f"{rank.abbreviation} {pilot.name}"
            grid.addWidget(QLabel(name), row, 0)
            grid.addWidget(QLabel(str(squadron)), row, 1)
            grid.addWidget(QLabel(str(squadron.aircraft)), row, 2)

            state = morale_rules.morale_state(pilot.morale)
            morale = QLabel(state.name)
            if state.severity:
                morale.setText(f"<b>{state.name}</b>")
                morale.setToolTip("He is close to being no use to you at all.")
            grid.addWidget(morale, row, 3)

            # Saying yes to two men costs a squadron of sixteen pilots and four
            # aircraft nothing, and one of ten and twelve a mission it cannot fly.
            spare = spare_pilots(squadron, excluding=pilot)
            aircraft = squadron.owned_aircraft
            cover = QLabel(f"{spare} free · {aircraft} aircraft")
            if spare < aircraft:
                cover.setText(f"<b>{spare} free</b> · {aircraft} aircraft")
                cover.setToolTip(
                    "Granting this leaves fewer pilots than airframes: something will "
                    "sit on the ground."
                )
            grid.addWidget(cover, row, 4)

            # He asked for a number; the player may hand him less. The box opens on
            # what he asked for so saying yes is one click.
            asked = pilot.leave_turns_requested or morale_rules.DEFAULT_LEAVE_TURNS
            turns = QSpinBox()
            turns.setRange(1, morale_rules.MAX_LEAVE_TURNS)
            turns.setValue(min(asked, morale_rules.MAX_LEAVE_TURNS))
            turns.setToolTip(f"He asked for {asked}.")
            grid.addWidget(turns, row, 5)

            grant = QCheckBox()
            grant.setChecked(bool(state.severity))
            grid.addWidget(grant, row, 6, Qt.AlignmentFlag.AlignCenter)

            self.rows.append((squadron, pilot, grant, turns))

        # The squadron name is the one that varies; everything else is a short word.
        grid.setColumnStretch(1, 1)

        apply_button = QPushButton("Answer them")
        apply_button.clicked.connect(self.answer)
        outer.addWidget(apply_button)

    def answer(self) -> None:
        """Grant the ticked ones and refuse the rest. Unanswered is an answer."""
        turn = self.game.turn
        for squadron, pilot, grant, turns in self.rows:
            pilot.wants_leave = False
            if grant.isChecked():
                try:
                    squadron.send_on_leave(pilot, turns.value(), turn)
                except RuntimeError:
                    logging.exception(f"Could not send {pilot.name} on leave")
                continue
            pilot.leave_turns_requested = 0
            pilot.move_morale(
                morale_rules.LEAVE_REFUSED,
                squadron.pilot_skill(pilot),
                self.game.settings,
                turn,
            )
            logging.info(f"{pilot.name} was refused leave")
        self.accept()
