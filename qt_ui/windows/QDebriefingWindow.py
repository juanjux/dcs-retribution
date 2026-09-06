import logging
from typing import Callable, Dict, Optional, TypeVar

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QFrame,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from game.cruise_raids import debrief_expenditures
from game.debriefing import Debriefing
from game.squadrons.experience import turns_phrase
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
            debriefing.motorpool_losses_by_type(player),
            lambda u: f"{u} from motorpool",
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
            nc = not_counted.get(unit_type, 0)
            # Show the counted figure as the headline — which may be 0 when every
            # loss of this type was an ignored non-combat crash — so the player
            # still sees the type went down; the parenthetical explains why it
            # didn't count.
            counted = count - nc
            row = self.rowCount()
            try:
                name = unit_type.display_name
            except AttributeError:
                name = unit_type.id
            self.addWidget(QLabel(name), row, 0)
            self.addWidget(QLabel(str(counted)), row, 1)
            if nc:
                self.addWidget(
                    QLabel(
                        f"(other {nc} not counted because of crashed-do-not-count setting)"
                    ),
                    row,
                    2,
                )


class CasualtyReportContainer(QGroupBox):
    """The list of what one side lost.

    It used to be a scroll area of its own, from when the window did not scroll. Now
    that the whole report does, a second bar inside it only makes two lines of losses
    look like a list too long to fit.
    """

    def __init__(self, debriefing: Debriefing, player: Player) -> None:
        country = (
            debriefing.player_country if player.is_blue else debriefing.enemy_country
        )
        super().__init__(f"{country}'s lost units:")
        self.setLayout(LossGrid(debriefing, player))


class MissionImpactGrid(QGridLayout):
    def __init__(self, debriefing: Debriefing) -> None:
        super().__init__()
        for row, (label, value) in enumerate(self._rows_for(debriefing)):
            self.addWidget(QLabel(f"<b>{label}</b>"), row, 0)
            self.addWidget(QLabel(value), row, 1)

    @staticmethod
    def _rows_for(debriefing: Debriefing) -> list[tuple[str, str]]:
        blue_losses = debriefing.loss_counts(Player.BLUE)
        red_losses = debriefing.loss_counts(Player.RED)
        captured = [
            capture.control_point.name
            for capture in debriefing.base_captures
            if capture.captured_by_player.is_blue
        ]
        lost = [
            capture.control_point.name
            for capture in debriefing.base_captures
            if capture.captured_by_player.is_red
        ]
        runways = [airfield.name for airfield in debriefing.damaged_runways]

        rows = [
            (
                "Mission status",
                (
                    "Mission ended normally"
                    if debriefing.state_data.mission_ended
                    else "Mission ended early or state data was incomplete"
                ),
            ),
            (
                "Bases captured",
                ", ".join(captured) if captured else "None",
            ),
            (
                "Bases lost",
                ", ".join(lost) if lost else "None",
            ),
            (
                "Runways damaged",
                ", ".join(runways) if runways else "None",
            ),
            (
                f"{debriefing.player_country} losses",
                f"{blue_losses.aircraft} aircraft, {blue_losses.front_line} front-line "
                f"units, {blue_losses.ground_objects} site units, {blue_losses.bases_lost} bases",
            ),
            (
                f"{debriefing.enemy_country} losses",
                f"{red_losses.aircraft} aircraft, {red_losses.front_line} front-line "
                f"units, {red_losses.ground_objects} site units, {red_losses.bases_lost} bases",
            ),
        ]
        return rows


class MissionImpactContainer(QGroupBox):
    def __init__(self, debriefing: Debriefing) -> None:
        super().__init__("Mission Impact")
        layout = QVBoxLayout()
        layout.addLayout(MissionImpactGrid(debriefing))
        self.setLayout(layout)


class QDebriefingWindow(QDialog):
    def __init__(self, debriefing: Debriefing):
        super(QDebriefingWindow, self).__init__()
        self.debriefing = debriefing

        self.setModal(True)
        self.setWindowTitle("Debriefing")
        self.setMinimumSize(300, 200)
        self.setWindowIcon(QIcon("./resources/icon.png"))

        # The report scrolls as a whole. It used not to, and a mission with a busy
        # Pilots box squeezed every section until the lines overlapped each other:
        # the window can only grow to the height of the screen, and the layout took
        # the difference out of whatever was longest.
        outer = QVBoxLayout()
        self.setLayout(outer)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll, 1)

        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout()
        body.setLayout(layout)

        header = QLabel(self)
        header.setGeometry(0, 0, 655, 106)
        pixmap = QPixmap("./resources/ui/debriefing.png")
        header.setPixmap(pixmap)
        layout.addWidget(header)

        title = QLabel("<b>Casualty report</b>")
        layout.addWidget(title)

        impact = MissionImpactContainer(debriefing)
        layout.addWidget(impact)

        player_lost_units = CasualtyReportContainer(debriefing, player=Player.BLUE)
        layout.addWidget(player_lost_units)

        enemy_lost_units = CasualtyReportContainer(debriefing, player=Player.RED)
        layout.addWidget(enemy_lost_units)

        # Shown after the turn-boundary debit, so "remaining" is the magazine sailing
        # into next turn. Enemy remainders stay hidden.
        expenditures = debrief_expenditures(debriefing.game, debriefing)
        if expenditures:
            expenditure_box = QGroupBox("Cruise missiles expended:")
            expenditure_grid = QGridLayout()
            for row, (group_name, fired, remaining) in enumerate(expenditures):
                expenditure_grid.addWidget(QLabel(group_name), row, 0)
                if remaining is None:
                    detail = f"{fired} fired"
                else:
                    detail = f"{fired} fired, {remaining} remaining"
                expenditure_grid.addWidget(QLabel(detail), row, 1)
            expenditure_box.setLayout(expenditure_grid)
            layout.addWidget(expenditure_box)

        pilots_box = self._pilots_box(debriefing)
        if pilots_box is not None:
            layout.addWidget(pilots_box)
        layout.addStretch(1)

        # Outside the scroll area: the way out of the dialog is always in reach.
        okay = QPushButton("Okay")
        okay.clicked.connect(self.close)
        outer.addWidget(okay)

        # Tall enough to read without being taller than the screen.
        available = self.screen().availableGeometry() if self.screen() else None
        if available is not None:
            self.resize(
                min(760, available.width() - 80),
                min(920, available.height() - 80),
            )

    @staticmethod
    def _pilots_box(debriefing: Debriefing) -> Optional[QGroupBox]:
        """Who went up, who walked away, and who did not come back.

        Omitted entirely when nothing happened to the aircrew: an empty box says less
        than no box.
        """
        outcomes = debriefing.pilot_outcomes
        if outcomes.empty:
            return None

        box = QGroupBox("Pilots:")
        grid = QGridLayout()
        row = 0

        def line(text: str, detail: str = "") -> None:
            nonlocal row
            grid.addWidget(QLabel(text), row, 0)
            if detail:
                grid.addWidget(QLabel(detail), row, 1)
            row += 1

        if outcomes.promotions:
            line("<b>Promoted</b>")
            for promotion in outcomes.promotions:
                line(
                    f"{promotion.from_rank} {promotion.pilot_name}",
                    f"promoted to {promotion.to_rank} — {promotion.squadron}",
                )

        if outcomes.survivors:
            line("<b>Shot down and recovered</b>")
            for survivor in outcomes.survivors:
                brought_down = survivor.killed_by or "an unknown attacker"
                line(
                    survivor.pilot_name,
                    f"lost his {survivor.aircraft} to {brought_down}, and walked away",
                )

        if outcomes.wounded:
            line("<b>Wounded</b>")
            for wound in outcomes.wounded:
                line(
                    wound.pilot_name,
                    f"pulled out alive, unavailable for "
                    f"{turns_phrase(wound.turns)} — {wound.squadron}",
                )

        if outcomes.morale_shifts:
            line("<b>Morale</b>")
            for shift in outcomes.morale_shifts:
                direction = "up" if shift.after > shift.before else "down"
                line(
                    shift.pilot_name,
                    f"{direction} from {shift.before} to {shift.after} — "
                    f"{', '.join(shift.reasons)}",
                )

        if outcomes.deaths:
            line("<b>Killed in action</b>")
            for death in outcomes.deaths:
                if death.friendly_fire:
                    detail = f"killed by {death.killed_by} — friendly fire"
                elif death.killed_by:
                    detail = f"killed by {death.killed_by}"
                else:
                    detail = "lost, with nobody credited"
                line(f"{death.pilot_name} ({death.aircraft})", detail)

        box.setLayout(grid)
        return box

    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)
        # Queued rather than shown here: this dialog is modal and still closing, and a
        # second modal raised inside its own close handler does not always come up.
        QTimer.singleShot(0, self._congratulate_the_player)
        QTimer.singleShot(0, self._answer_leave_requests)
        state = self.debriefing.game.check_win_loss()
        GameUpdateSignal.get_instance().gameStateChanged(state)

    def _answer_leave_requests(self) -> None:
        """Whoever asked for a rest this turn, and your answer.

        Queued after the promotion box so the good news comes first.
        """
        from qt_ui.windows.LeaveRequestsDialog import (
            LeaveRequestsDialog,
            pending_leave_requests,
        )

        game = self.debriefing.game
        if not game.settings.live_pilots_enabled or not getattr(
            game.settings, "morale_enabled", True
        ):
            return
        requests = pending_leave_requests(game)
        if not requests:
            return
        self._leave_dialog = LeaveRequestsDialog(game, requests)
        self._leave_dialog.exec()

    def _congratulate_the_player(self) -> None:
        """Tell the player he has been promoted. Nobody else gets a parade."""
        promotions = [p for p in self.debriefing.pilot_outcomes.promotions if p.player]
        if not promotions:
            return

        # He knows who he is and which squadron he flies for, so the rank is the whole
        # of the news. More than one player pilot can be promoted in a mission, though,
        # and then they cannot all be "you": name them instead.
        box = QMessageBox(self)
        box.setWindowTitle("Promotion")
        box.setIcon(QMessageBox.Icon.Information)
        if len(promotions) == 1:
            rank = promotions[0].to_rank_full or promotions[0].to_rank
            box.setText(f"<b>Congratulations, you have been promoted to {rank}!</b>")
        else:
            box.setText("<b>Congratulations!</b>")
            box.setInformativeText(
                "<br>".join(
                    f"{p.pilot_name} is promoted to {p.to_rank_full or p.to_rank}"
                    for p in promotions
                )
            )
        box.exec()
