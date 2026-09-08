"""The gear that opens a thing's options.

Used wherever a row has settings of its own rather than a page of its own: the
plugin list and the switches that carry their own tuning. Framed, because flat it
read as decoration rather than as something to press.
"""

from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QToolButton, QWidget

import qt_ui.uiconstants as CONST

GEAR_STYLE = (
    "QToolButton { background: #2D3E50; border: 1px solid #3A4B5C;"
    " border-radius: 3px; }"
    "QToolButton:hover { background: #33475C; }"
    "QToolButton:pressed { background: #22303B; }"
    "QToolButton:disabled { background: #26303A; border-color: #2F3A45; }"
)


def gear_button(tooltip: str, parent: Optional[QWidget] = None) -> QToolButton:
    gear = QToolButton(parent)
    gear.setIcon(CONST.ICONS["Settings"])
    gear.setIconSize(QSize(16, 16))
    gear.setFixedSize(24, 24)
    gear.setToolTip(tooltip)
    gear.setCursor(Qt.CursorShape.PointingHandCursor)
    gear.setStyleSheet(GEAR_STYLE)
    return gear
