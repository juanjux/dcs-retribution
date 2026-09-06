import logging
from copy import deepcopy
from functools import partial
from typing import Callable, Iterator, Optional, Type

from PySide6.QtCore import (
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QRectF,
    QSize,
    Qt,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)
from dcs.unittype import FlyingType

from game.ato.flightplans.custom import CustomFlightPlan
from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.dcs.aircrafttype import AircraftType
from game.squadrons import morale as morale_rules
from game.squadrons.experience import turns_phrase
from game.purchaseadapter import AircraftPurchaseAdapter, TransactionError
from game.server import EventStream
from game.sim import GameUpdateEvents
from game.squadrons import Pilot, Squadron
from game.theater import ConflictTheater, ControlPoint, ParkingType
from game.squadrons.pilot import PilotStatus
from qt_ui.delegates import painter_context
from qt_ui.rankstars import (
    STAR_EMPTY,
    STAR_EMPTY_DIMMED,
    STAR_EMPTY_SELECTED,
    STAR_FILLED,
    STAR_FILLED_DIMMED,
    STAR_FILLED_SELECTED,
    paint_rank_stars,
)
from qt_ui.errorreporter import report_errors
from qt_ui.models import AtoModel, SquadronModel
from qt_ui.simcontroller import SimController
from qt_ui.uiconstants import AIRCRAFT_ICONS
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.widgets.combos.QSquadronLiverySelector import SquadronLiverySelector
from qt_ui.widgets.combos.primarytaskselector import PrimaryTaskSelector

#: Everything the redesign paints. The rest of the palette comes from the Air Wing
#: list, which these rows have to sit beside without looking like a different program.
ROW_SELECTED = "#1E3A52"
ROW_HOVERED = "#1A2A38"
ROW_SEPARATOR = "#1D2731"
BAR_HOVERED = "#3F5D73"
BAR_SELECTED = "#8FC3F0"

NAME = "#F2F7FA"
NAME_SELECTED = "#FFFFFF"
RANK_NAME = "#B7C6D2"
RANK_NAME_SELECTED = "#D3DFE8"
MUTED = "#8E9DAA"
MUTED_SELECTED = "#9FB3C2"
DIM = "#7C8B99"
DOT_SEPARATOR = "#4F6070"
DOT_SEPARATOR_SELECTED = "#6E93B0"

PLAYER_CHIP_FILL = "#22384A"
PLAYER_CHIP_TEXT = "#8FC3F0"

WARNING_ADVISORY = "#E0A86B"
WARNING_BLOCKING = "#D9645E"

AVAILABLE = "#5F8A6C"
AVAILABLE_SELECTED = "#9BD1AD"
WOUNDED = "#C08A72"
WOUNDED_SELECTED = "#E0A86B"
WOUNDED_DETAIL = "#8A6C5C"
ON_LEAVE = "#8FC3F0"
ON_LEAVE_SELECTED = "#BEDCF6"
ON_LEAVE_DETAIL = "#6E93B0"

#: The morale ramp, cold to hot, matching the states in :mod:`game.squadrons.morale`.
#: Normal is deliberately grey: a squadron that is holding up should read as quiet, and
#: colour should mean something is unusual.
MORALE_COLOURS = {
    "Triumphant": "#8FC3F0",
    "Confident": "#86C39A",
    "Normal": "#8E9DAA",
    "Shaken": "#E0A86B",
    "Shattered": "#D97B4F",
    "Broken": "#D9645E",
}
#: The label recedes further than the dot for a pilot nobody needs to think about.
MORALE_LABEL_OVERRIDE = {"Normal": "#B7C6D2"}
MORALE_LABEL_OVERRIDE_SELECTED = {"Normal": "#E4EDF4"}

FATE_CHIPS = {
    PilotStatus.Dead: ("KIA", "#3B2523", "#D9645E"),
    PilotStatus.Deserted: ("DESERTED", "#3B2D21", "#E0A86B"),
    PilotStatus.Discharged: ("DISCHARGED", "#26343F", "#9FADB9"),
}

#: The form ends here and the roster takes the rest of the window.
LEFT_PANEL_WIDTH = 574

PILOT_ROW_HEIGHT = 52
FALLEN_ROW_HEIGHT = 36

#: The left column ends here, and the notes column runs between these two.
COLUMN_A_RIGHT = 290
NOTES_LEFT = 300
NOTES_RIGHT = 430
MARGIN = 14


def _font(
    size: float, weight: QFont.Weight = QFont.Weight.Normal, mono: bool = False
) -> QFont:
    font = QFont("Consolas") if mono else QFont()
    font.setPixelSize(int(size))
    font.setWeight(weight)
    return font


class PilotRowPainter:
    """What both delegates share: a squadron, and the manners of the palette.

    Deliberately without an ``__init__``: Qt's own constructor walks the MRO, so a
    second one here would be called with no arguments. Each delegate sets the model.
    """

    squadron_model: SquadronModel

    @property
    def squadron(self) -> Squadron:
        return self.squadron_model.squadron

    @property
    def morale_in_play(self) -> bool:
        return bool(self.squadron.morale_in_play)

    def rank_of(self, pilot: Pilot) -> tuple[int, str]:
        """His rung, and what his own air force calls it."""
        rank = self.squadron.pilot_rank(pilot)
        level = morale_rules.rank_level(self.squadron.pilot_skill(pilot))
        return level, "" if rank is None else rank.name

    @staticmethod
    def missions_of(pilot: Pilot) -> tuple[str, str]:
        flown = pilot.record.missions_flown
        return str(flown), "mission" if flown == 1 else "missions"


class PilotDelegate(QStyledItemDelegate, PilotRowPainter):
    """One living pilot in three zones: who he is, what he needs, how he is.

    The right edge is always "how is this pilot", so it can be scanned down the list
    rather than read row by row.
    """

    def __init__(self, squadron_model: SquadronModel) -> None:
        super().__init__()
        self.squadron_model = squadron_model

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(0, PILOT_ROW_HEIGHT)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        pilot = self.squadron_model.pilot_at_index(index)
        rect = option.rect
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        with painter_context(painter):
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.translate(rect.topLeft())
            width = rect.width()

            if selected:
                painter.fillRect(0, 0, width, PILOT_ROW_HEIGHT, QColor(ROW_SELECTED))
                painter.fillRect(0, 0, 3, PILOT_ROW_HEIGHT, QColor(BAR_SELECTED))
            elif hovered:
                painter.fillRect(0, 0, width, PILOT_ROW_HEIGHT, QColor(ROW_HOVERED))
                painter.fillRect(0, 0, 3, PILOT_ROW_HEIGHT, QColor(BAR_HOVERED))
            painter.fillRect(0, 51, width, 1, QColor(ROW_SEPARATOR))

            self._paint_identity(painter, pilot, selected)
            self._paint_notes(painter, pilot)
            self._paint_state(painter, pilot, width, selected)

    # --- who he is ----------------------------------------------------------

    def _paint_identity(self, painter: QPainter, pilot: Pilot, selected: bool) -> None:
        painter.setFont(_font(14, QFont.Weight.DemiBold))
        metrics = painter.fontMetrics()
        chip_room = 62 if pilot.player else 0
        name = metrics.elidedText(
            pilot.name,
            Qt.TextElideMode.ElideRight,
            COLUMN_A_RIGHT - MARGIN - chip_room,
        )
        painter.setPen(QColor(NAME_SELECTED if selected else NAME))
        painter.drawText(MARGIN, 22, name)

        if pilot.player:
            self._paint_player_chip(
                painter, MARGIN + metrics.horizontalAdvance(name) + 8
            )

        # Line two: five slots of rank, the name his air force gives it, then what he
        # has flown. The stars are a bar you scan; the name is what he is called.
        level, rank_name = self.rank_of(pilot)
        x = float(MARGIN)
        x += paint_rank_stars(
            painter,
            x,
            42,
            level,
            filled=STAR_FILLED_SELECTED if selected else STAR_FILLED,
            empty=STAR_EMPTY_SELECTED if selected else STAR_EMPTY,
        )
        x += 6

        painter.setFont(_font(12))
        metrics = painter.fontMetrics()
        count, word = self.missions_of(pilot)
        tail = metrics.horizontalAdvance(f" · {count} {word}")
        if rank_name:
            rank_name = metrics.elidedText(
                rank_name,
                Qt.TextElideMode.ElideRight,
                max(0, int(COLUMN_A_RIGHT - x - tail)),
            )
            painter.setPen(QColor(RANK_NAME_SELECTED if selected else RANK_NAME))
            painter.drawText(int(x), 42, rank_name)
            x += metrics.horizontalAdvance(rank_name) + 6

        painter.setPen(QColor(DOT_SEPARATOR_SELECTED if selected else DOT_SEPARATOR))
        painter.drawText(int(x), 42, "·")
        x += metrics.horizontalAdvance("·") + 6

        painter.setFont(_font(12, mono=True))
        painter.setPen(QColor(MUTED_SELECTED if selected else MUTED))
        painter.drawText(int(x), 42, count)
        x += painter.fontMetrics().horizontalAdvance(count) + 4
        painter.setFont(_font(12))
        painter.setPen(QColor(MUTED_SELECTED if selected else DIM))
        painter.drawText(int(x), 42, word)

    def _paint_player_chip(self, painter: QPainter, x: float) -> None:
        """Almost every pilot is AI. Painting "AI" forty times is noise; this is not."""
        painter.setFont(_font(9.5, QFont.Weight.Bold))
        label = "PLAYER"
        width = painter.fontMetrics().horizontalAdvance(label) + 12
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PLAYER_CHIP_FILL))
        painter.drawRoundedRect(QRectF(x, 9, width, 16), 3, 3)
        painter.setPen(QColor(PLAYER_CHIP_TEXT))
        painter.drawText(QRectF(x, 9, width, 16), Qt.AlignmentFlag.AlignCenter, label)

    # --- what wants a decision ----------------------------------------------

    def _paint_notes(self, painter: QPainter, pilot: Pilot) -> None:
        note = self.note_for(pilot)
        if note is None:
            return
        text, colour = note
        painter.setPen(QColor(colour))
        painter.setFont(_font(11))
        painter.drawText(NOTES_LEFT, 30, "▲")
        x = NOTES_LEFT + painter.fontMetrics().horizontalAdvance("▲") + 6
        painter.setFont(_font(11.5))
        text = painter.fontMetrics().elidedText(
            text, Qt.TextElideMode.ElideRight, NOTES_RIGHT - x
        )
        painter.drawText(int(x), 30, text)

    def note_for(self, pilot: Pilot) -> Optional[tuple[str, str]]:
        """Anything the player could act on, never what the game has already decided.

        A wound is a state and lives under morale; a request for leave is a question
        addressed to the player, and belongs here.
        """
        if not self.morale_in_play:
            return None
        if pilot.refuses_to_fly:
            return "Will refuse to fly next mission", WARNING_BLOCKING
        if pilot.wants_leave:
            asked = pilot.leave_turns_requested
            return (
                (
                    f"Requests leave · {turns_phrase(asked)}"
                    if asked
                    else "Requests leave"
                ),
                WARNING_ADVISORY,
            )
        if (
            pilot.morale < pilot.morale_last_turn
            and morale_rules.morale_state(pilot.morale).severity
        ):
            return "Morale dropping — consider leave", WARNING_ADVISORY
        return None

    # --- how he is ----------------------------------------------------------

    def _paint_state(
        self, painter: QPainter, pilot: Pilot, width: int, selected: bool
    ) -> None:
        right = width - MARGIN
        if self.morale_in_play:
            state = morale_rules.morale_state(pilot.morale)
            dot = MORALE_COLOURS.get(state.name, MUTED)
            override = (
                MORALE_LABEL_OVERRIDE_SELECTED if selected else MORALE_LABEL_OVERRIDE
            )
            painter.setFont(_font(12, QFont.Weight.Medium))
            label_width = painter.fontMetrics().horizontalAdvance(state.name)
            painter.setPen(QColor(override.get(state.name, dot)))
            painter.drawText(int(right - label_width), 22, state.name)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(dot))
            painter.drawEllipse(QRectF(right - label_width - 14, 13, 8, 8))

        text, colour, detail, detail_colour = self._status_of(pilot, selected)
        painter.setFont(_font(11.5))
        metrics = painter.fontMetrics()
        full = f"{text} {detail}" if detail else text
        x = right - metrics.horizontalAdvance(full)
        painter.setPen(QColor(colour))
        painter.drawText(int(x), 42, text)
        if detail:
            painter.setPen(QColor(detail_colour))
            painter.drawText(int(x + metrics.horizontalAdvance(f"{text} ")), 42, detail)

    def _status_of(self, pilot: Pilot, selected: bool) -> tuple[str, str, str, str]:
        """What the game has decided about him. A wound outranks leave outranks fit."""
        if pilot.wounded:
            return (
                "Wounded",
                WOUNDED_SELECTED if selected else WOUNDED,
                f"· {turns_phrase(pilot.wounded_turns)} to recover",
                WOUNDED_DETAIL,
            )
        if pilot.on_leave:
            detail = (
                f"· {turns_phrase(pilot.leave_turns)} left" if pilot.leave_turns else ""
            )
            return (
                "On leave",
                ON_LEAVE_SELECTED if selected else ON_LEAVE,
                detail,
                ON_LEAVE_DETAIL,
            )
        return "Available", AVAILABLE_SELECTED if selected else AVAILABLE, "", ""


class FallenPilotDelegate(QStyledItemDelegate, PilotRowPainter):
    """A memorial and a record, not a working list: one line, and dim on purpose.

    It must not compete with the roster above it, and morale is dropped from these rows
    because it no longer means anything.
    """

    def __init__(self, squadron_model: SquadronModel) -> None:
        super().__init__()
        self.squadron_model = squadron_model

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(0, FALLEN_ROW_HEIGHT)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        pilot = self.squadron_model.pilot_at_index(index)
        rect = option.rect

        with painter_context(painter):
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.translate(rect.topLeft())
            width = rect.width()
            painter.fillRect(0, FALLEN_ROW_HEIGHT - 1, width, 1, QColor(ROW_SEPARATOR))

            painter.setFont(_font(13, QFont.Weight.DemiBold))
            painter.setPen(QColor(RANK_NAME))
            painter.drawText(MARGIN, 23, pilot.name)
            x = float(MARGIN + painter.fontMetrics().horizontalAdvance(pilot.name) + 8)

            level, rank_name = self.rank_of(pilot)
            x += paint_rank_stars(
                painter,
                x,
                23,
                level,
                filled=STAR_FILLED_DIMMED,
                empty=STAR_EMPTY_DIMMED,
            )
            if rank_name:
                x += 6
                painter.setFont(_font(12))
                painter.setPen(QColor(DIM))
                painter.drawText(int(x), 23, rank_name)

            count, word = self.missions_of(pilot)
            painter.setFont(_font(12, mono=True))
            painter.setPen(QColor(MUTED))
            painter.drawText(340, 23, count)
            after = 340 + painter.fontMetrics().horizontalAdvance(count) + 4
            painter.setFont(_font(12))
            painter.setPen(QColor(DIM))
            painter.drawText(after, 23, word)

            self._paint_fate(painter, pilot, width)

    @staticmethod
    def _paint_fate(painter: QPainter, pilot: Pilot, width: int) -> None:
        chip = FATE_CHIPS.get(pilot.status)
        if chip is None:
            return
        label, fill, text = chip
        painter.setFont(_font(10, QFont.Weight.Bold))
        chip_width = painter.fontMetrics().horizontalAdvance(label) + 16
        x = width - MARGIN - chip_width
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(fill))
        painter.drawRoundedRect(QRectF(x, 9, chip_width, 18), 4, 4)
        painter.setPen(QColor(text))
        painter.drawText(
            QRectF(x, 9, chip_width, 18), Qt.AlignmentFlag.AlignCenter, label
        )


class PilotList(QListView):
    """List view for displaying a squadron's pilots."""

    def __init__(self, squadron_model: SquadronModel, fallen: bool = False) -> None:
        super().__init__()
        self.squadron_model = squadron_model

        delegate: QStyledItemDelegate = (
            FallenPilotDelegate(squadron_model)
            if fallen
            else PilotDelegate(squadron_model)
        )
        self.setItemDelegate(delegate)
        self.setModel(self.squadron_model)
        self.selectionModel().setCurrentIndex(
            self.squadron_model.index(0, 0, QModelIndex()),
            QItemSelectionModel.SelectionFlag.Select,
        )

        # The rows light up under the cursor, which needs the view to follow it.
        self.setMouseTracking(True)
        self.setUniformItemSizes(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        if fallen:
            self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)


class AutoAssignedTaskControls(QVBoxLayout):
    """The mission types this squadron will be given without being asked.

    Seventeen of them stacked one per line ran the panel to some 560 px; three columns
    bring it to about 150, which is what lets the rest of the form fit beside the
    roster. All and None are here because setting sixteen of seventeen by hand is a
    chore nobody should have to do twice.
    """

    COLUMNS = 3

    def __init__(self, squadron_model: SquadronModel) -> None:
        super().__init__()
        self.squadron_model = squadron_model
        self.checkboxes: dict[FlightType, QCheckBox] = {}

        shortcuts = QHBoxLayout()
        shortcuts.setSpacing(6)
        for text, checked in (("All", True), ("None", False)):
            button = QPushButton(text)
            button.setStyleSheet(BUTTON_SECONDARY)
            button.setFixedHeight(22)
            button.clicked.connect(partial(self.set_every_task, checked))
            shortcuts.addWidget(button)
        shortcuts.addStretch()
        self.addLayout(shortcuts)

        def make_callback(toggled_task: FlightType) -> Callable[[bool], None]:
            def callback(checked: bool) -> None:
                self.on_toggled(toggled_task, checked)

            return callback

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(2)
        self.addLayout(grid)

        row = column = 0
        for task in FlightType:
            if not self.squadron_model.squadron.capable_of(task):
                continue
            checkbox = QCheckBox(text=task.value)
            checkbox.setChecked(squadron_model.is_auto_assignable(task))
            checkbox.toggled.connect(make_callback(task))
            grid.addWidget(checkbox, row, column)
            self.checkboxes[task] = checkbox
            column += 1
            if column == self.COLUMNS:
                column = 0
                row += 1

    def set_every_task(self, checked: bool) -> None:
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(checked)

    def on_toggled(self, task: FlightType, checked: bool) -> None:
        self.squadron_model.set_auto_assignable(task, checked)


class SquadronDestinationComboBox(QComboBox):
    def __init__(self, squadron: Squadron, theater: ConflictTheater) -> None:
        super().__init__()
        self.squadron = squadron
        self.theater = theater
        #: Bases with squadrons that don't fit, collected while building the
        #: combo so the dialog can show a single consolidated warning.
        self.parking_overflow: dict[str, list[tuple[Squadron, str]]] = {}

        parking_type = ParkingType().from_squadron(squadron)
        room = squadron.location.unclaimed_parking(parking_type)
        self.addItem(
            f"Remain at {squadron.location} (room for {room} more aircraft)",
            squadron.location,
        )
        selected_index: Optional[int] = None
        for idx, destination in enumerate(sorted(self.iter_destinations(), key=str), 1):
            if destination == squadron.destination:
                selected_index = idx
            room = self.calculate_parking_slots(
                destination, squadron.aircraft.dcs_unit_type
            )
            self.addItem(
                f"Transfer to {destination} (room for {room} more aircraft)",
                destination,
            )
            if room < squadron.owned_aircraft or room == 0:
                diff = squadron.owned_aircraft - room
                text = (
                    f"Transfer to {destination} not possible "
                    f"({diff} additional slots required)"
                )
                if squadron.owned_aircraft == 0 and room == 0:
                    text = (
                        f"Transfer to {destination} not possible "
                        f"(no fitting slots found)"
                    )
                self.setItemText(idx, text)
                self.model().item(idx).setEnabled(False)

        if squadron.destination is None:
            selected_index = 0

        if selected_index is not None:
            self.setCurrentIndex(selected_index)

    def iter_destinations(self) -> Iterator[ControlPoint]:
        size = self.squadron.expected_size_next_turn
        parking_type = ParkingType().from_squadron(self.squadron)
        for control_point in self.theater.control_points_for(self.squadron.player):
            if control_point == self.squadron.location:
                continue
            if not control_point.can_operate(self.squadron.aircraft):
                continue
            ac_type = self.squadron.aircraft.dcs_unit_type
            if (
                self.squadron.destination is not control_point
                and control_point.unclaimed_parking(parking_type) < size
                and self.calculate_parking_slots(control_point, ac_type) < size
            ):
                continue
            yield control_point

    def calculate_parking_slots(
        self, cp: ControlPoint, dcs_unit_type: Type[FlyingType]
    ) -> int:
        if cp.dcs_airport:
            ap = deepcopy(cp.dcs_airport)
            overflow = []

            parking_type = ParkingType(
                fixed_wing=False, fixed_wing_stol=False, rotary_wing=True
            )
            free_helicopter_slots = cp.total_aircraft_parking(parking_type)

            parking_type = ParkingType(
                fixed_wing=False, fixed_wing_stol=True, rotary_wing=False
            )
            free_ground_spawns = cp.total_aircraft_parking(parking_type)

            # Squadrons whose parking must be reserved at this base next turn:
            # every squadron currently based here (outgoing transfers included —
            # they may need to return if the destination is captured this turn)
            # plus any squadrons relocating in.
            occupants = list(cp.squadrons)
            occupants += [
                s for s in cp.coalition.air_wing.iter_squadrons() if s.destination == cp
            ]
            for s in occupants:
                for count in range(s.owned_aircraft):
                    is_heli = s.aircraft.helicopter
                    is_vtol = not is_heli and s.aircraft.lha_capable
                    count_ground_spawns = (
                        s.aircraft.flyable
                        or cp.coalition.game.settings.ground_start_ai_planes
                    )

                    if free_helicopter_slots > 0 and is_heli:
                        free_helicopter_slots -= 1
                    elif free_ground_spawns > 0 and (
                        is_heli or is_vtol or count_ground_spawns
                    ):
                        free_ground_spawns -= 1
                    else:
                        slot = ap.free_parking_slot(s.aircraft.dcs_unit_type)
                        if slot:
                            slot.unit_id = id(s) + count
                        else:
                            if s.aircraft.helicopter:
                                pk_label = "rotary-wing"
                            elif s.aircraft.lha_capable:
                                pk_label = "STOL/ground-spawn"
                            else:
                                pk_label = "fixed-wing"
                            overflow.append((s, pk_label))
                            break
            if overflow:
                self.parking_overflow[cp.name] = list(overflow)
            else:
                self.parking_overflow.pop(cp.name, None)
            return (
                len(ap.free_parking_slots(dcs_unit_type))
                + free_helicopter_slots
                + free_ground_spawns
            )
        else:
            parking_type = ParkingType().from_aircraft(
                next(AircraftType.for_dcs_type(dcs_unit_type)),
                cp.coalition.game.settings.ground_start_ai_planes,
            )
            return cp.unclaimed_parking(parking_type)


#: The left panel is a form, and a form reads better when its labels get out of the
#: way. Small, spaced, upper case, and the colour of a caption rather than a heading.
SECTION_LABEL_STYLE = (
    "font-size: 11px; font-weight: bold; letter-spacing: 1px; color: #6B7A87;"
)
TILE_STYLE = "background: #26343F; border: 1px solid #1D2731; border-radius: 3px;"
BUTTON_SECONDARY = (
    "QPushButton { height: 30px; font-size: 12px; font-weight: 600;"
    " background: #26343F; border: 1px solid #3A4B5C; border-radius: 3px;"
    " color: #D3DFE8; padding: 0 12px; }"
    "QPushButton:disabled { background: #202B36; border-color: #2F3D4B; color: #5F6F7D; }"
)
BUTTON_PRIMARY = (
    "QPushButton { height: 30px; font-size: 12px; font-weight: 600;"
    " background: #8FC3F0; border: none; border-radius: 3px; color: #0F1922;"
    " padding: 0 12px; }"
    "QPushButton:disabled { background: #202B36; color: #5F6F7D; }"
)
BUTTON_DESTRUCTIVE = (
    "QPushButton { height: 30px; font-size: 12px; font-weight: 600;"
    " background: #A8443F; border: none; border-radius: 3px; color: #FFFFFF;"
    " padding: 0 12px; }"
    "QPushButton:hover { background: #BF4F49; }"
    "QPushButton:disabled { background: #202B36; color: #5F6F7D; }"
)

#: The five figures of the inventory, in the order they are read: what you have, what
#: is coming, what you lost, what you paid for, what you started with.
INVENTORY_TILES = (
    ("CURRENT", "owned_aircraft", "#F2F7FA"),
    ("ON ORDER", "pending_deliveries", "#E0A86B"),
    ("DESTROYED", "destroyed_aircraft", "#C08A72"),
    ("PURCHASED", "purchased_aircraft", "#B7C6D2"),
    ("INITIAL", "initial_aircraft", "#8E9DAA"),
)


def _section_label(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setStyleSheet(SECTION_LABEL_STYLE)
    return label


class SquadronDialog(QDialog):
    """Dialog window showing a squadron."""

    def __init__(
        self,
        ato_model: AtoModel,
        squadron_model: SquadronModel,
        theater: ConflictTheater,
        sim_controller: SimController,
        parent,
    ) -> None:
        super().__init__(parent)
        self.ato_model = ato_model
        self.squadron_model = squadron_model
        # The main list (and the action buttons) operate on living pilots only;
        # dead pilots get their own read-only list below.
        self.squadron_model.pilot_filter = "living"
        self.dead_squadron_model = SquadronModel(
            squadron_model.squadron, pilot_filter="dead"
        )
        self.sim_controller = sim_controller
        self.theater = theater
        self._child_dialogs: list[QDialog] = []

        self.setMinimumSize(1200, 760)
        self.setWindowTitle(f"Squadron — {squadron_model.squadron}")
        # TODO: self.setWindowIcon()

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)
        self.setLayout(layout)

        columns = QHBoxLayout()
        columns.setSpacing(18)
        layout.addLayout(columns, stretch=1)

        left_column = QVBoxLayout()
        left_column.setSpacing(8)
        left_column.setContentsMargins(0, 0, 0, 0)
        # Boxed and pinned: a livery name can run to sixty characters, and left to
        # itself the form would take half the window from the roster.
        left_panel = QWidget()
        left_panel.setLayout(left_column)
        left_panel.setFixedWidth(LEFT_PANEL_WIDTH)
        columns.addWidget(left_panel, stretch=0)

        left_column.addLayout(self._build_header())

        left_column.addWidget(_section_label("Primary task"))
        self.primary_task_selector = PrimaryTaskSelector.for_squadron(
            self.squadron_model.squadron
        )
        self.primary_task_selector.currentIndexChanged.connect(
            self.on_task_index_changed
        )
        left_column.addWidget(self.primary_task_selector)

        left_column.addWidget(_section_label("Livery"))
        self.livery_selector = SquadronLiverySelector(self.squadron_model.squadron)
        left_column.addWidget(self.livery_selector)

        left_column.addWidget(_section_label("Aircraft inventory"))
        self.inventory_tiles: dict[str, QLabel] = {}
        left_column.addLayout(self._build_inventory_tiles())

        # Buying aircraft is only meaningful for the player's own squadrons.
        if self.squadron.player.is_blue:
            self.purchase_adapter: AircraftPurchaseAdapter = AircraftPurchaseAdapter(
                self.squadron.location
            )

            purchase_row = QHBoxLayout()
            purchase_row.setSpacing(6)
            self.sell_aircraft_button = QPushButton("−")
            self.sell_aircraft_button.setProperty("style", "btn-sell")
            self.sell_aircraft_button.setFixedSize(28, 28)
            self.sell_aircraft_button.clicked.connect(self.sell_aircraft)
            purchase_row.addWidget(self.sell_aircraft_button)

            self.on_order_label = QLabel()
            self.on_order_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.on_order_label.setFixedWidth(44)
            self.on_order_label.setStyleSheet(
                "background: #14202B; border: 1px solid #3A4B5C; border-radius: 3px;"
                " padding: 4px 0; font-size: 13px;"
            )
            purchase_row.addWidget(self.on_order_label)

            self.buy_aircraft_button = QPushButton("+")
            self.buy_aircraft_button.setProperty("style", "btn-buy")
            self.buy_aircraft_button.setFixedSize(28, 28)
            self.buy_aircraft_button.clicked.connect(self.buy_aircraft)
            purchase_row.addWidget(self.buy_aircraft_button)

            self.price_label = QLabel()
            self.price_label.setStyleSheet("font-size: 12px; color: #8E9DAA;")
            purchase_row.addWidget(self.price_label)
            purchase_row.addStretch()
            left_column.addLayout(purchase_row)

            self.parking_slots_label = QLabel()
            self.parking_slots_label.setStyleSheet("font-size: 12px; color: #7C8B99;")
            left_column.addWidget(self.parking_slots_label)

            self._refresh_aircraft_controls()

        left_column.addWidget(_section_label("Auto-assignable mission types"))
        self.auto_assigned_tasks = AutoAssignedTaskControls(squadron_model)
        left_column.addLayout(self.auto_assigned_tasks)

        # Pinned to the bottom of the panel so it does not float mid-form.
        left_column.addStretch()
        left_column.addWidget(_section_label("Base"))
        self.transfer_destination = SquadronDestinationComboBox(
            squadron_model.squadron, theater
        )
        self.transfer_destination.currentIndexChanged.connect(
            self.on_destination_changed
        )
        left_column.addWidget(self.transfer_destination)

        right_column = QVBoxLayout()
        right_column.setSpacing(6)
        columns.addLayout(right_column, stretch=1)

        right_column.addLayout(self._build_roster_header())
        right_column.addWidget(self._build_column_headers())

        self.pilot_list = PilotList(squadron_model)
        self.pilot_list.selectionModel().selectionChanged.connect(
            self.on_selection_changed
        )
        right_column.addWidget(self.pilot_list, stretch=3)

        right_column.addWidget(_section_label("KIA & discharged"))
        self.dead_pilot_list = PilotList(self.dead_squadron_model, fallen=True)
        right_column.addWidget(self.dead_pilot_list, stretch=1)

        # Under the roster, not under the aircraft: these all act on a pilot.
        right_column.addLayout(self._build_buttons())

        self._warn_parking_overflow()

    # --- the panels ---------------------------------------------------------

    def _build_header(self) -> QHBoxLayout:
        """Identity on the left, context on the right, two lines each.

        The aircraft is the title because that is what a squadron is; the name and its
        nickname sit under it, and where it flies from reads on the right.
        """
        squadron = self.squadron
        row = QHBoxLayout()
        row.setSpacing(12)

        icon_name = squadron.aircraft.dcs_id.replace("/", "_")
        pixmap = AIRCRAFT_ICONS.get(icon_name)
        if pixmap is not None:
            silhouette = QLabel()
            silhouette.setPixmap(pixmap)
            silhouette.setFixedSize(91, 24)
            silhouette.setScaledContents(True)
            row.addWidget(silhouette, alignment=Qt.AlignmentFlag.AlignTop)

        identity = QVBoxLayout()
        identity.setSpacing(2)
        row.addLayout(identity)

        type_row = QHBoxLayout()
        type_row.setSpacing(6)
        name = QLabel(squadron.aircraft.display_name)
        name.setStyleSheet("font-size: 20px; font-weight: 600; color: #F2F7FA;")
        type_row.addWidget(name)
        variant = squadron.aircraft.variant_id
        if variant and variant != squadron.aircraft.display_name:
            variant_label = QLabel(variant)
            variant_label.setStyleSheet("font-size: 13px; color: #8E9DAA;")
            type_row.addWidget(variant_label, alignment=Qt.AlignmentFlag.AlignBottom)
        type_row.addStretch()
        identity.addLayout(type_row)

        second = QHBoxLayout()
        second.setSpacing(6)
        squadron_name = QLabel(squadron.name)
        squadron_name.setStyleSheet("font-size: 13px; color: #B7C6D2;")
        second.addWidget(squadron_name)
        if squadron.nickname:
            nickname = QLabel(f"“{squadron.nickname}”")
            nickname.setStyleSheet("font-size: 13px; color: #7C8B99;")
            second.addWidget(nickname)
        second.addStretch()
        identity.addLayout(second)

        context = QVBoxLayout()
        context.setSpacing(2)
        row.addLayout(context)
        task = QLabel(squadron.primary_task.value.upper())
        task.setStyleSheet(
            "font-size: 10px; font-weight: bold; letter-spacing: 0.8px;"
            " color: #8FC3F0; background: #22384A; border-radius: 3px;"
            " padding: 3px 8px;"
        )
        context.addWidget(task, alignment=Qt.AlignmentFlag.AlignRight)
        base = QLabel(str(squadron.location))
        base.setStyleSheet("font-size: 13px; color: #8E9DAA;")
        context.addWidget(base, alignment=Qt.AlignmentFlag.AlignRight)
        return row

    def _build_inventory_tiles(self) -> QHBoxLayout:
        """Five figures instead of four lines of prose: they are read, not parsed."""
        row = QHBoxLayout()
        row.setSpacing(6)
        for label, attribute, colour in INVENTORY_TILES:
            tile = QVBoxLayout()
            tile.setSpacing(0)
            value = QLabel(str(getattr(self.squadron, attribute)))
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value.setStyleSheet(
                f"font-family: Consolas, monospace; font-size: 20px;"
                f" font-weight: 600; color: {colour};"
            )
            caption = QLabel(label)
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setStyleSheet("font-size: 10px; color: #7C8B99;")
            tile.addWidget(value)
            tile.addWidget(caption)

            holder = QWidget()
            holder.setLayout(tile)
            holder.setFixedHeight(64)
            holder.setStyleSheet(TILE_STYLE)
            row.addWidget(holder)
            self.inventory_tiles[attribute] = value
        return row

    def _build_roster_header(self) -> QHBoxLayout:
        """How many pilots, and the shape of them, before you scroll anything."""
        row = QHBoxLayout()
        row.addWidget(_section_label("Pilots"))
        self.roster_summary = QLabel()
        self.roster_summary.setStyleSheet("font-size: 12px; color: #8E9DAA;")
        row.addWidget(self.roster_summary)
        row.addStretch()
        self._refresh_roster_summary()
        return row

    def _refresh_roster_summary(self) -> None:
        pilots = self.squadron.living_pilots
        wounded = sum(1 for p in pilots if p.wounded)
        on_leave = sum(1 for p in pilots if p.on_leave)
        available = len(pilots) - wounded - on_leave
        parts = [f"<b>{len(pilots)}</b>", f"{available} available"]
        if wounded:
            parts.append(f"{wounded} wounded")
        if on_leave:
            parts.append(f"{on_leave} on leave")
        self.roster_summary.setText(" · ".join(parts))

    @staticmethod
    def _build_column_headers() -> QWidget:
        header = QWidget()
        header.setFixedHeight(22)
        header.setStyleSheet("background: #1B2732;")
        row = QHBoxLayout()
        row.setContentsMargins(MARGIN, 0, MARGIN, 0)
        header.setLayout(row)
        for text, stretch, align in (
            ("PILOT", 0, Qt.AlignmentFlag.AlignLeft),
            ("NOTES", 1, Qt.AlignmentFlag.AlignLeft),
            ("MORALE / STATUS", 0, Qt.AlignmentFlag.AlignRight),
        ):
            label = _section_label(text)
            row.addWidget(label, stretch, align)
        return header

    def _build_buttons(self) -> QHBoxLayout:
        """Discharge is set apart: a fast click on Rename must never land on it."""
        panel = QHBoxLayout()
        panel.setSpacing(8)
        panel.setContentsMargins(0, 6, 0, 0)

        self.discharge_button = QPushButton("Discharge")
        self.discharge_button.setStyleSheet(BUTTON_DESTRUCTIVE)
        self.discharge_button.clicked.connect(self.discharge_pilot)
        panel.addWidget(self.discharge_button)
        panel.addSpacing(24)
        panel.addStretch()

        self.rename_button = QPushButton("Rename")
        self.rename_button.setStyleSheet(BUTTON_SECONDARY)
        self.rename_button.clicked.connect(self.rename_pilot)
        panel.addWidget(self.rename_button)

        self.toggle_ai_button = QPushButton()
        self.toggle_ai_button.setStyleSheet(BUTTON_SECONDARY)
        self.toggle_ai_button.clicked.connect(self.toggle_ai)
        panel.addWidget(self.toggle_ai_button)

        self.toggle_leave_button = QPushButton()
        self.toggle_leave_button.setStyleSheet(BUTTON_PRIMARY)
        self.toggle_leave_button.clicked.connect(self.toggle_leave)
        panel.addWidget(self.toggle_leave_button)

        self.reset_button_states(self.pilot_list.currentIndex())
        return panel

    def _warn_parking_overflow(self) -> None:
        overflow = self.transfer_destination.parking_overflow
        if not overflow:
            return
        self._overflow_squadrons: dict[str, Squadron] = {}
        lines = [
            "Insufficient parking space was detected at the following "
            "bases:<br/><br/>"
        ]
        for cp_name, entries in overflow.items():
            lines.append(f"<b>{cp_name}</b>:<br/>")
            for s, pk_label in entries:
                href = str(s.id)
                self._overflow_squadrons[href] = s
                lines.append(
                    f'&nbsp;&nbsp;<a href="{href}"><b><u>{s.name}</u></b></a>'
                    f" - {s.aircraft.variant_id} "
                    f"(no free {pk_label} parking space)<br/>"
                )
            lines.append("<br/>")
        lines.append(
            "Consider moving these squadrons to a different airfield to "
            "avoid possible air-starts."
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Insufficient parking space detected!")
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        layout = QVBoxLayout()

        label = QLabel("".join(lines))
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        label.setOpenExternalLinks(False)
        # Default Qt link blue is nearly unreadable on the dark theme.
        link_palette = label.palette()
        link_palette.setColor(QPalette.ColorRole.Link, QColor("#E0E0E0"))
        label.setPalette(link_palette)
        label.linkActivated.connect(self._open_overflow_squadron)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(label)
        layout.addWidget(scroll)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.close)
        layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignRight)

        dialog.setLayout(layout)
        dialog.resize(520, 360)
        self._parking_warning = dialog
        dialog.show()

    def _open_overflow_squadron(self, href: str) -> None:
        squadron = self._overflow_squadrons.get(href)
        if squadron is None:
            return
        dialog = SquadronDialog(
            self.ato_model,
            SquadronModel(squadron),
            self.theater,
            self.sim_controller,
            self,
        )
        self._child_dialogs.append(dialog)
        dialog.show()

    @property
    def squadron(self) -> Squadron:
        return self.squadron_model.squadron

    @staticmethod
    def _purchase_amount() -> int:
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.ShiftModifier:
            return 10
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            return 5
        return 1

    def _refresh_aircraft_controls(self) -> None:
        for attribute, tile in self.inventory_tiles.items():
            tile.setText(str(getattr(self.squadron, attribute)))
        self.on_order_label.setText(str(self.squadron.pending_deliveries))
        self.price_label.setText(
            f"order aircraft · ${self.purchase_adapter.price_of(self.squadron)}M"
        )
        parking_type = ParkingType().from_squadron(self.squadron)
        free_slots = self.squadron.location.unclaimed_parking(parking_type)
        self.parking_slots_label.setText(
            f"{free_slots} parking "
            f"{'slot' if free_slots == 1 else 'slots'} free at "
            f"{self.squadron.location}"
        )
        can_buy = self.purchase_adapter.can_buy(self.squadron)
        self.buy_aircraft_button.setEnabled(can_buy)
        self.buy_aircraft_button.setToolTip(
            "Buy aircraft. Use Shift or Ctrl to buy 10 or 5 at once."
            if can_buy
            else "Cannot buy: insufficient budget, parking or squadron capacity."
        )
        can_sell = self.purchase_adapter.can_sell_or_cancel(self.squadron)
        self.sell_aircraft_button.setEnabled(can_sell)
        self.sell_aircraft_button.setToolTip(
            "Sell aircraft. Use Shift or Ctrl to sell 10 or 5 at once."
            if can_sell
            else "Cannot sell: no idle aircraft or pending orders."
        )

    def buy_aircraft(self) -> None:
        try:
            self.purchase_adapter.buy(self.squadron, self._purchase_amount())
        except TransactionError as ex:
            logging.exception("Aircraft purchase failed")
            QMessageBox.warning(
                self, "Purchase failed", str(ex), QMessageBox.StandardButton.Ok
            )
        finally:
            self._refresh_aircraft_controls()
            GameUpdateSignal.get_instance().updateBudget(self.ato_model.game)

    def sell_aircraft(self) -> None:
        try:
            self.purchase_adapter.sell(self.squadron, self._purchase_amount())
        except TransactionError as ex:
            logging.exception("Aircraft sale failed")
            QMessageBox.warning(
                self, "Sale failed", str(ex), QMessageBox.StandardButton.Ok
            )
        finally:
            self._refresh_aircraft_controls()
            GameUpdateSignal.get_instance().updateBudget(self.ato_model.game)

    def _instant_relocate(self, destination: ControlPoint) -> None:
        self.squadron.relocate_to(destination)
        for _, f in self.squadron.flight_db.objects.items():
            if f.squadron == self.squadron:
                if isinstance(f.flight_plan, CustomFlightPlan):
                    for wpt in f.flight_plan.waypoints:
                        if wpt.waypoint_type == FlightWaypointType.LANDING_POINT:
                            wpt.control_point = destination
                            wpt.position = wpt.control_point.position
                            break
                f.recreate_flight_plan()
                EventStream.put_nowait(GameUpdateEvents().update_flight(f))

    def on_destination_changed(self, index: int) -> None:
        with report_errors("Could not change squadron destination", self):
            destination = self.transfer_destination.itemData(index)
            if destination is self.squadron.location:
                self.squadron.cancel_relocation()
            elif self.ato_model.game.settings.enable_transfer_cheat:
                self._instant_relocate(destination)
            else:
                self.squadron.plan_relocation(
                    destination, self.sim_controller.current_time_in_sim
                )
            self.ato_model.replace_from_game(player=True)

    def reset_button_states(self, index: QModelIndex) -> None:
        """Every button follows the selection, and says why when it cannot act."""
        pilot = self.squadron_model.pilot_at_index(index) if index.isValid() else None
        self.rename_button.setEnabled(pilot is not None)
        self.discharge_button.setEnabled(pilot is not None and pilot.alive)
        self.reset_ai_toggle_state(index)
        self.reset_leave_toggle_state(index)

    def check_disabled_button_states(
        self, button: QPushButton, index: QModelIndex
    ) -> bool:
        if not index.isValid():
            button.setText("No pilot selected")
            button.setDisabled(True)
            return True
        pilot = self.squadron_model.pilot_at_index(index)
        if not pilot.alive:
            button.setText("Pilot is gone")
            button.setDisabled(True)
            return True
        if pilot.wounded:
            # He is already off the roster and comes back on his own schedule.
            button.setText(f"Wounded for {turns_phrase(pilot.wounded_turns)}")
            button.setDisabled(True)
            return True
        return False

    def rename_pilot(self) -> None:
        index = self.pilot_list.currentIndex()
        if not index.isValid():
            logging.error("Cannot toggle player/AI: no pilot is selected")
            return
        p = self.squadron_model.pilot_at_index(index)
        text, ok = QInputDialog.getText(
            self, "Rename pilot", "New name: ", QLineEdit.EchoMode.Normal
        )
        if ok:
            p.name = text

    def toggle_ai(self) -> None:
        index = self.pilot_list.currentIndex()
        if not index.isValid():
            logging.error("Cannot toggle player/AI: no pilot is selected")
            return
        self.squadron_model.toggle_ai_state(index)

    def reset_ai_toggle_state(self, index: QModelIndex) -> None:
        if self.check_disabled_button_states(self.toggle_ai_button, index):
            return
        if not self.squadron_model.squadron.aircraft.flyable:
            self.toggle_ai_button.setText("Not flyable")
            self.toggle_ai_button.setDisabled(True)
            return
        self.toggle_ai_button.setEnabled(True)
        pilot = self.squadron_model.pilot_at_index(index)
        self.toggle_ai_button.setText(
            "Convert to AI" if pilot.player else "Convert to player"
        )

    def toggle_leave(self) -> None:
        index = self.pilot_list.currentIndex()
        if not index.isValid():
            logging.error("Cannot toggle on leave state: no pilot is selected")
            return
        self.squadron_model.toggle_leave_state(index)

    def reset_leave_toggle_state(self, index: QModelIndex) -> None:
        if self.check_disabled_button_states(self.toggle_leave_button, index):
            return
        pilot = self.squadron_model.pilot_at_index(index)
        self.toggle_leave_button.setEnabled(
            not pilot.on_leave or self.squadron_model.squadron.has_unfilled_pilot_slots
        )
        self.toggle_leave_button.setText(
            "Cancel leave" if pilot.on_leave else "Send on leave"
        )
        cost = abs(morale_rules.LEAVE_CANCELLED.amount(self.squadron.settings))
        self.toggle_leave_button.setToolTip(
            f"He loses {cost} morale for being called back early."
            if pilot.on_leave
            else ""
        )

    def discharge_pilot(self) -> None:
        """Throw a pilot out. Asked about first: there is no getting him back."""
        index = self.pilot_list.currentIndex()
        if not index.isValid():
            logging.error("Cannot discharge: no pilot is selected")
            return
        pilot = self.squadron_model.pilot_at_index(index)
        rank = self.squadron.pilot_rank(pilot)
        addressed = pilot.name if rank is None else f"{rank.abbreviation} {pilot.name}"
        answer = QMessageBox.question(
            self,
            "Discharge pilot",
            f"Discharge {addressed} from {self.squadron}? "
            "He leaves the squadron for good.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.squadron_model.discharge_pilot(index)
        self.dead_squadron_model.beginResetModel()
        self.dead_squadron_model.endResetModel()
        self._refresh_roster_summary()
        self.reset_button_states(self.pilot_list.currentIndex())

    def on_selection_changed(
        self, selected: QItemSelection, _deselected: QItemSelection
    ) -> None:
        indexes = selected.indexes()
        if not indexes:
            return
        self.reset_button_states(indexes[0])

    def on_task_index_changed(self, index: int) -> None:
        task = self.primary_task_selector.itemData(index)
        if task is None:
            raise RuntimeError("Selected task cannot be None")
        self.squadron.primary_task = task
