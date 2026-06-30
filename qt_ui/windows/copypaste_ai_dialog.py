"""Per-turn copy-paste window for the OPFOR-AI feature (free-LLM accounts).

Copy the compact turn blob to any LLM, paste its reply back, Apply. All the
serialisation/parsing lives in game/agent/copypaste.py; this is just the UI.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from game.agent import copypaste


class CopyPasteAiDialog(QDialog):
    def __init__(self, side: str = "red", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.side = side
        self.setWindowTitle("OPFOR AI — copy-paste")
        self.resize(720, 640)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "1) Copy the turn blob and paste it to your LLM.\n"
                "2) Paste the LLM's reply below and click Apply."
            )
        )

        self.outgoing = QPlainTextEdit()
        self.outgoing.setReadOnly(True)
        layout.addWidget(self.outgoing, 1)

        top_buttons = QHBoxLayout()
        copy_btn = QPushButton("Copy turn blob")
        copy_btn.clicked.connect(self._copy_outgoing)
        top_buttons.addWidget(copy_btn)
        briefing_btn = QPushButton("Show briefing")
        briefing_btn.clicked.connect(self._show_briefing)
        top_buttons.addWidget(briefing_btn)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_outgoing)
        top_buttons.addWidget(refresh_btn)
        top_buttons.addStretch(1)
        layout.addLayout(top_buttons)

        layout.addWidget(QLabel("Paste the LLM's reply here:"))
        self.incoming = QPlainTextEdit()
        layout.addWidget(self.incoming, 1)

        self.results = QPlainTextEdit()
        self.results.setReadOnly(True)
        self.results.setMaximumHeight(130)
        self.results.setPlaceholderText("Results appear here after Apply.")
        layout.addWidget(self.results)

        bottom = QHBoxLayout()
        apply_btn = QPushButton("Apply reply")
        apply_btn.setProperty("style", "start-button")
        apply_btn.clicked.connect(self._apply)
        bottom.addWidget(apply_btn)
        bottom.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

        self._refresh_outgoing()

    def _refresh_outgoing(self) -> None:
        try:
            self.outgoing.setPlainText(copypaste.outgoing_blob(self.side))
        except Exception as exc:  # no game / server not ready
            self.outgoing.setPlainText(f"(could not build the turn blob: {exc})")

    def _copy_outgoing(self) -> None:
        QApplication.clipboard().setText(self.outgoing.toPlainText())

    def _show_briefing(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Copy-paste briefing")
        box.setText(copypaste.briefing(self.side))
        box.exec()

    def _apply(self) -> None:
        try:
            result = copypaste.apply_incoming(self.side, self.incoming.toPlainText())
        except Exception as exc:
            result = f"ERROR: {exc}"
        self.results.setPlainText(result)
        self._refresh_outgoing()  # reflect the applied changes
