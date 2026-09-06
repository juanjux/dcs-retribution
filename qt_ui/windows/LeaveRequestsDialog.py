"""The pilots who have asked for a rest, and your answer.

Shown once at the end of a turn, after the debriefing, when anybody asked. A pilot asks
more often the worse he is holding up, but a contented one asks now and then too. Saying
yes costs you the man for the turns you grant; saying no costs him morale.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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


def pending_leave_requests(game: "Game") -> list[tuple["Squadron", Pilot]]:
    """Everyone on the player's side waiting to be told yes or no."""
    requests: list[tuple[Squadron, Pilot]] = []
    for squadron in game.blue.air_wing.iter_squadrons():
        for pilot in squadron.current_roster:
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
        self.setMinimumWidth(640)

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
            ("Pilot", "Squadron", "Aircraft", "Holding up", "Turns", "Grant")
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

            turns = QSpinBox()
            turns.setRange(1, morale_rules.MAX_LEAVE_TURNS)
            turns.setValue(morale_rules.DEFAULT_LEAVE_TURNS)
            grid.addWidget(turns, row, 4)

            grant = QCheckBox()
            grant.setChecked(bool(state.severity))
            grid.addWidget(grant, row, 5, Qt.AlignmentFlag.AlignCenter)

            self.rows.append((squadron, pilot, grant, turns))

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
            pilot.morale = morale_rules.apply(
                pilot.morale,
                morale_rules.LEAVE_REFUSED,
                squadron.pilot_skill(pilot),
                self.game.settings,
            )
            logging.info(f"{pilot.name} was refused leave")
        self.accept()
