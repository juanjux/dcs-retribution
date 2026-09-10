"""Cards with their captions above them, the shape the redesigned dialogs use.

A ``QGroupBox`` puts its title inside its own frame, which means every section pays for
a border, a title inset and a set of margins before it shows anything. These draw the
caption above a plain card instead: the name reads as a heading, the card holds only
content, and two cards side by side line up on their contents rather than on their
frames.

Written once here because the debriefing, the flight dialog and the squadron dialog
were each about to grow their own copy, and a fourth would have drifted.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

CARD_BG = "#14202B"
CARD_BORDER = "#1D2731"
CAPTION = "#6B7A87"
HINT = "#4F6070"

CAPTION_HEIGHT = 20


def card() -> QWidget:
    """An empty card. Give it a layout and put the content in."""
    widget = QWidget()
    widget.setStyleSheet(
        f"background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 3px;"
    )
    return widget


def caption(text: str, hint: str = "") -> QWidget:
    """A section's name, above its card rather than inside a frame.

    The hint is for the sentence a group box would have put inside itself and pushed
    the content down for -- "AUTO lets the generator pick", "TOT comes from the
    package". It belongs with the heading, in the quietest colour on the page.
    """
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)

    name = QLabel(text.upper())
    name.setStyleSheet(
        f"font-size: 11px; font-weight: bold; letter-spacing: 1px; color: {CAPTION};"
        " background: transparent; border: none;"
    )
    row.addWidget(name)

    if hint:
        note = QLabel(hint)
        note.setStyleSheet(
            f"font-size: 11px; color: {HINT}; background: transparent; border: none;"
        )
        row.addWidget(note)

    row.addStretch()
    holder = QWidget()
    holder.setFixedHeight(CAPTION_HEIGHT)
    holder.setLayout(row)
    return holder


def section(
    name: str, content: QWidget, hint: str = "", spacing: int = 10
) -> QVBoxLayout:
    """A caption and its card, as one thing to add to a column."""
    column = QVBoxLayout()
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(spacing)
    column.addWidget(caption(name, hint))
    column.addWidget(content)
    return column


def carded(
    name: str, inner: QWidget, hint: str = "", margins: Optional[tuple] = None
) -> QVBoxLayout:
    """The common case: wrap a widget in a card and give it a caption.

    ``inner`` keeps its own background, so anything that paints itself -- a scroll
    area, a table -- comes through unchanged and only the frame follows the card.
    """
    holder = card()
    layout = QVBoxLayout()
    left, top, right, bottom = margins if margins is not None else (12, 10, 12, 10)
    layout.setContentsMargins(left, top, right, bottom)
    layout.setSpacing(8)
    inner.setStyleSheet(
        (inner.styleSheet() or "") + " background: transparent; border: none;"
    )
    layout.addWidget(inner)
    holder.setLayout(layout)
    return section(name, holder, hint)
