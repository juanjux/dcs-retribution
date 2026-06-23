import logging
from typing import Callable, Dict, TypeVar

from PySide6.QtGui import QIcon, QPixmap, QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from game.debriefing import Debriefing
from game.theater import Player
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal

T = TypeVar("T")


class LossGrid(QGridLayout):
    def __init__(self, debriefing: Debriefing, player: Player) -> None:
        super().__init__()

        self.add_air_loss_rows(debriefing, player)
        self.add_loss_rows(
            debriefing.front_line_losses_by_type(player), lambda u: str(u)
        )
        self.add_loss_rows(
            debriefing.convoy_losses_by_type(player), lambda u: f"{u} from convoy"
        )
        self.add_loss_rows(
            debriefing.cargo_ship_losses_by_type(player),
            lambda u: f"{u} from cargo ship",
        )
        self.add_loss_rows(
            debriefing.airlift_losses_by_type(player), lambda u: f"{u} from airlift"
        )
        self.add_loss_rows(debriefing.ground_object_losses_by_type(player), lambda u: u)
        self.add_loss_rows(debriefing.scenery_losses_by_type(player), lambda u: u)

        # TODO: Display dead ground object units and runways.

    def add_loss_rows(self, losses: Dict[T, int], make_name: Callable[[T], str]):
        for unit_type, count in losses.items():
            row = self.rowCount()
            try:
                name = make_name(unit_type)
            except AttributeError:
                logging.exception(f"Could not make unit name for {unit_type}")
                name = unit_type.id
            self.addWidget(QLabel(name), row, 0)
            self.addWidget(QLabel(str(count)), row, 1)

    def add_air_loss_rows(self, debriefing: Debriefing, player: Player) -> None:
        # Air losses, flagging how many didn't count when the "crashes don't
        # count" doctrine is on, so the debrief matches what the campaign applied.
        doctrine_on = bool(
            getattr(debriefing.game.settings, "ignore_non_combat_air_losses", False)
        )
        losses = (
            debriefing.air_losses.player
            if player.is_blue
            else debriefing.air_losses.enemy
        )
        not_counted: Dict[object, int] = {}
        if doctrine_on:
            for loss in losses:
                if debriefing.is_non_combat_loss(loss):
                    unit_type = loss.flight.unit_type
                    not_counted[unit_type] = not_counted.get(unit_type, 0) + 1
        for unit_type, count in debriefing.air_losses.by_type(player).items():
            row = self.rowCount()
            try:
                name = unit_type.display_name
            except AttributeError:
                name = unit_type.id
            self.addWidget(QLabel(name), row, 0)
            self.addWidget(QLabel(str(count)), row, 1)
            nc = not_counted.get(unit_type, 0)
            if nc:
                self.addWidget(
                    QLabel(
                        f"({nc} not counted because of crashed-do-not-count setting)"
                    ),
                    row,
                    2,
                )


class ScrollingCasualtyReportContainer(QGroupBox):
    def __init__(self, debriefing: Debriefing, player: Player) -> None:
        country = (
            debriefing.player_country if player.is_blue else debriefing.enemy_country
        )
        super().__init__(f"{country}'s lost units:")
        scroll_content = QWidget()
        scroll_content.setLayout(LossGrid(debriefing, player))
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_content)
        layout = QVBoxLayout()
        layout.addWidget(scroll_area)
        self.setLayout(layout)


class QDebriefingWindow(QDialog):
    def __init__(self, debriefing: Debriefing):
        super(QDebriefingWindow, self).__init__()
        self.debriefing = debriefing

        self.setModal(True)
        self.setWindowTitle("Debriefing")
        self.setMinimumSize(300, 200)
        self.setWindowIcon(QIcon("./resources/icon.png"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel(self)
        header.setGeometry(0, 0, 655, 106)
        pixmap = QPixmap("./resources/ui/debriefing.png")
        header.setPixmap(pixmap)
        layout.addWidget(header)

        title = QLabel("<b>Casualty report</b>")
        layout.addWidget(title)

        player_lost_units = ScrollingCasualtyReportContainer(
            debriefing, player=Player.BLUE
        )
        layout.addWidget(player_lost_units)

        enemy_lost_units = ScrollingCasualtyReportContainer(
            debriefing, player=Player.RED
        )
        layout.addWidget(enemy_lost_units, 1)

        okay = QPushButton("Okay")
        okay.clicked.connect(self.close)
        layout.addWidget(okay)

    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)
        state = self.debriefing.game.check_win_loss()
        GameUpdateSignal.get_instance().gameStateChanged(state)
