import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QProgressDialog,
    QPushButton,
)

import qt_ui.uiconstants as CONST
from game import Game, persistency
from game.ato.flightstate import Uninitialized
from game.ato.package import Package
from game.ato.traveltime import TotEstimator
from game.profiling import logged_duration
from game.server import EventStream
from game.settings.settings import FastForwardStopCondition
from game.sim import GameUpdateEvents
from game.utils import meters
from qt_ui.models import GameModel
from qt_ui.simcontroller import SimController
from qt_ui.uiflags import UiFlags
from qt_ui.widgets.QBudgetBox import QBudgetBox
from qt_ui.widgets.QConditionsWidget import QConditionsWidget
from qt_ui.widgets.QFactionsInfos import QFactionsInfos
from qt_ui.widgets.QIntelBox import QIntelBox
from qt_ui.widgets.clientslots import MaxPlayerCount
from qt_ui.widgets.QMissionProgressPanel import MissionProgressPanel
from qt_ui.widgets.simspeedcontrols import SimSpeedControls
from qt_ui.windows.AirWingDialog import AirWingDialog
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.PendingTransfersDialog import PendingTransfersDialog
from qt_ui.windows.QWaitingForMissionResultWindow import DebriefingFileWrittenSignal


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
    def fix_tots(packages: List[Package]) -> None:
        for package in packages:
            estimator = TotEstimator(package)
            package.time_over_target = estimator.earliest_tot()

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

    def confirm_negative_start_time(self, negative_starts: List[Package]) -> bool:
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
            self.fix_tots(negative_starts)
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

    def launch_mission(self):
        """Finishes planning and waits for mission completion."""
        if not self.ato_has_clients() and not self.confirm_no_client_launch():
            return

        if self.check_no_missing_pilots():
            return

        negative_starts = self.negative_start_packages(
            self.sim_controller.current_time_in_sim
        )
        if negative_starts:
            if not self.confirm_negative_start_time(negative_starts):
                return

        if self.game.settings.fast_forward_stop_condition not in [
            FastForwardStopCondition.DISABLED,
            FastForwardStopCondition.MANUAL,
        ]:
            with logged_duration("Simulating to first contact"):
                self.sim_controller.run_to_first_contact()
        self.sim_controller.generate_miz(
            persistency.mission_path_for("retribution_nextturn.miz")
        )

        self._begin_mission_panel()

    # ------------------------------------------------------------------ #
    # Embedded "mission in progress" panel (replaces the old waiting dialog).
    # The live map is hidden and the panel takes its splitter slot; the rest
    # of the UI is covered with dim scrims so the panel reads as modal.
    # ------------------------------------------------------------------ #
    def _begin_mission_panel(self) -> None:
        window = self.window()
        self._mp_map = getattr(window, "liberation_map", None)
        self._mp_splitter = (
            self._mp_map.parentWidget() if self._mp_map is not None else None
        )
        self._mp_map_index = -1
        self._mp_splitter_sizes = None
        self._mp_debriefing = None
        self._mp_real_start = datetime.now()

        panel = MissionProgressPanel()
        self._mp_panel = panel

        if self._mp_splitter is not None:
            self._mp_map_index = self._mp_splitter.indexOf(self._mp_map)
            self._mp_splitter_sizes = self._mp_splitter.sizes()
            self._mp_splitter.insertWidget(self._mp_map_index, panel)
            self._mp_map.setVisible(False)

        overlay_parent = (
            window.centralWidget() if hasattr(window, "centralWidget") else window
        )
        panel.install_scrims(
            [
                self,
                getattr(window, "ato_panel", None),
                getattr(window, "info_panel", None),
            ],
            overlay_parent,
        )

        panel.accept_btn.clicked.connect(self._mp_accept)
        panel.manually_submit_btn.clicked.connect(self._mp_submit_manually)
        panel.abort_btn.clicked.connect(self._mp_abort)

        DebriefingFileWrittenSignal.get_instance().debriefingReceived.connect(
            self._mp_on_debriefing
        )
        self._mp_wait_thread = self.sim_controller.wait_for_debriefing(
            lambda d: DebriefingFileWrittenSignal.get_instance().sendDebriefing(d)
        )

        self._mp_timer = QTimer(self)
        self._mp_timer.timeout.connect(self._mp_tick)
        self._mp_timer.start(1000)
        self._mp_tick()

    def _mp_on_debriefing(self, debriefing) -> None:
        try:
            self._mp_debriefing = debriefing
            self._mp_panel.ingest_debriefing(debriefing)
        except Exception:
            logging.exception("Failed to ingest debriefing into mission panel")

    def _mp_tick(self) -> None:
        panel = getattr(self, "_mp_panel", None)
        if panel is None:
            return
        try:
            sim_time = self.sim_controller.current_time_in_sim_if_game_loaded
        except Exception:
            sim_time = None
        try:
            sim_elapsed = self.sim_controller.elapsed_time
        except Exception:
            sim_elapsed = None
        try:
            panel.update_clocks(
                self._mp_real_start,
                datetime.now(),
                sim_time,
                sim_elapsed,
                self.game.turn,
            )
        except Exception:
            logging.exception("mission panel: clock update failed")
        try:
            self._mp_update_conditions(panel)
        except Exception:
            logging.exception("mission panel: conditions update failed")
        try:
            self._mp_update_flights(panel)
        except Exception:
            logging.exception("mission panel: flights update failed")

    def _mp_update_conditions(self, panel: MissionProgressPanel) -> None:
        cond = self.game.conditions
        weather = cond.weather
        wind = weather.wind.at_0m
        speed_kt = round(getattr(wind, "speed", 0) * 1.94384)
        wind_str = f"{round(getattr(wind, 'direction', 0)):03d}° {speed_kt} kt"
        preset = getattr(weather.clouds, "preset", None)
        clouds = preset.name if preset is not None else "Clear"
        temp = getattr(weather.atmospheric, "temperature_celsius", None)
        tod = cond.time_of_day.name.replace("_", " ").title()
        panel.update_conditions(wind_str, clouds, temp, tod)

    def _mp_update_flights(self, panel: MissionProgressPanel) -> None:
        airborne = combat = waiting = 0
        for _, flight in self.game.db.flights.objects.items():
            state = flight.state
            if state is None or not state.alive:
                continue
            if state.in_combat:
                combat += 1
                airborne += 1
            elif state.in_flight:
                airborne += 1
            elif state.is_waiting_for_start:
                waiting += 1
        panel.update_flights(airborne, combat, waiting)

    def _mp_accept(self) -> None:
        debriefing = getattr(self, "_mp_debriefing", None)
        if debriefing is None:
            return
        # Turn processing blocks the UI; show an indeterminate busy dialog meanwhile.
        progress = QProgressDialog(
            "End of Mission Detected, processing Mission Data",
            "",
            0,
            0,
            self.window(),
        )
        progress.setWindowTitle("Processing")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.show()
        QApplication.processEvents()
        try:
            with logged_duration("Turn processing"):
                self.sim_controller.process_results(debriefing)
                self.game.pass_turn()
                GameUpdateSignal.get_instance().sendDebriefing(debriefing)
                GameUpdateSignal.get_instance().updateGame(self.game)
        finally:
            progress.close()
        self._mp_teardown()

    def _mp_submit_manually(self) -> None:
        file = QFileDialog.getOpenFileName(
            self, "Select game file to open", filter="json(*.json)", dir="."
        )
        if file[0] == "":
            return
        logging.debug("Processing manually submitted %s", file[0])
        wait_thread = getattr(self, "_mp_wait_thread", None)
        if wait_thread is not None:
            wait_thread.stop()
            self._mp_wait_thread = None
        DebriefingFileWrittenSignal.get_instance().sendDebriefing(
            self.sim_controller.debrief_current_state(Path(file[0]), force_end=True)
        )

    def _mp_abort(self) -> None:
        self.sim_controller.set_game(self.game)
        events = GameUpdateEvents()
        for _, f in self.game.db.flights.objects.items():
            f.state = Uninitialized(f, self.game.settings)
            events.update_flight(f)
        for cp in self.game.theater.controlpoints:
            cp.release_parking_slots()
        GameUpdateSignal.get_instance().updateGame(self.game)
        EventStream().put_nowait(events)
        self._mp_teardown()

    def _mp_teardown(self) -> None:
        timer = getattr(self, "_mp_timer", None)
        if timer is not None:
            timer.stop()
            self._mp_timer = None
        wait_thread = getattr(self, "_mp_wait_thread", None)
        if wait_thread is not None:
            wait_thread.stop()
            self._mp_wait_thread = None
        try:
            DebriefingFileWrittenSignal.get_instance().debriefingReceived.disconnect(
                self._mp_on_debriefing
            )
        except (RuntimeError, TypeError):
            pass
        panel = getattr(self, "_mp_panel", None)
        if panel is not None:
            panel.remove_scrims()
            panel.setParent(None)
            panel.deleteLater()
            self._mp_panel = None
        if getattr(self, "_mp_map", None) is not None:
            self._mp_map.setVisible(True)
            if self._mp_splitter is not None and self._mp_splitter_sizes is not None:
                self._mp_splitter.setSizes(self._mp_splitter_sizes)
        self._mp_map = None
        self._mp_splitter = None

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
