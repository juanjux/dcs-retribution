import json
import logging
import textwrap
import zipfile
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from PySide6 import QtWidgets
from PySide6.QtCore import QItemSelectionModel, QPoint, QSize, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel, QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListView,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

import qt_ui.uiconstants as CONST
from game.game import Game
from game.theater import Player
from game.persistency import settings_dir
from game.server import EventStream
from game.settings import (
    BooleanOption,
    BoundedFloatOption,
    BoundedIntOption,
    ChoicesOption,
    MinutesOption,
    OptionDescription,
    Settings,
    TextOption,
)
from game.settings.ISettingsContainer import SettingsContainer
from game.settings.settings import (
    LIVE_PILOTS_RANKS_SECTION,
    LIVE_PILOTS_PAGE,
    OPFOR_AI_SECTION,
)
from game.squadrons.pilotranks import RANK_NAMES_CUSTOM, ranks_for
from game.weather.cloudpresetpacks import apply_cloud_preset_pack
from game.sim import GameUpdateEvents
from qt_ui.widgets.QLabeledWidget import QLabeledWidget
from qt_ui.widgets.spinsliders import FloatSpinSlider, TimeInputs
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.settings.plugins import PluginOptionsPage, PluginsPage


class CheatSettingsBox(QGroupBox):
    def __init__(
        self, sc: SettingsContainer, apply_settings: Callable[[], None]
    ) -> None:
        super().__init__("Cheat Settings")
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Frontline
        self.frontline_cheat_checkbox = QCheckBox()
        self.frontline_cheat_checkbox.setChecked(sc.settings.enable_frontline_cheats)
        self.frontline_cheat_checkbox.toggled.connect(apply_settings)
        self.frontline_cheat = QLabeledWidget(
            "Enable Frontline Cheats:", self.frontline_cheat_checkbox
        )
        self.main_layout.addLayout(self.frontline_cheat)

        # Base capture
        self.base_capture_cheat_checkbox = QCheckBox()
        self.base_capture_cheat_checkbox.setChecked(
            sc.settings.enable_base_capture_cheat
        )
        self.base_capture_cheat_checkbox.toggled.connect(apply_settings)
        self.base_capture_cheat = QLabeledWidget(
            "Enable Base Capture Cheat:", self.base_capture_cheat_checkbox
        )
        self.main_layout.addLayout(self.base_capture_cheat)

        # Runway state
        self.base_runway_state_cheat_checkbox = QCheckBox()
        self.base_runway_state_cheat_checkbox.setChecked(
            sc.settings.enable_runway_state_cheat
        )
        self.base_runway_state_cheat_checkbox.toggled.connect(apply_settings)
        self.main_layout.addLayout(
            QLabeledWidget(
                "Enable Runway State Cheat:", self.base_runway_state_cheat_checkbox
            )
        )

        # Instant transfer
        self.transfer_cheat_checkbox = QCheckBox()
        self.transfer_cheat_checkbox.setChecked(sc.settings.enable_transfer_cheat)
        self.transfer_cheat_checkbox.toggled.connect(apply_settings)
        self.transfer_cheat = QLabeledWidget(
            "Enable Instant Squadron Transfer Cheat:", self.transfer_cheat_checkbox
        )
        self.main_layout.addLayout(self.transfer_cheat)

        # Air wing adjustments
        self.air_wing_adjustments_checkbox = QCheckBox()
        self.air_wing_adjustments_checkbox.setChecked(
            sc.settings.enable_air_wing_adjustments
        )
        self.air_wing_adjustments_checkbox.toggled.connect(apply_settings)
        self.air_wing_cheat = QLabeledWidget(
            "Enable Air Wing adjustments:", self.air_wing_adjustments_checkbox
        )
        self.main_layout.addLayout(self.air_wing_cheat)

        # Buy/Sell actions for OPFOR
        self.opfor_buysell_checkbox = QCheckBox()
        self.opfor_buysell_checkbox.setChecked(sc.settings.enable_enemy_buy_sell)
        self.opfor_buysell_checkbox.toggled.connect(apply_settings)
        self.redfor_buysell_cheat = QLabeledWidget(
            "Enable OPFOR Buy/Sell actions Cheat:", self.opfor_buysell_checkbox
        )
        self.main_layout.addLayout(self.redfor_buysell_cheat)

    @property
    def show_frontline_cheat(self) -> bool:
        return self.frontline_cheat_checkbox.isChecked()

    @property
    def show_base_capture_cheat(self) -> bool:
        return self.base_capture_cheat_checkbox.isChecked()

    @property
    def show_transfer_cheat(self) -> bool:
        return self.transfer_cheat_checkbox.isChecked()

    @property
    def enable_runway_state_cheat(self) -> bool:
        return self.base_runway_state_cheat_checkbox.isChecked()

    @property
    def enable_air_wing_cheats(self) -> bool:
        return self.air_wing_adjustments_checkbox.isChecked()

    @property
    def enable_redfor_buysell(self) -> bool:
        return self.opfor_buysell_checkbox.isChecked()


class AutoSettingsLayout(QGridLayout):
    def __init__(
        self,
        page: str,
        section: str,
        sc: SettingsContainer,
        write_full_settings: Callable[[], None],
    ) -> None:
        super().__init__()
        self.page = page
        self.section = section
        self.sc = sc
        self.write_full_settings = write_full_settings
        self.settings_map: Dict[str, QWidget] = {}
        self.label_map: Dict[str, QWidget] = {}
        #: Set by the page once every group exists. A setting can hide one in
        #: another group, so a change here has to re-evaluate the whole page.
        self.on_settings_changed: Optional[Callable[[], None]] = None
        #: Extra work a hand-built section needs doing whenever a value changes.
        self.refresh_hooks: List[Callable[[], None]] = []
        self._rank_rows: List[Tuple[QLineEdit, QLineEdit]] = []
        self._rank_names: List[Tuple[str, str]] = []

        self.init_ui()

    def init_ui(self):
        if self.section == LIVE_PILOTS_RANKS_SECTION:
            self._build_rank_grid()
            return
        for row, (name, description) in enumerate(
            Settings.fields(self.page, self.section)
        ):
            self.label_map[name] = self.add_label(row, description)
            if isinstance(description, BooleanOption):
                self.add_checkbox_for(row, name, description)
            elif isinstance(description, ChoicesOption):
                self.add_combobox_for(row, name, description)
            elif isinstance(description, BoundedFloatOption):
                self.add_float_spin_slider_for(row, name, description)
            elif isinstance(description, BoundedIntOption):
                self.add_spinner_for(row, name, description)
            elif isinstance(description, MinutesOption):
                self.add_duration_controls_for(row, name, description)
            elif isinstance(description, TextOption):
                self.add_line_edit_for(row, name, description)
            else:
                raise TypeError(f"Unhandled option type: {description}")
        self.apply_visibility()
        if self.section == OPFOR_AI_SECTION:
            self._wire_opfor_ai()
        if self.page == LIVE_PILOTS_PAGE:
            self._wire_dependents(
                "live_pilots_enabled",
                (
                    "live_pilots_show_names",
                    "live_pilots_show_ranks",
                ),
            )

    def _build_rank_grid(self) -> None:
        """The rank ladder: five rungs, short and full form side by side.

        Not one setting per row like every other section. Ten rows reading "Cadet
        (short)", "Cadet (full)" is a form to fill in; a rung per row under two column
        headings is a ladder you can read down.
        """
        row = 0
        for name, description in Settings.fields(self.page, self.section):
            if isinstance(description, ChoicesOption):
                # The naming choice belongs at the head of the ladder it names.
                self.label_map[name] = self.add_label(row, description)
                self.add_combobox_for(row, name, description)
                self._rank_combo = self.settings_map[name]
                self.removeWidget(self._rank_combo)
                self.addWidget(self._rank_combo, row, 1, 1, 2)
                row += 1
                continue
            if not name.endswith("_short"):
                continue
            if not self._rank_rows:
                self.addWidget(QLabel("<b>Short</b>"), row, 1)
                self.addWidget(QLabel("<b>Full</b>"), row, 2)
                row += 1
            full_name = name[: -len("_short")] + "_full"
            label = QLabel(f"<strong>{description.text}</strong>")
            self.addWidget(label, row, 0)
            # One label serves both boxes, so both names have to find it.
            self.label_map[name] = label
            self.label_map[full_name] = label

            max_length = getattr(description, "max_length", None)
            short = self._rank_edit(name, 60, max_length)
            full = self._rank_edit(full_name, 156)
            self.addWidget(short, row, 1)
            self.addWidget(full, row, 2)
            self._rank_rows.append((short, full))
            self._rank_names.append((name, full_name))
            row += 1

        self.setColumnStretch(3, 1)
        self.refresh_hooks.append(self._sync_rank_boxes)
        self._sync_rank_boxes()

    def _rank_edit(
        self, name: str, width: int, max_length: Optional[int] = None
    ) -> QLineEdit:
        edit = QLineEdit(self.sc.settings.__dict__[name])
        if max_length is not None:
            edit.setMaxLength(max_length)
        edit.setFixedWidth(width)

        def on_changed(value: str) -> None:
            self.sc.settings.__dict__[name] = value.strip()

        edit.textChanged.connect(on_changed)
        self.settings_map[name] = edit
        return edit

    def _sync_rank_boxes(self) -> None:
        """Show the ladder the chosen naming produces, editable only when it is custom.

        The other namings write nothing back: their values are a preview, the boxes are
        read-only while one is on display, and switching to Custom restores whatever the
        player last typed -- blanks included, which is how a rung asks for its generic
        name.
        """
        settings = self.sc.settings
        editable = settings.live_pilots_rank_names == RANK_NAMES_CUSTOM
        if editable:
            pairs = [
                (settings.__dict__[short], settings.__dict__[full])
                for short, full in self._rank_names
            ]
        else:
            # The container is the settings window, which knows the campaign; country
            # ranks are per squadron, so the player faction is the honest preview.
            faction = getattr(getattr(self.sc, "game", None), "blue", None)
            country = getattr(getattr(faction, "faction", None), "country", None)
            ladder = ranks_for(settings.live_pilots_rank_names, country)
            pairs = [(rank.abbreviation, rank.name) for rank in ladder]

        combo = getattr(self, "_rank_combo", None)
        if combo is not None:
            combo.setEnabled(bool(settings.live_pilots_enabled))
        for (short_edit, full_edit), (short_text, full_text) in zip(
            self._rank_rows, pairs
        ):
            for edit, text in ((short_edit, short_text), (full_edit, full_text)):
                # Disabled, not read-only: the greyed-out tone is what a player reads
                # as "you cannot type here", and it comes from the theme rather than
                # from a colour hard-coded here.
                edit.setEnabled(editable)
                if edit.text() != text:
                    edit.blockSignals(True)
                    edit.setText(text)
                    edit.blockSignals(False)

    def _wire_dependents(
        self, master_name: str, dependent_names: Iterable[str]
    ) -> None:
        """Grey out the settings that mean nothing while their master is off."""
        master = self.settings_map.get(master_name)
        if not isinstance(master, QCheckBox):
            return
        dependents = [
            (self.settings_map.get(name), self.label_map.get(name))
            for name in dependent_names
        ]

        def refresh() -> None:
            enabled = master.isChecked()
            for widget, label in dependents:
                for target in (widget, label):
                    if target is not None:
                        target.setEnabled(enabled)

        master.toggled.connect(lambda _=None: refresh())
        refresh()

    def _wire_opfor_ai(self) -> None:
        """Show the REST/MCP connect URLs when OPFOR AI control is enabled."""
        master = self.settings_map.get("opfor_ai_enabled")

        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 4, 0, 0)
        v.addWidget(QLabel("<b>Connect your LLM (paste a URL):</b>"))
        self._opfor_ai_rest = self._url_row(v, "REST — any HTTP/REST client or curl")
        self._opfor_ai_mcp = self._url_row(v, "MCP — any MCP-compatible client")
        self.addWidget(box, self.rowCount(), 0, 1, 2)
        self._opfor_ai_box = box

        def refresh() -> None:
            show = bool(master and master.isChecked())
            self._opfor_ai_box.setVisible(show)
            if show:
                try:
                    from game.agent import service

                    self._opfor_ai_rest.setText(service.connect_url())
                    self._opfor_ai_mcp.setText(service.mcp_url())
                except Exception:
                    self._opfor_ai_rest.setText(
                        "(start a campaign to generate the URL)"
                    )
                    self._opfor_ai_mcp.setText("")

        if master is not None:
            master.toggled.connect(lambda _=None: refresh())
        refresh()

    def _url_row(self, parent_layout: QVBoxLayout, label: str) -> QLineEdit:
        h = QHBoxLayout()
        h.addWidget(QLabel(label + ":"))
        field = QLineEdit()
        field.setReadOnly(True)
        h.addWidget(field, 1)
        copy = QPushButton("Copy")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(field.text()))
        h.addWidget(copy)
        parent_layout.addLayout(h)
        return field

    def add_label(self, row: int, description: OptionDescription) -> QLabel:
        wrapped_title = "<br />".join(textwrap.wrap(description.text, width=55))
        text = f"<strong>{wrapped_title}</strong>"
        if description.detail is not None:
            wrapped = "<br />".join(textwrap.wrap(description.detail, width=55))
            text += f"<br />{wrapped}"
        label = QLabel(text)
        if description.tooltip is not None:
            label.setToolTip(description.tooltip)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.addWidget(label, row, 0)
        return label

    def add_checkbox_for(self, row: int, name: str, description: BooleanOption) -> None:
        def on_toggle(value: bool) -> None:
            if description.invert:
                value = not value
            self.sc.settings.__dict__[name] = value
            self.settings_changed()
            if description.causes_expensive_game_update:
                self.write_full_settings()

        checkbox = QCheckBox()
        value = self.sc.settings.__dict__[name]
        if description.invert:
            value = not value
        checkbox.setChecked(value)
        checkbox.toggled.connect(on_toggle)
        self.addWidget(checkbox, row, 1, Qt.AlignmentFlag.AlignRight)
        self.settings_map[name] = checkbox

    def add_combobox_for(self, row: int, name: str, description: ChoicesOption) -> None:
        combobox = QComboBox()

        def on_changed(index: int) -> None:
            self.sc.settings.__dict__[name] = combobox.itemData(index)
            self.settings_changed()

        for text, value in description.choices.items():
            combobox.addItem(text, value)
        combobox.setCurrentText(
            description.text_for_value(self.sc.settings.__dict__[name])
        )
        combobox.currentIndexChanged.connect(on_changed)
        self.addWidget(combobox, row, 1, Qt.AlignmentFlag.AlignRight)
        self.settings_map[name] = combobox

    def add_line_edit_for(self, row: int, name: str, description: TextOption) -> None:
        edit = QLineEdit(self.sc.settings.__dict__[name])
        if description.placeholder is not None:
            edit.setPlaceholderText(description.placeholder)

        def on_changed(value: str) -> None:
            self.sc.settings.__dict__[name] = value.strip()

        edit.textChanged.connect(on_changed)
        if description.max_length is not None:
            edit.setMaxLength(description.max_length)
            edit.setMinimumWidth(90)
        else:
            edit.setMinimumWidth(260)
        self.addWidget(edit, row, 1, Qt.AlignmentFlag.AlignRight)
        self.settings_map[name] = edit

    def add_float_spin_slider_for(
        self, row: int, name: str, description: BoundedFloatOption
    ) -> None:
        spinner = FloatSpinSlider(
            description.min,
            description.max,
            self.sc.settings.__dict__[name],
            divisor=description.divisor,
        )

        def on_changed() -> None:
            self.sc.settings.__dict__[name] = spinner.value

        spinner.spinner.valueChanged.connect(on_changed)
        self.addLayout(spinner, row, 1, Qt.AlignmentFlag.AlignRight)
        self.settings_map[name] = spinner

    def add_spinner_for(
        self, row: int, name: str, description: BoundedIntOption
    ) -> None:
        def on_changed(value: int) -> None:
            self.sc.settings.__dict__[name] = value
            if description.causes_expensive_game_update:
                self.write_full_settings()

        spinner = QSpinBox()
        spinner.setMinimum(description.min)
        spinner.setMaximum(description.max)
        spinner.setValue(self.sc.settings.__dict__[name])

        spinner.valueChanged.connect(on_changed)
        self.addWidget(spinner, row, 1, Qt.AlignmentFlag.AlignRight)
        self.settings_map[name] = spinner

    def add_duration_controls_for(
        self, row: int, name: str, description: MinutesOption
    ) -> None:
        inputs = TimeInputs(
            self.sc.settings.__dict__[name], description.min, description.max
        )

        def on_changed() -> None:
            self.sc.settings.__dict__[name] = inputs.value

        inputs.spinner.valueChanged.connect(on_changed)
        self.addLayout(inputs, row, 1, Qt.AlignmentFlag.AlignRight)
        self.settings_map[name] = inputs

    def settings_changed(self) -> None:
        """A value changed: re-evaluate visibility, page-wide when the page said how."""
        if self.on_settings_changed is not None:
            self.on_settings_changed()
        else:
            self.apply_visibility()

    def apply_visibility(self) -> bool:
        """Hide the settings whose visible_when says they do not apply right now.

        Returns whether anything is left showing, so a section whose every setting is
        conditional can hide its own group box instead of leaving an empty frame.
        """
        any_visible = False
        for name, description in Settings.fields(self.page, self.section):
            if description.visible_when is None:
                any_visible = True
                continue
            visible = bool(description.visible_when(self.sc.settings))
            any_visible = any_visible or visible
            self.label_map[name].setVisible(visible)
            entry = self.settings_map[name]
            # The spinner and time options register a layout rather than a widget,
            # and a layout cannot be hidden -- its contents can.
            if isinstance(entry, QLayout):
                for i in range(entry.count()):
                    if (child := entry.itemAt(i).widget()) is not None:
                        child.setVisible(visible)
            else:
                entry.setVisible(visible)
        for hook in self.refresh_hooks:
            hook()
        return any_visible

    def update_from_settings(self) -> None:
        for hook in self.refresh_hooks:
            hook()
        for name, description in Settings.fields(self.page, self.section):
            widget = self.settings_map[name]
            value = self.sc.settings.__dict__[name]
            if isinstance(widget, QCheckBox):
                widget.setChecked(value)
            elif isinstance(widget, QComboBox):
                if (index := widget.findData(value)) > -1:
                    widget.setCurrentIndex(index)
                elif (index := widget.findText(value)) > -1:
                    widget.setCurrentIndex(index)
                else:
                    logging.error(
                        f"Incompatible type '{type(value)}' for ComboBox option {name}"
                    )
            elif isinstance(widget, FloatSpinSlider):
                widget.spinner.setValue(int(value * widget.spinner.divisor))
            elif isinstance(widget, QSpinBox):
                widget.setValue(value)
            elif isinstance(widget, TimeInputs):
                widget.spinner.setValue(value.seconds // 60)
        self.apply_visibility()


class AutoSettingsGroup(QGroupBox):
    def __init__(
        self,
        page: str,
        section: str,
        sc: SettingsContainer,
        write_full_settings: Callable[[], None],
    ) -> None:
        super().__init__(section)
        self.layout = AutoSettingsLayout(page, section, sc, write_full_settings)
        self.setLayout(self.layout)

    def apply_visibility(self) -> None:
        self.setVisible(self.layout.apply_visibility())

    def update_from_settings(self) -> None:
        self.layout.update_from_settings()
        self.apply_visibility()


class AutoSettingsPageLayout(QVBoxLayout):
    def __init__(
        self,
        page: str,
        sc: SettingsContainer,
        write_full_settings: Callable[[], None],
    ) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.widgets = []
        for section in Settings.sections(page):
            self.widgets.append(
                AutoSettingsGroup(page, section, sc, write_full_settings)
            )
            self.addWidget(self.widgets[-1])

        for group in self.widgets:
            group.layout.on_settings_changed = self.refresh_page

    def refresh_page(self) -> None:
        """Re-evaluate every group, since one section can hide another's settings.

        Never call this while the layout is still being built. A group box added to
        a layout that is not yet installed on a widget has no parent, and showing a
        parentless widget in Qt makes it a window: the settings dialog flashed a
        handful of white frames that resized and vanished as the real parent
        arrived. The page calls it once its layout is in place."""
        for group in self.widgets:
            group.apply_visibility()

    def update_from_settings(self) -> None:
        for w in self.widgets:
            w.update_from_settings()


class AutoSettingsPage(QWidget):
    def __init__(
        self,
        page: str,
        sc: SettingsContainer,
        write_full_settings: Callable[[], None],
    ) -> None:
        super().__init__()
        self.layout = AutoSettingsPageLayout(page, sc, write_full_settings)
        self.setLayout(self.layout)
        # Only now do the group boxes have a parent, and only now is hiding one of
        # them a layout change rather than a stray window.
        self.layout.refresh_page()

    def update_from_settings(self) -> None:
        self.layout.update_from_settings()


class QSettingsWindow(QDialog):
    def __init__(self, game: Game):
        super().__init__()
        self.game = game
        self.setLayout(QSettingsWidget(game.settings, game).layout)

        self.setModal(True)
        self.setWindowTitle("Settings")
        self.setWindowIcon(CONST.ICONS["Settings"])
        self.setMinimumSize(840, 480)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._handle_mod_settings()
        super().closeEvent(event)

    def _handle_mod_settings(self) -> None:
        # Applied again on every weather generation, so this is only about the choice
        # taking effect the moment the dialog is closed rather than a turn later.
        apply_cloud_preset_pack(self.game.settings)


class QSettingsWidget(QtWidgets.QWizardPage, SettingsContainer):
    def __init__(self, settings: Settings, game: Optional[Game] = None):
        super().__init__()

        self.settings = game.settings if game else settings
        self.game = game

        #: Only the pages the player has actually looked at. See _ensure_page.
        self.pages: dict[str, AutoSettingsPage] = {}
        self._page_names: list[str] = list(Settings.pages())
        self._page_scrolls: dict[int, QScrollArea] = {}

        self.pluginsPage = PluginsPage(self)
        self.pluginsOptionsPage = PluginOptionsPage(self)

        self.updating_ui = False

        self.initUi()

    def initUi(self):
        self.layout = QGridLayout()

        self.categoryList = QListView()
        self.right_layout = QStackedLayout()

        self.categoryList.setMaximumWidth(175)

        self.categoryModel = QStandardItemModel(self.categoryList)

        self.categoryList.setIconSize(QSize(32, 32))

        for index, name in enumerate(self._page_names):
            page_item = QStandardItem(name)
            if name in CONST.ICONS:
                page_item.setIcon(CONST.ICONS[name])
            else:
                page_item.setIcon(CONST.ICONS["Generator"])
            page_item.setEditable(False)
            page_item.setSelectable(True)
            self.categoryModel.appendRow(page_item)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            self._page_scrolls[index] = scroll
            self.right_layout.addWidget(scroll)

        self.initCheatLayout()
        cheat = QStandardItem("Cheat Menu")
        cheat.setIcon(CONST.ICONS["Cheat"])
        cheat.setEditable(False)
        cheat.setSelectable(True)
        self.categoryModel.appendRow(cheat)
        self.right_layout.addWidget(self.cheatPage)

        plugins = QStandardItem("LUA Plugins")
        plugins.setIcon(CONST.ICONS["Plugins"])
        plugins.setEditable(False)
        plugins.setSelectable(True)
        self.categoryModel.appendRow(plugins)
        self.right_layout.addWidget(self.pluginsPage)

        pluginsOptions = QStandardItem("LUA Plugins Options")
        pluginsOptions.setIcon(CONST.ICONS["PluginsOptions"])
        pluginsOptions.setEditable(False)
        pluginsOptions.setSelectable(True)
        self.categoryModel.appendRow(pluginsOptions)
        scroll = QScrollArea()
        scroll.setWidget(self.pluginsOptionsPage)
        scroll.setWidgetResizable(True)
        self.right_layout.addWidget(scroll)

        self.categoryList.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.categoryList.setModel(self.categoryModel)
        self.categoryList.selectionModel().setCurrentIndex(
            self.categoryList.indexAt(QPoint(1, 1)),
            QItemSelectionModel.SelectionFlag.Select,
        )
        # The default selection is set before the signal is connected, so nothing
        # would build the page the dialog opens on.
        self._ensure_page(0)
        self.categoryList.selectionModel().selectionChanged.connect(
            self.onSelectionChanged
        )

        self.layout.addWidget(self.categoryList, 0, 0, 1, 1)
        self.layout.addLayout(self.right_layout, 0, 1, 5, 1)

        load = QPushButton("Load Settings")
        load.clicked.connect(self.load_settings)
        self.layout.addWidget(load, 1, 0, 1, 1)
        save = QPushButton("Save Settings")
        save.clicked.connect(self.save_settings)
        self.layout.addWidget(save, 2, 0, 1, 1)

        self.setLayout(self.layout)

    def initCheatLayout(self):
        self.cheatPage = QWidget()
        self.cheatLayout = QVBoxLayout()
        self.cheatPage.setLayout(self.cheatLayout)

        self.cheat_options = CheatSettingsBox(self, self.applySettings)
        self.cheatLayout.addWidget(self.cheat_options)

        # One box per coalition so money can be given/taken to OWNFOR and OPFOR.
        # (OPFOR money used to be reachable only via the negative-aircraft exploit.)
        money_row = QHBoxLayout()
        money_row.addWidget(
            self._build_money_cheat_box("OWNFOR (BLUE) Money Cheat", Player.BLUE)
        )
        money_row.addWidget(
            self._build_money_cheat_box("OPFOR (RED) Money Cheat", Player.RED)
        )
        self.cheatLayout.addLayout(money_row, stretch=1)

    def _build_money_cheat_box(self, title: str, player: Player) -> QGroupBox:
        box = QGroupBox(title)
        box.setDisabled(self.game is None)
        box.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout = QGridLayout()
        box.setLayout(layout)
        cheats_amounts = [25, 50, 100, 200, 500, 1000, -25, -50, -100, -200]
        for i, amount in enumerate(cheats_amounts):
            if amount > 0:
                btn = QPushButton("Cheat +" + str(amount) + "M")
                btn.setProperty("style", "btn-success")
            else:
                btn = QPushButton("Cheat " + str(amount) + "M")
                btn.setProperty("style", "btn-danger")
            btn.clicked.connect(self.cheatLambda(amount, player))
            layout.addWidget(btn, i // 2, i % 2)
        return box

    def cheatLambda(self, amount, player):
        return lambda: self.cheatMoney(amount, player)

    def cheatMoney(self, amount, player):
        logging.info(f"CHEATING {player} FOR AMOUNT : {amount}M")
        self.game.coalition_for(player).budget += amount
        GameUpdateSignal.get_instance().updateGame(self.game)

    def applySettings(self):
        if self.updating_ui:
            return
        self.settings.enable_frontline_cheats = self.cheat_options.show_frontline_cheat
        self.settings.enable_base_capture_cheat = (
            self.cheat_options.show_base_capture_cheat
        )
        self.settings.enable_transfer_cheat = self.cheat_options.show_transfer_cheat
        self.settings.enable_runway_state_cheat = (
            self.cheat_options.enable_runway_state_cheat
        )
        self.settings.enable_air_wing_adjustments = (
            self.cheat_options.enable_air_wing_cheats
        )
        self.settings.enable_enemy_buy_sell = self.cheat_options.enable_redfor_buysell

        if self.game:
            events = GameUpdateEvents()
            self.game.compute_unculled_zones(events)
            EventStream.put_nowait(events)
            GameUpdateSignal.get_instance().updateGame(self.game)

    def _ensure_page(self, index: int) -> None:
        """Build a settings page the first time it is looked at.

        The seven pages together are 192 settings and some six hundred widgets, and
        the dialog is rebuilt from scratch on every open -- it used to build all of
        them to show one, which is the couple of seconds before the window appears.
        """
        scroll = self._page_scrolls.get(index)
        if scroll is None or scroll.widget() is not None:
            return
        name = self._page_names[index]
        page = AutoSettingsPage(name, self, self.applySettings)
        self.pages[name] = page
        scroll.setWidget(page)

    def onSelectionChanged(self) -> None:
        index = self.categoryList.selectionModel().currentIndex().row()
        self._ensure_page(index)
        self.right_layout.setCurrentIndex(index)

    def update_from_settings(self) -> None:
        self.updating_ui = True
        for p in self.pages.values():
            p.update_from_settings()

        self.cheat_options.base_capture_cheat_checkbox.setChecked(
            self.settings.enable_base_capture_cheat
        )
        self.cheat_options.frontline_cheat_checkbox.setChecked(
            self.settings.enable_frontline_cheats
        )
        self.cheat_options.transfer_cheat_checkbox.setChecked(
            self.settings.enable_transfer_cheat
        )
        self.cheat_options.base_runway_state_cheat_checkbox.setChecked(
            self.settings.enable_runway_state_cheat
        )
        self.cheat_options.air_wing_adjustments_checkbox.setChecked(
            self.settings.enable_air_wing_adjustments
        )
        self.cheat_options.opfor_buysell_checkbox.setChecked(
            self.settings.enable_enemy_buy_sell
        )

        self.pluginsPage.update_from_settings()
        self.pluginsOptionsPage.update_from_settings()

        self.updating_ui = False

    def load_settings(self):
        sd = settings_dir()
        fd = QFileDialog(caption="Load Settings", directory=str(sd), filter="*.zip")
        if fd.exec_():
            zipfilename = fd.selectedFiles()[0]
            with zipfile.ZipFile(zipfilename, "r") as zf:
                filename = zipfilename.split("/")[-1].replace(".zip", ".json")
                settings = json.loads(
                    zf.read(filename).decode("utf-8"),
                    object_hook=self.settings.obj_hook,
                )
                self.settings.__setstate__(settings)
                self.update_from_settings()

    def save_settings(self):
        sd = settings_dir()
        fd = QFileDialog(caption="Save Settings", directory=str(sd), filter="*.zip")
        fd.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        if fd.exec_():
            zipfilename = fd.selectedFiles()[0]
            with zipfile.ZipFile(zipfilename, "w", zipfile.ZIP_DEFLATED) as zf:
                filename = zipfilename.split("/")[-1].replace(".zip", ".json")
                zf.writestr(
                    filename,
                    json.dumps(
                        self.settings.__dict__,
                        indent=2,
                        default=self.settings.default_json,
                    ),
                    zipfile.ZIP_DEFLATED,
                )

    def load_default_settings(self):
        sd = settings_dir()
        default_zip_path = sd / "Default.zip"
        if default_zip_path.exists():
            with zipfile.ZipFile(default_zip_path, "r") as zf:
                filename = [n for n in zf.namelist() if n.lower() == "default.json"]
                if filename:
                    filename = filename[0]
                    settings_data = json.loads(
                        zf.read(filename).decode("utf-8"),
                        object_hook=self.settings.obj_hook,
                    )
                    self.settings.__setstate__(settings_data)
        else:
            if self.settings is None:
                default_settings = Settings()
            else:
                default_settings = self.settings
            with zipfile.ZipFile(default_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                filename = "Default.json"
                zf.writestr(
                    filename,
                    json.dumps(
                        default_settings.__dict__,
                        indent=2,
                        default=default_settings.default_json,
                    ),
                    zipfile.ZIP_DEFLATED,
                )
            self.settings.__setstate__(default_settings.__dict__)
