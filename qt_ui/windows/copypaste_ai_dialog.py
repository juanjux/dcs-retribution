"""Per-turn copy-paste window for the OPFOR-AI feature (free-LLM accounts).

Give your LLM the briefing once, then each turn copy the turn blob to it and paste
its reply back. All serialisation/parsing lives in game/agent/copypaste.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from game.agent import copypaste


class _BriefingDialog(QDialog):
    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Briefing for your LLM — paste this once")
        self.resize(760, 640)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Give this to your LLM ONCE at the start of the session (as your first "
                "message). It teaches it how to read the turn blob and how to reply."
            )
        )
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setPlainText(text)
        layout.addWidget(view, 1)
        row = QHBoxLayout()
        copy = QPushButton("Copy briefing")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(text))
        row.addWidget(copy)
        row.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        layout.addLayout(row)


class CopyPasteAiDialog(QDialog):
    def __init__(self, side: str = "red", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.side = side
        self.setWindowTitle("OPFOR AI — copy-paste")
        self.resize(740, 680)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "<b>First time only:</b> click <b>Briefing for your LLM</b> and paste "
                "it to your LLM as the first message.<br>"
                "<b>Each turn:</b> 1) <b>Copy turn blob</b> → paste it to your LLM. "
                "2) Paste its reply below → <b>Apply reply</b>.<br>"
                "The blob is scrambled (handle-safe ROT13: words rotated, handles/numbers "
                "kept) so you can't read red's plan; the LLM decodes it and replies the "
                "same way. To send plain text instead, untick the obfuscate option in "
                "OPFOR AI settings."
            )
        )

        briefing_btn = QPushButton("Briefing for your LLM  (paste once)")
        briefing_btn.clicked.connect(self._show_briefing)
        layout.addWidget(briefing_btn)

        layout.addWidget(QLabel("1) Turn blob — copy this to your LLM:"))
        self.outgoing = QPlainTextEdit()
        self.outgoing.setReadOnly(True)
        layout.addWidget(self.outgoing, 1)

        top = QHBoxLayout()
        copy_btn = QPushButton("Copy turn blob")
        copy_btn.clicked.connect(self._copy_outgoing)
        top.addWidget(copy_btn)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_outgoing)
        top.addWidget(refresh_btn)
        top.addStretch(1)
        layout.addLayout(top)

        layout.addWidget(QLabel("2) Paste the LLM's reply here:"))
        self.incoming = QPlainTextEdit()
        layout.addWidget(self.incoming, 1)

        self.results = QPlainTextEdit()
        self.results.setReadOnly(True)
        self.results.setMaximumHeight(120)
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
        _BriefingDialog(copypaste.briefing(self.side), self).exec()

    def _apply(self) -> None:
        try:
            result = copypaste.apply_incoming(self.side, self.incoming.toPlainText())
        except Exception as exc:
            result = f"ERROR: {exc}"
        self.results.setPlainText(result)
        self._refresh_outgoing()  # reflect the applied changes
