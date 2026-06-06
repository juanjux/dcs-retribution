from datetime import datetime
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
)

import qt_ui.uiconstants as CONST
from game import Game, persistency
from game.ato.flight import Flight
from game.ato.flightstate import Uninitialized
from game.ato.package import Package
from game.ato.starttype import StartType
from game.ato.traveltime import TotEstimator
from game.profiling import logged_duration
from game.settings.settings import FastForwardStopCondition
from game.utils import meters
from qt_ui.models import GameModel
from qt_ui.simcontroller import SimController
from qt_ui.uiflags import UiFlags
from qt_ui.widgets.QBudgetBox import QBudgetBox
from qt_ui.widgets.QConditionsWidget import QConditionsWidget
from qt_ui.widgets.QFactionsInfos import QFactionsInfos
from qt_ui.widgets.QIntelBox import QIntelBox
from qt_ui.widgets.clientslots import MaxPlayerCount
from qt_ui.widgets.simspeedcontrols import SimSpeedControls
from qt_ui.windows.AirWingDialog import AirWingDialog
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.PendingTransfersDialog import PendingTransfersDialog
from qt_ui.windows.QWaitingForMissionResultWindow import QWaitingForMissionResultWindow


class QTopPanel(QFrame):
    def __init__(
        self, game_model: GameModel, sim_controller: SimController, ui_flags: UiFlags
    ) -> None:
        super(QTopPanel, self).__init__()
        self.game_model = game_model
        self.sim_controller = sim_controller
        self.dialog: Optional[QDialog] = None

        self.setMaximumHeight(70)

        self.conditionsWidget = QConditionsWidget(sim_controller)
        self.budgetBox = QBudgetBox(self.game)

        pass_turn_text = "Pass Turn"
        if not self.game or self.game.turn == 0:
            pass_turn_text = "Begin Campaign"
        self.passTurnButton = QPushButton(pass_turn_text)
        self.passTurnButton.setIcon(CONST.ICONS["PassTurn"])
        self.passTurnButton.setProperty("style", "btn-primary")
        self.passTurnButton.clicked.connect(self.passTurn)
        if not self.game:
            self.passTurnButton.setEnabled(False)

        self.proceedButton = QPushButton("Take off")
        self.proceedButton.setIcon(CONST.ICONS["Proceed"])
        self.proceedButton.setProperty("style", "start-button")
        self.proceedButton.clicked.connect(self.launch_mission)
        if not self.game or self.game.turn == 0:
            self.proceedButton.setEnabled(False)

        self.factionsInfos = QFactionsInfos(self.game)

        self.air_wing = QPushButton("Air Wing")
        self.air_wing.setDisabled(True)
        self.air_wing.setProperty("style", "btn-primary")
        self.air_wing.clicked.connect(self.open_air_wing)

        self.transfers = QPushButton("Transfers")
        self.transfers.setDisabled(True)
        self.transfers.setProperty("style", "btn-primary")
        self.transfers.clicked.connect(self.open_transfers)

        self.intel_box = QIntelBox(self.game)

        self.buttonBox = QGroupBox("Misc")
        self.buttonBoxLayout = QHBoxLayout()
        self.buttonBoxLayout.addWidget(self.air_wing)
        self.buttonBoxLayout.addWidget(self.transfers)
        self.buttonBox.setLayout(self.buttonBoxLayout)

        self.simSpeedControls = SimSpeedControls(sim_controller)

        self.proceedBox = QGroupBox("Proceed")
        self.proceedBoxLayout = QHBoxLayout()
        if ui_flags.show_sim_speed_controls:
            self.proceedBoxLayout.addLayout(self.simSpeedControls)
        self.proceedBoxLayout.addLayout(MaxPlayerCount(self.game_model.ato_model))
        self.proceedBoxLayout.addWidget(self.passTurnButton)
        self.proceedBoxLayout.addWidget(self.proceedButton)
        self.proceedBox.setLayout(self.proceedBoxLayout)

        self.controls = [
            self.air_wing,
            self.transfers,
            self.simSpeedControls,
            self.passTurnButton,
            self.proceedButton,
        ]

        self.layout = QHBoxLayout()

        self.layout.addWidget(self.factionsInfos)
        self.layout.addWidget(self.conditionsWidget)
        self.layout.addWidget(self.budgetBox)
        self.layout.addWidget(self.intel_box)
        self.layout.addWidget(self.buttonBox)
        self.layout.addStretch(1)
        self.layout.addWidget(self.proceedBox)

        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)

        GameUpdateSignal.get_instance().gameupdated.connect(self.setGame)
        GameUpdateSignal.get_instance().budgetupdated.connect(self.budget_update)

    @property
    def game(self) -> Optional[Game]:
        return self.game_model.game

    def setGame(self, game: Optional[Game]):
        if game is None:
            return

        self.air_wing.setEnabled(True)
        self.transfers.setEnabled(True)

        self.conditionsWidget.setCurrentTurn(game.turn, game.conditions)

        if game.conditions.weather.clouds:
            base_m = game.conditions.weather.clouds.base
            base_ft = int(meters(base_m).feet)
            self.conditionsWidget.setToolTip(f"Cloud Base: {base_m}m / {base_ft}ft")
        else:
            self.conditionsWidget.setToolTip("")

        self.intel_box.set_game(game)
        self.budgetBox.setGame(game)
        self.factionsInfos.setGame(game)

        self.setControls(True)

        if game.turn > 0:
            self.passTurnButton.setText("Pass Turn")
        elif game.turn == 0:
            self.passTurnButton.setText("Begin Campaign")
            self.proceedButton.setEnabled(False)
            self.simSpeedControls.setEnabled(False)
        else:
            raise RuntimeError(f"game.turn out of bounds!\n  value = {game.turn}")

    def open_air_wing(self):
        self.dialog = AirWingDialog(self.game_model, self.window())
        self.dialog.show()

    def open_transfers(self):
        self.dialog = PendingTransfersDialog(self.game_model)
        self.dialog.show()

    def passTurn(self):
        with logged_duration("Skipping turn"):
            self.game.pass_turn(no_action=True)
            GameUpdateSignal.get_instance().updateGame(self.game)
            state = self.game_model.game.check_win_loss()
            GameUpdateSignal.get_instance().gameStateChanged(state)
            self.proceedButton.setEnabled(True)

    def negative_start_packages(self, now: datetime) -> List[Package]:
        packages = []
        for package in self.game_model.ato_model.ato.packages:
            if not package.flights:
                continue
            for flight in package.flights:
                if isinstance(flight.state, Uninitialized):
                    flight.state.reinitialize(now)
                if flight.state.is_waiting_for_start:
                    startup = flight.flight_plan.startup_time()
                    if startup < now:
                        packages.append(package)
                        break
        return packages

    @staticmethod
    def fix_tots(packages: List[Package], now: datetime) -> None:
        for package in packages:
            estimator = TotEstimator(package)
            package.time_over_target = estimator.earliest_tot(now)

    def ato_has_clients(self) -> bool:
        for package in self.game.blue.ato.packages:
            for flight in package.flights:
                if flight.client_count > 0:
                    return True
        return False

    def confirm_no_client_launch(self) -> bool:
        result = QMessageBox.question(
            self,
            "Continue without player pilots?",
            (
                "No player pilots have been assigned to flights. Continuing will allow "
                "the AI to perform the mission, but players will be unable to "
                "participate.<br />"
                "<br />"
                "To assign player pilots to a flight, select a package from the "
                "Packages panel on the left of the main window, and then a flight from "
                "the Flights panel below the Packages panel. The edit button below the "
                "Flights panel will allow you to assign specific pilots to the flight. "
                "If you have no player pilots available, the checkbox next to the "
                "name will convert them to a player.<br />"
                "<br />Click 'Yes' to continue with an AI only mission"
                "<br />Click 'No' if you'd like to make more changes."
            ),
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        return result == QMessageBox.StandardButton.Yes

    def confirm_negative_start_time(
        self, negative_starts: List[Package], now: datetime
    ) -> bool:
        formatted = "<br />".join(
            [f"{p.primary_task} {p.target.name}" for p in negative_starts]
        )
        mbox = QMessageBox(
            QMessageBox.Icon.Question,
            "Continue with past start times?",
            (
                "Some flights in the following packages have start times set "
                "earlier than mission start time:<br />"
                "<br />"
                f"{formatted}<br />"
                "<br />"
                "Flight start times are estimated based on the package TOT, so it "
                "is possible that not all flights will be able to reach the "
                "target area at their assigned times.<br />"
                "<br />"
                "You can either continue with the mission as planned, with the "
                "misplanned flights potentially flying too fast and/or missing "
                "their rendezvous; automatically fix negative TOTs; or cancel "
                "mission start and fix the packages manually."
            ),
            parent=self,
        )
        auto = mbox.addButton(
            "Fix TOTs automatically", QMessageBox.ButtonRole.ActionRole
        )
        ignore = mbox.addButton(
            "Continue without fixing", QMessageBox.ButtonRole.DestructiveRole
        )
        cancel = mbox.addButton(QMessageBox.StandardButton.Cancel)
        mbox.setEscapeButton(cancel)
        mbox.exec_()
        clicked = mbox.clickedButton()
        if clicked == auto:
            self.fix_tots(negative_starts, now)
            return True
        elif clicked == ignore:
            return True
        return False

    def check_no_missing_pilots(self) -> bool:
        missing_pilots = []
        for package in self.game.blue.ato.packages:
            for flight in package.flights:
                if flight.missing_pilots > 0:
                    missing_pilots.append((package, flight))

        if not missing_pilots:
            return False

        formatted = "<br />".join(
            [f"{p.primary_task} {p.target}: {f}" for p, f in missing_pilots]
        )
        mbox = QMessageBox(
            QMessageBox.Icon.Critical,
            "Flights are missing pilots",
            (
                "The following flights are missing one or more pilots:<br />"
                "<br />"
                f"{formatted}<br />"
                "<br />"
                "You must either assign pilots to those flights or cancel those "
                "missions."
            ),
            parent=self,
        )
        mbox.setEscapeButton(mbox.addButton(QMessageBox.StandardButton.Close))
        mbox.exec_()
        return True

    # Lowest start_type compatible with each player-targeted fast-forward
    # stop condition. If a player flight's start_type is "later" (skips
    # earlier states), the stop condition never fires for that flight.
    # Ordering of states the flight passes through:
    #   COLD -> StartUp -> Taxi -> Takeoff -> Navigating
    #   WARM ->           Taxi -> Takeoff -> Navigating
    #   RUNWAY ->                 Takeoff -> Navigating
    #   IN_FLIGHT ->                         Navigating
    _STOP_CONDITION_REQUIRED_START: dict[
        FastForwardStopCondition, frozenset[StartType]
    ] = {
        FastForwardStopCondition.PLAYER_STARTUP: frozenset({StartType.COLD}),
        FastForwardStopCondition.PLAYER_TAXI: frozenset(
            {StartType.COLD, StartType.WARM}
        ),
        FastForwardStopCondition.PLAYER_TAKEOFF: frozenset(
            {StartType.COLD, StartType.WARM, StartType.RUNWAY}
        ),
    }

    def _mismatched_player_flights(self) -> List[Flight]:
        """Return player flights whose start_type would skip the configured
        fast-forward stop condition (so the sim would never halt for them)."""
        cond = self.game.settings.fast_forward_stop_condition
        compatible = self._STOP_CONDITION_REQUIRED_START.get(cond)
        if compatible is None:
            return []
        mismatched: List[Flight] = []
        for package in self.game.blue.ato.packages:
            for flight in package.flights:
                if flight.client_count <= 0:
                    continue
                if flight.start_type not in compatible:
                    mismatched.append(flight)
        return mismatched

    @staticmethod
    def _matching_start_type_for_condition(
        cond: FastForwardStopCondition,
    ) -> StartType:
        """Earliest-state start_type compatible with cond. Picking the
        earliest preserves the user's intent ('halt at startup' means
        actually go through startup), at the cost of a longer pre-mission
        spool. Users who want a shorter spool can instead pick the
        'halt at this flight's start' branch."""
        if cond is FastForwardStopCondition.PLAYER_STARTUP:
            return StartType.COLD
        if cond is FastForwardStopCondition.PLAYER_TAXI:
            return StartType.WARM
        if cond is FastForwardStopCondition.PLAYER_TAKEOFF:
            return StartType.RUNWAY
        # Caller ensures cond targets a player-flight state.
        raise ValueError(f"No matching start type for {cond}")

    def resolve_start_type_mismatches(self) -> bool:
        """For every player flight whose start_type makes the configured
        fast-forward stop condition unreachable, ask the user to choose:
        adjust the flight or override the stop condition (both
        mission-only). Returns False if the user cancelled."""
        mismatches = self._mismatched_player_flights()
        if not mismatches:
            return True

        cond = self.game.settings.fast_forward_stop_condition
        matching = self._matching_start_type_for_condition(cond)

        for flight in mismatches:
            mbox = QMessageBox(self)
            mbox.setIcon(QMessageBox.Icon.Question)
            mbox.setWindowTitle("Fast-forward / start-type mismatch")
            mbox.setText(
                f"<b>{flight}</b> starts <b>{flight.start_type.value}</b>, but "
                f"<i>Fast forward until</i> is set to "
                f"<b>{cond.value}</b>, which is a state this flight will "
                f"skip.<br /><br />"
                f"Where would you like fast-forward to stop for this "
                f"flight?"
            )
            mbox.setInformativeText(
                "Both choices apply to <i>this mission only</i> and do not "
                "modify your saved settings."
            )
            change_flight_btn = mbox.addButton(
                f"Change this flight to {matching.value}",
                QMessageBox.ButtonRole.AcceptRole,
            )
            halt_at_spawn_btn = mbox.addButton(
                f"Halt at this flight's start ({flight.start_type.value})",
                QMessageBox.ButtonRole.AcceptRole,
            )
            cancel_btn = mbox.addButton(QMessageBox.StandardButton.Cancel)
            mbox.setEscapeButton(cancel_btn)
            mbox.exec_()
            clicked = mbox.clickedButton()
            if clicked is change_flight_btn:
                flight.start_type = matching
            elif clicked is halt_at_spawn_btn:
                flight.halt_sim_on_spawn = True
            else:
                return False
        return True

    def launch_mission(self):
        """Finishes planning and waits for mission completion."""
        if not self.ato_has_clients() and not self.confirm_no_client_launch():
            return

        if self.check_no_missing_pilots():
            return

        now = self.sim_controller.current_time_in_sim
        negative_starts = self.negative_start_packages(now)
        if negative_starts:
            if not self.confirm_negative_start_time(negative_starts, now):
                return

        if self.game.settings.fast_forward_stop_condition not in [
            FastForwardStopCondition.DISABLED,
            FastForwardStopCondition.MANUAL,
        ]:
            if not self.resolve_start_type_mismatches():
                return
            with logged_duration("Simulating to first contact"):
                self.sim_controller.run_to_first_contact()
        self.sim_controller.generate_miz(
            persistency.mission_path_for("retribution_nextturn.miz")
        )

        waiting = QWaitingForMissionResultWindow(self.game, self.sim_controller, self)
        waiting.exec_()

    def budget_update(self, game: Game):
        self.budgetBox.setGame(game)

    def setControls(self, enabled: bool):
        for controller in self.controls:
            controller.setEnabled(enabled)

    def check_for_contact(self) -> bool:
        if (
            len(self.game.blue.ato.packages) == 0
            and len(self.game.red.ato.packages) == 0
        ):
            mbox = QMessageBox(
                QMessageBox.Icon.Critical,
                "No flights planned",
                (
                    "No flights are planned and fast forward to first contact "
                    "is enabled. You must either plan flights or disable fast forward."
                ),
                parent=self,
            )
            mbox.setEscapeButton(mbox.addButton(QMessageBox.StandardButton.Close))
            mbox.exec_()
            return False
        return True
