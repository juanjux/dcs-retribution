from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from game.radio.TacanContainer import TacanContainer
from game.radio.tacan import TacanChannel, TacanBand
from qt_ui.models import GameModel
from qt_ui.windows.QTacanDialog import QTacanDialog


class QTacanWidget(QWidget):
    def __init__(self, container: TacanContainer, game_model: GameModel) -> None:
        super().__init__()

        self.ct = container
        self.gm = game_model

        columns = QHBoxLayout()
        self.setLayout(columns)

        self.channel = QLabel(self._get_label_text())
        self.check_channel()
        columns.addWidget(self.channel)
        columns.addStretch()

        self.set_tacan_btn = QPushButton("Set TACAN")
        self.set_tacan_btn.setProperty("class", "comms")
        self.set_tacan_btn.setFixedWidth(100)
        columns.addWidget(self.set_tacan_btn)
        self.set_tacan_btn.clicked.connect(self.open_tacan_dialog)

        self.reset_tacan_btn = QPushButton("Reset TACAN")
        self.reset_tacan_btn.setProperty("class", "btn-danger comms")
        self.reset_tacan_btn.setFixedWidth(100)
        columns.addWidget(self.reset_tacan_btn)
        self.reset_tacan_btn.clicked.connect(self.reset_tacan)

    def _get_label_text(self) -> str:
        if self.ct.tacan is None:
            return "<b>TACAN: AUTO</b>"
        cs = self.ct.tcn_name
        cs = "" if cs is None else f" ({cs})"
        is_auto = getattr(self.ct, "tacan_is_auto", False)
        prefix = "AUTO " if is_auto else ""
        return f"<b>TACAN: {prefix}{self.ct.tacan}{cs}</b>"

    def open_tacan_dialog(self) -> None:
        self.tacan_dialog = QTacanDialog(self, self.ct)
        self.tacan_dialog.accepted.connect(self.assign_tacan)
        self.tacan_dialog.show()

    def assign_tacan(self) -> None:
        channel = self.tacan_dialog.tacan_input.value()
        band = self.tacan_dialog.band_input.currentText()
        band = TacanBand.X if band == "X" else TacanBand.Y
        candidate = TacanChannel(number=channel, band=band)

        # Warn before letting the user double-book a TACAN that is already in
        # use elsewhere (another base/carrier, or a flight). Skip the warning
        # when the user "re-saves" the same channel this container already
        # owns — that's not a new collision.
        if candidate != self.ct.tacan and candidate in self.gm.allocated_tacan:
            reply = QMessageBox.question(
                self,
                "TACAN already in use",
                (
                    f"TACAN channel {candidate} is already assigned elsewhere "
                    "in this mission (another base, carrier or flight). "
                    "Assigning it here will double-book the channel.\n\n"
                    "Use it anyway?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._try_remove()
        self.ct.tacan = candidate
        self.gm.allocated_tacan.append(self.ct.tacan)
        if cs := self.tacan_dialog.callsign_input.text():
            self.ct.tcn_name = cs.upper()
        # User-chosen channel: lock it in so the auto-allocator reuses it and
        # the UI no longer labels it 'AUTO'.
        self.ct.tacan_is_auto = False
        self.channel.setText(self._get_label_text())
        self.check_channel()

    def reset_tacan(self) -> None:
        self._try_remove()
        self.ct.tacan = None
        self.ct.tcn_name = None
        # Back to auto: the next mission generation will allocate a fresh
        # channel and the dialog will read 'AUTO' or 'AUTO (94X)' afterwards.
        self.ct.tacan_is_auto = True
        self.channel.setText(self._get_label_text())
        self._reset_color_and_tooltip()

    def check_channel(self) -> None:
        if self.ct.tacan is None:
            return
        if self.gm.allocated_tacan.count(self.ct.tacan) > 1:
            self.channel.setStyleSheet("color: orange")
            self.channel.setToolTip(
                "Double booked TACAN channel, verify that this was your intention."
            )
        elif self.gm.allocated_tacan.count(self.ct.tacan) == 1:
            self._reset_color_and_tooltip()

    def _reset_color_and_tooltip(self):
        self.channel.setStyleSheet("color: white")
        self.channel.setToolTip(None)

    def _try_remove(self) -> None:
        try:
            self.gm.allocated_tacan.remove(self.ct.tacan)
        except ValueError:
            pass
