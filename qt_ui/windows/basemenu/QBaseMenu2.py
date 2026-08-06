from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QGridLayout,
)

from dcs.planes import B_1B
from game import Game
from game.ato.flighttype import FlightType
from game.config import RUNWAY_REPAIR_COST
from game.dcs.aircrafttype import AircraftType
from game.radio.ICLSContainer import ICLSContainer
from game.radio.RadioFrequencyContainer import RadioFrequencyContainer
from game.radio.TacanContainer import TacanContainer
from game.server import EventStream
from game.sim import GameUpdateEvents
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.theater import (
    AMMO_DEPOT_FRONTLINE_UNIT_CONTRIBUTION,
    ControlPoint,
    ControlPointType,
    FREE_FRONTLINE_UNIT_SUPPLY,
    NavalControlPoint,
    ParkingType,
    Player,
)
from qt_ui.dialogs import Dialog
from qt_ui.models import GameModel
from qt_ui.uiconstants import EVENT_ICONS
from qt_ui.widgets.QFrequencyWidget import QFrequencyWidget
from qt_ui.widgets.QICLSWidget import QICLSWidget
from qt_ui.widgets.QLink4Widget import QLink4Widget
from qt_ui.widgets.QTacanWidget import QTacanWidget
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.basemenu.NewUnitTransferDialog import NewUnitTransferDialog
from qt_ui.windows.basemenu.QBaseMenuTabs import QBaseMenuTabs
from qt_ui.windows.basemenu.UnitTransactionFrame import UnitTransactionFrame


class QBaseMenu2(QDialog):
    def __init__(self, parent, cp: ControlPoint, game_model: GameModel):
        super(QBaseMenu2, self).__init__(parent)

        # Attrs
        self.cp = cp
        self.game_model = game_model
        self.objectName = "menuDialogue"

        if self.cp.captured.is_blue:
            self.deliveryEvent = None

        self.setWindowIcon(EVENT_ICONS["capture"])

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(300, 200)
        self.setMinimumWidth(1024)
        self.setMaximumWidth(1024)
        self.setModal(True)

        self.setWindowTitle(self.cp.name)

        base_menu_header = QWidget()
        top_layout = QHBoxLayout()

        header = QLabel(self)
        header.setGeometry(0, 0, 655, 106)
        pixmap = QPixmap(self.get_base_image())
        header.setPixmap(pixmap)

        cp_settings = QGridLayout()
        top_layout.addLayout(cp_settings)

        title = QLabel("<b>" + self.cp.name + "</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        title.setProperty("style", "base-title")
        cp_settings.addWidget(title, 0, 0, 1, 2)
        cp_settings.setHorizontalSpacing(20)

        counter = 2

        self.freq_widget = None
        self.link4_widget = None

        is_friendly = cp.is_friendly(Player.BLUE)
        if is_friendly and isinstance(cp, RadioFrequencyContainer):
            self.freq_widget = QFrequencyWidget(cp, self.game_model)
            cp_settings.addWidget(self.freq_widget, counter // 2, counter % 2)
            counter += 1

        if is_friendly and isinstance(cp, TacanContainer):
            self.tacan_widget = QTacanWidget(cp, self.game_model)
            cp_settings.addWidget(self.tacan_widget, counter // 2, counter % 2)
            counter += 1

        if is_friendly and isinstance(cp, ICLSContainer):
            self.icls_widget = QICLSWidget(cp, self.game_model)
            cp_settings.addWidget(self.icls_widget, counter // 2, counter % 2)
            counter += 1

        if is_friendly and isinstance(cp, NavalControlPoint):
            self.link4_widget = QLink4Widget(cp, self.game_model)
            cp_settings.addWidget(self.link4_widget, counter // 2, counter % 2)
            counter += 1

        if self.freq_widget and self.link4_widget:
            # link them so on change they check freq
            self.freq_widget.freq_changed.connect(self.link4_widget.check_freq)
            self.link4_widget.freq_changed.connect(self.freq_widget.check_freq)

        self.intel_summary = QLabel()
        self.intel_summary.setTextFormat(Qt.TextFormat.RichText)
        self.intel_summary.setToolTip(self.generate_intel_tooltip())
        self.update_intel_summary()
        top_layout.addWidget(self.intel_summary)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        runway_buttons_layout = QVBoxLayout()
        top_layout.addLayout(runway_buttons_layout)

        if (
            self.cp.runway_is_destroyable
            and self.game_model.game.settings.enable_runway_state_cheat
        ):
            self.cheat_runway_state = QPushButton()
            self.update_cheat_runway_state_text()
            self.cheat_runway_state.clicked.connect(self.on_cheat_runway_state)
            runway_buttons_layout.addWidget(self.cheat_runway_state)

        self.repair_button = QPushButton()
        self.repair_button.clicked.connect(self.begin_runway_repair)
        self.update_repair_button()
        runway_buttons_layout.addWidget(self.repair_button)
        runway_buttons_layout.addStretch()

        base_menu_header.setProperty("style", "baseMenuHeader")
        base_menu_header.setLayout(top_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(header)
        main_layout.addWidget(base_menu_header)
        main_layout.addWidget(QBaseMenuTabs(cp, self.game_model))
        bottom_row = QHBoxLayout()
        main_layout.addLayout(bottom_row)

        if FlightType.OCA_RUNWAY in self.cp.mission_types(for_player=Player.BLUE):
            runway_attack_button = QPushButton("Attack airfield")
            bottom_row.addWidget(runway_attack_button)

            runway_attack_button.setProperty("style", "btn-danger")
            runway_attack_button.clicked.connect(self.new_package)

        if self.cp.captured.is_blue and self.has_transfer_destinations:
            transfer_button = QPushButton("Transfer Units")
            transfer_button.setProperty("style", "btn-success")
            bottom_row.addWidget(transfer_button)
            transfer_button.clicked.connect(self.open_transfer_dialog)

        if self.cheat_capturable:
            label = "Sink/Resurrect" if self.cp.is_fleet else "Capture"
            capture_button = QPushButton(f"CHEAT: {label}")
            capture_button.setProperty("style", "btn-danger")
            bottom_row.addWidget(capture_button)
            capture_button.clicked.connect(self.cheat_capture)

        self.budget_display = QLabel(
            UnitTransactionFrame.BUDGET_FORMAT.format(self.game_model.game.blue.budget)
        )
        self.budget_display.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom
        )
        self.budget_display.setProperty("style", "budget-label")
        bottom_row.addWidget(self.budget_display)
        GameUpdateSignal.get_instance().budgetupdated.connect(self.update_budget)
        self.setLayout(main_layout)

    @property
    def cheat_capturable(self) -> bool:
        return self.game_model.game.settings.enable_base_capture_cheat

    def cheat_capture(self) -> None:
        events = GameUpdateEvents()
        if self.cp.is_fleet:
            for go in self.cp.ground_objects:
                if go.is_naval_control_point:
                    if go.alive_unit_count > 0:
                        for u in go.units:
                            u.kill(events)
                    else:
                        for u in go.units:
                            u.revive(events)
        else:
            self.cp.capture(
                self.game_model.game, events, for_player=self.cp.captured.opponent
            )
            mrp = MissionResultsProcessor(self.game_model.game)
            mrp.redeploy_units(self.cp)
        # Reinitialized ground planners and the like. The ATO needs to be reset because
        # missions planned against the flipped base (or killed carrier) are no longer valid.
        self.game_model.game.initialize_turn(events)
        EventStream.put_nowait(events)
        GameUpdateSignal.get_instance().updateGame(self.game_model.game)
        state = self.game_model.game.check_win_loss()
        GameUpdateSignal.get_instance().gameStateChanged(state)
        self.close()

    @property
    def has_transfer_destinations(self) -> bool:
        return self.game_model.game.transit_network_for(
            self.cp.captured
        ).has_destinations(self.cp)

    def update_cheat_runway_state_text(self) -> None:
        if self.cp.runway_can_be_repaired:
            self.cheat_runway_state.setText("CHEAT: Repair runway")
        else:
            self.cheat_runway_state.setText("CHEAT: Destroy runway")

    def on_cheat_runway_state(self) -> None:
        if self.cp.runway_can_be_repaired:
            self.cp.runway_status.repair()
        else:
            self.cp.runway_status.damage()
        self.update_cheat_runway_state_text()
        self.update_repair_button()
        self.update_intel_summary()
        with EventStream.event_context() as events:
            events.update_control_point(self.cp)

    @property
    def can_repair_runway(self) -> bool:
        return self.cp.captured.is_blue and self.cp.runway_can_be_repaired

    @property
    def can_afford_runway_repair(self) -> bool:
        return self.game_model.game.blue.budget >= RUNWAY_REPAIR_COST

    def begin_runway_repair(self) -> None:
        if not self.can_afford_runway_repair:
            QMessageBox.critical(
                self,
                "Cannot repair runway",
                f"Runway repair costs ${RUNWAY_REPAIR_COST}M but you have "
                f"only ${self.game_model.game.blue.budget}M available.",
                QMessageBox.StandardButton.Ok,
            )
            return
        if not self.can_repair_runway:
            QMessageBox.critical(
                self,
                "Cannot repair runway",
                f"Cannot repair this runway.",
                QMessageBox.StandardButton.Ok,
            )
            return

        self.cp.begin_runway_repair()
        self.game_model.game.blue.budget -= RUNWAY_REPAIR_COST
        self.update_repair_button()
        self.update_intel_summary()
        GameUpdateSignal.get_instance().updateGame(self.game_model.game)

    def update_repair_button(self) -> None:
        self.repair_button.setVisible(True)
        turns_remaining = self.cp.runway_status.repair_turns_remaining
        if self.cp.captured.is_blue and turns_remaining is not None:
            self.repair_button.setText("Repairing...")
            self.repair_button.setDisabled(True)
            return

        if self.can_repair_runway:
            if self.can_afford_runway_repair:
                self.repair_button.setText(f"Repair ${RUNWAY_REPAIR_COST}M")
                self.repair_button.setDisabled(False)
                return
            else:
                self.repair_button.setText(
                    f"Cannot afford repair ${RUNWAY_REPAIR_COST}M"
                )
                self.repair_button.setDisabled(True)
                return

        self.repair_button.setVisible(False)
        self.repair_button.setDisabled(True)

    def _parking_categories(self) -> "dict[str, dict[str, int]] | None":
        """Estimate per-category parking usage by simulating slot allocation.

        The data model only tracks aircraft counts, not which slot each one
        occupies, so this replicates the placement priority used elsewhere to
        attribute aircraft to slot categories. The split is an estimate.
        """
        airport = self.cp.dcs_airport
        if airport is None:
            return None

        pt_rotary = ParkingType(rotary_wing=True)
        pt_stol = ParkingType(fixed_wing_stol=True)
        slots = list(self.cp.parking_slots)
        totals = {
            "shared": len([s for s in slots if s.helicopter and s.airplanes]),
            "fixed": len([s for s in slots if s.airplanes and not s.helicopter]),
            "rotary": len([s for s in slots if s.helicopter and not s.airplanes])
            + self.cp.total_aircraft_parking(pt_rotary),
            "ground": self.cp.total_aircraft_parking(pt_stol),
        }
        counts: dict[str, dict[str, int]] = {
            c: {"present": 0, "transferring": 0, "ordered": 0}
            for c in ("shared", "fixed", "rotary", "ground")
        }

        ap = deepcopy(airport)
        free_helipads = self.cp.total_aircraft_parking(pt_rotary)
        free_ground = self.cp.total_aircraft_parking(pt_stol)
        ground_start = self.cp.coalition.game.settings.ground_start_ai_planes

        def place(aircraft: AircraftType, phase: str) -> None:
            nonlocal free_helipads, free_ground
            is_heli = aircraft.helicopter
            is_vtol = not is_heli and aircraft.lha_capable
            ground_ok = aircraft.flyable or ground_start
            if free_helipads > 0 and is_heli:
                free_helipads -= 1
                counts["rotary"][phase] += 1
            elif free_ground > 0 and (is_heli or is_vtol or ground_ok):
                free_ground -= 1
                counts["ground"][phase] += 1
            else:
                slot = ap.free_parking_slot(aircraft.dcs_unit_type)
                if slot is None:
                    return
                slot.unit_id = 1
                if slot.helicopter and slot.airplanes:
                    counts["shared"][phase] += 1
                elif slot.airplanes:
                    counts["fixed"][phase] += 1
                else:
                    counts["rotary"][phase] += 1

        staying = [s for s in self.cp.squadrons if s.destination is None]
        incoming = [
            s
            for s in self.cp.coalition.air_wing.iter_squadrons()
            if s.destination == self.cp
        ]
        for s in staying:
            for _ in range(s.owned_aircraft):
                place(s.aircraft, "present")
        for s in incoming:
            for _ in range(s.owned_aircraft):
                place(s.aircraft, "transferring")
        for s in staying + incoming:
            for _ in range(max(s.pending_deliveries, 0)):
                place(s.aircraft, "ordered")

        # Fixed-wing slots split by size. "Big" slots are those that can host a
        # heavy aircraft (C-130, B-1B, tankers, AWACS...). DCS uses two slot
        # schemes: v1 maps flag big slots with .large, while v2 maps decide
        # purely by physical dimensions, so we mirror pydcs' own v2 fit test
        # against a representative heavy (the B-1B). Free counts come from the
        # placement sim above, so they match what a transfer would actually find.
        fw_slots = [s for s in ap.parking_slots if s.airplanes]
        if ap.slot_version == 1:
            big_flags = [s.large for s in fw_slots]
        else:
            big_flags = [
                s.width is not None
                and s.length is not None
                and B_1B.width < s.width
                and B_1B.height < (s.height or 1000)
                and B_1B.length < s.length
                for s in fw_slots
            ]
        big_total = sum(big_flags)
        small_total = len(fw_slots) - big_total
        free_big = sum(
            1 for s, big in zip(fw_slots, big_flags) if big and s.unit_id is None
        )
        free_small = sum(
            1 for s, big in zip(fw_slots, big_flags) if not big and s.unit_id is None
        )

        result: dict[str, dict[str, int]] = {}
        for c, total in totals.items():
            occ = counts[c]["present"]
            tr = counts[c]["transferring"]
            od = counts[c]["ordered"]
            result[c] = {
                "total": total,
                "occupied": occ,
                "transferring": tr,
                "ordered": od,
                "free": max(total - occ - tr - od, 0),
            }
        result["fixed_size"] = {
            "small_total": small_total,
            "free_small": free_small,
            "big_total": big_total,
            "free_big": free_big,
        }
        return result

    def update_intel_summary(self) -> None:
        parking_type_all = ParkingType(
            fixed_wing=True, fixed_wing_stol=True, rotary_wing=True
        )

        air_alloc = self.cp.allocated_aircraft(parking_type_all)
        aircraft = air_alloc.total_present
        parking = self.cp.total_aircraft_parking(parking_type_all)
        air_transferring = air_alloc.total_transferring
        air_ordered = air_alloc.total_ordered
        air_free = max(parking - aircraft - air_transferring - air_ordered, 0)
        parking_type_stol = ParkingType(
            fixed_wing=False, fixed_wing_stol=True, rotary_wing=False
        )
        parking_type_rotary_wing = ParkingType(
            fixed_wing=False, fixed_wing_stol=False, rotary_wing=True
        )
        ground_spawn_parking = self.cp.total_aircraft_parking(parking_type_stol)
        helipads = self.cp.total_aircraft_parking(parking_type_rotary_wing)
        ground_unit_limit = self.cp.frontline_unit_count_limit
        deployable_unit_info = ""

        allocated = self.cp.allocated_ground_units(
            self.game_model.game.coalition_for(self.cp.captured).transfers
        )
        unit_overage = max(
            allocated.total_present - self.cp.frontline_unit_count_limit, 0
        )
        if self.cp.has_active_frontline:
            deployable_unit_info = (
                f" (Up to {ground_unit_limit} deployable, {unit_overage} reserve)"
            )

        # Grouped into Air / Ground / Status sections for readability. Indentation
        # via non-breaking spaces since this renders as rich text in a QLabel.
        i1 = "&nbsp;" * 4
        i2 = "&nbsp;" * 8
        air_lines = [
            "<b>Air</b>",
            f"{i1}Total: {aircraft}/{parking} aircraft ({air_free} free)",
        ]
        ground_spawn_line = None
        breakdown = self._parking_categories()
        if breakdown is not None:
            fs = breakdown["fixed_size"]
            fw_total = fs["small_total"] + fs["big_total"]
            fw_free = fs["free_small"] + fs["free_big"]
            air_lines += [
                f"{i1}Fixed-wing: {fw_free} free of {fw_total}",
                f"{i2}Small: {fs['free_small']} free of {fs['small_total']}",
                f"{i2}Big: {fs['free_big']} free of {fs['big_total']}",
                f"{i1}Rotary: {breakdown['rotary']['free']} free of "
                f"{breakdown['rotary']['total']}",
            ]
            if air_transferring or air_ordered:
                air_lines.append(
                    f"{i1}<i>{air_transferring} transferring, "
                    f"{air_ordered} ordered</i>"
                )
            g = breakdown["ground"]
            if g["total"]:
                ground_spawn_line = (
                    f"{i1}Ground spawns: {g['free']} free of {g['total']}"
                )
        else:
            air_lines.append(f"{i1}Helipads: {helipads}")
            if ground_spawn_parking:
                ground_spawn_line = f"{i1}Ground spawns: {ground_spawn_parking}"

        # Ground spawns are ground-start aircraft positions, so they live in the
        # Ground section (before ground units), per the agreed layout.
        ground_lines = ["<b>Ground</b>"]
        if ground_spawn_line is not None:
            ground_lines.append(ground_spawn_line)
        ground_lines += [
            f"{i1}Units: {self.cp.base.total_armor}{deployable_unit_info}",
            f"{i1}{allocated.total_transferring} en route, "
            f"{allocated.total_ordered} ordered",
        ]
        status_lines = [
            "<b>Status</b>",
            f"{i1}{self.cp.runway_status}",
            f"{i1}Ammo depots: {self.cp.active_ammo_depots_count}/"
            f"{self.cp.total_ammo_depots_count}",
            f"{i1}"
            + ("Factory can produce units" if self.cp.has_factory else "No factory"),
        ]
        self.intel_summary.setText("<br>".join(air_lines + ground_lines + status_lines))

    def generate_intel_tooltip(self) -> str:
        tooltip = (
            f"Deployable unit limit ({self.cp.frontline_unit_count_limit}) = {FREE_FRONTLINE_UNIT_SUPPLY} (base) + "
            f" {AMMO_DEPOT_FRONTLINE_UNIT_CONTRIBUTION} (per connected ammo depot) * {self.cp.total_ammo_depots_count} "
            f"(depots)"
        )

        if self.cp.has_active_frontline:
            unit_overage = max(
                self.cp.base.total_armor - self.cp.frontline_unit_count_limit, 0
            )
            tooltip += (
                f"\n{unit_overage} units will be held in reserve and will not be deployed to "
                f"connected frontlines for this turn"
            )

        return tooltip

    def closeEvent(self, close_event: QCloseEvent):
        GameUpdateSignal.get_instance().updateGame(self.game_model.game)

    def get_base_image(self):
        if (
            self.cp.cptype == ControlPointType.AIRCRAFT_CARRIER_GROUP
            or self.cp.cptype == ControlPointType.LHA_GROUP
        ):
            carrier_type = self.cp.get_carrier_group_type(always_supercarrier=True)
            return f"./resources/ui/units/ships/{carrier_type.id}.png"
        elif self.cp.cptype == ControlPointType.FOB and self.cp.has_helipads:
            return "./resources/ui/heliport.png"
        elif self.cp.cptype == ControlPointType.FOB:
            return "./resources/ui/fob.png"
        else:
            return "./resources/ui/airbase.png"

    def new_package(self) -> None:
        Dialog.open_new_package_dialog(self.cp, parent=self.window())

    def open_transfer_dialog(self) -> None:
        NewUnitTransferDialog(self.game_model, self.cp, parent=self.window()).show()

    def update_budget(self, game: Game) -> None:
        self.budget_display.setText(
            UnitTransactionFrame.BUDGET_FORMAT.format(game.blue.budget)
        )
