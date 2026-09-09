"""The Mission Plugins settings page.

There used to be two pages: one with a checkbox per plugin, and another with every
plugin's options laid out one box after another. Which meant that turning CTLD on and
then setting it up was two clicks apart in a list, and that the options page was a wall
of boxes for plugins you had not enabled.

One page now: a row per plugin -- switch, name, and a gear where there is something to
set -- with its description underneath. The options open in their own dialog, so the
page stays a list you can read down.
"""

from typing import Dict, List, Optional

from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from game.plugins import LuaPlugin, LuaPluginManager
from game.settings import Settings
from game.settings.ISettingsContainer import SettingsContainer
from qt_ui.widgets.gearbutton import gear_button

#: The column the names line up in, so the switches read as one rail.
SWITCH_WIDTH = 28


class PluginOptionsBox(QGroupBox):
    """One plugin's options. Shown in its own dialog now, not on a page of its own."""

    def __init__(self, plugin: LuaPlugin, with_description: bool = True) -> None:
        super().__init__(plugin.name)

        layout = QGridLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        self.widgets: Dict[str, QWidget] = {}

        row = 0
        if with_description and plugin.description:
            description = QLabel(plugin.description)
            description.setWordWrap(True)
            font = description.font()
            font.setItalic(True)
            description.setFont(font)
            description.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            layout.addWidget(description, row, 0, 1, 2)
            row += 1

        for option in plugin.options:
            label = QLabel(option.name)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label, row, 0)

            val = option.get_value
            if isinstance(val, bool):
                checkbox = QCheckBox()
                checkbox.setChecked(val)
                checkbox.toggled.connect(option.set_value)
                layout.addWidget(checkbox, row, 1)
                self.widgets[option.identifier] = checkbox
            elif isinstance(val, (float, int)):
                spinbox: QWidget
                if isinstance(val, float):
                    spinbox = QDoubleSpinBox()
                    spinbox.setSingleStep(0.01)
                    spinbox.setLocale(QLocale.Language.English)
                else:
                    spinbox = QSpinBox()
                spinbox.setMinimum(option.min)
                spinbox.setMaximum(option.max)
                spinbox.setValue(val)
                spinbox.valueChanged.connect(option.set_value)
                layout.addWidget(spinbox, row, 1)
                self.widgets[option.identifier] = spinbox

            row += 1

    def update_from_settings(self, settings: Settings) -> None:
        for identifier in self.widgets:
            value = settings.plugin_option(identifier)
            w = self.widgets[identifier]
            if isinstance(w, QCheckBox):
                w.setChecked(value)
            elif isinstance(w, (QDoubleSpinBox, QSpinBox)):
                w.setValue(value)


class PluginOptionsDialog(QDialog):
    """What the gear opens: this plugin's settings, and a way out."""

    def __init__(self, plugin: LuaPlugin, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{plugin.name} options")
        self.setMinimumWidth(560)
        self.resize(560, 700)

        column = QVBoxLayout()
        self.setLayout(column)
        # Splash Damage has sixty-five of them, so the box scrolls rather than
        # growing a dialog taller than the screen.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # The description is already on the row this was opened from.
        scroll.setWidget(PluginOptionsBox(plugin, with_description=False))
        column.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        column.addLayout(buttons)


class PluginRow(QWidget):
    """A switch, the plugin's name, a gear if it has anything to set, then why."""

    def __init__(self, plugin: LuaPlugin) -> None:
        super().__init__()
        self.plugin = plugin

        column = QVBoxLayout()
        column.setContentsMargins(0, 4, 0, 10)
        column.setSpacing(2)
        self.setLayout(column)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(6)
        column.addLayout(head)

        self.checkbox = QCheckBox()
        self.checkbox.setFixedWidth(SWITCH_WIDTH)
        self.checkbox.setChecked(plugin.get_value)
        self.checkbox.toggled.connect(plugin.set_value)
        head.addWidget(self.checkbox)

        name = QLabel(plugin.name)
        font = name.font()
        font.setBold(True)
        name.setFont(font)
        head.addWidget(name)

        if plugin.options:
            # The gears, the same icon the main toolbar opens settings with -- the
            # plug belongs to the plugin list, not to its options.
            self.gear = gear_button(f"{plugin.name} options")
            self.gear.clicked.connect(self.open_options)
            head.addWidget(self.gear)
        head.addStretch()

        if plugin.description:
            description = QLabel(plugin.description)
            description.setWordWrap(True)
            font = description.font()
            font.setItalic(True)
            description.setFont(font)
            description.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            # Indented to the name, so the switches keep their own column.
            description.setContentsMargins(SWITCH_WIDTH + 6, 0, 0, 0)
            column.addWidget(description)

        self.dialog: Optional[PluginOptionsDialog] = None

    def open_options(self) -> None:
        self.dialog = PluginOptionsDialog(self.plugin, self)
        self.dialog.exec()


class PluginsPage(QWidget):
    """Every plugin, one row each."""

    def __init__(self, sc: SettingsContainer) -> None:
        super().__init__()
        self.sc = sc

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        self.rows: List[PluginRow] = []
        for plugin in LuaPluginManager.plugins():
            if not plugin.show_in_ui:
                continue
            row = PluginRow(plugin)
            layout.addWidget(row)
            self.rows.append(row)

    def update_from_settings(self) -> None:
        enabled = self.sc.settings.plugins
        for row in self.rows:
            if row.plugin.identifier in enabled:
                row.checkbox.setChecked(enabled[row.plugin.identifier])
