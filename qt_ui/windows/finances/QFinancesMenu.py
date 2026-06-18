import itertools
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import qt_ui.uiconstants as CONST
from game.game import Game
from game.income import BuildingIncome, Income
from game.theater import ControlPoint, Player


class QHorizontalSeparationLine(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumWidth(1)
        self.setFixedHeight(20)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)


class FinancesLayout(QGridLayout):
    """Compact income-only breakdown, embedded in the intel panel."""

    def __init__(self, game: Game, player: Player, total_at_top: bool = False) -> None:
        super().__init__()
        self.row = itertools.count(0)

        income = Income(game, player)

        if total_at_top:
            self.add_total(game, income, player)
            self.add_line()

        control_points = reversed(
            sorted(income.control_points, key=lambda c: c.income_per_turn)
        )
        for control_point in control_points:
            self.add_control_point(control_point)

        self.add_line()

        buildings = reversed(sorted(income.buildings, key=lambda b: b.income))
        for building in buildings:
            self.add_building(building)

        if not total_at_top:
            self.add_line()
            self.add_total(game, income, player)

    def add_total(self, game: Game, income: Income, player: Player) -> None:
        self.add_row(
            middle=f"Income multiplier: {income.multiplier:.1f}",
            right=f"<b>{income.total:.1f}M</b>",
        )
        budget = game.coalition_for(player).budget
        self.add_row(middle="Balance", right=f"<b>{budget:.1f}M</b>")
        self.setRowStretch(next(self.row), 1)

    def add_row(
        self,
        left: Optional[str] = None,
        middle: Optional[str] = None,
        right: Optional[str] = None,
    ) -> None:
        if not any([left, middle, right]):
            raise ValueError

        row = next(self.row)
        if left is not None:
            self.addWidget(QLabel(left), row, 0)
        if middle is not None:
            self.addWidget(QLabel(middle), row, 1)
        if right is not None:
            self.addWidget(QLabel(right), row, 2)

    def add_control_point(self, control_point: ControlPoint) -> None:
        self.add_row(
            left=f"<b>{control_point.name}</b>",
            right=f"{control_point.income_per_turn}M",
        )

    def add_building(self, building: BuildingIncome) -> None:
        row = next(self.row)
        self.addWidget(
            QLabel(f"<b>{building.category.upper()} [{building.name}]</b>"), row, 0
        )
        self.addWidget(
            QLabel(f"{building.number} buildings x {building.income_per_building}M"),
            row,
            1,
        )
        rlabel = QLabel(f"{building.income}M")
        rlabel.setProperty("style", "green")
        self.addWidget(rlabel, row, 2)

    def add_line(self) -> None:
        self.addWidget(QHorizontalSeparationLine(), next(self.row), 0, 1, 3)


#: Automated-spending categories shown in the dialog, in display order. Each is
#: (last_turn_expenses key, label, the settings flag that toggles it for blue).
_EXPENSE_CATEGORIES = [
    ("front_line", "Front line reinforcement", "automate_front_line_reinforcements"),
    ("aircraft", "Aircraft purchases", "automate_aircraft_reinforcements"),
    ("runways", "Runway repairs", "automate_runway_repair"),
]

_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_CENTER = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter


def _money(value: float, signed: bool = False) -> str:
    rounded = round(value)
    if signed:
        sign = "+" if rounded > 0 else ("-" if rounded < 0 else "")
        return f"{sign}{abs(rounded)}M"
    return f"{rounded}M"


def _label(
    text: str,
    style: Optional[str] = None,
    *,
    right: bool = False,
    center: bool = False,
    bold: bool = False,
) -> QLabel:
    label = QLabel(text)
    if right:
        label.setAlignment(_RIGHT)
    elif center:
        label.setAlignment(_CENTER)
    if style is not None:
        label.setProperty("style", style)
    if bold:
        font = label.font()
        font.setBold(True)
        label.setFont(font)
    return label


def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


class QFinancesMenu(QDialog):
    """Finances dialog showing gross income, automated HQ spending and net.

    The income the player sees on the map is mostly auto-spent on reinforcements
    and repairs (when the matching automation is enabled) before they ever touch
    it. This dialog spells out income, that spending per category, and the net
    that actually reaches the budget, so the gap is no longer a mystery.
    """

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game
        self.setModal(True)
        self.setWindowTitle(f"Finances - Turn {game.turn}")
        self.setWindowIcon(CONST.ICONS["Money"])
        self.setMinimumSize(520, 420)

        income = Income(game, Player.BLUE)
        coalition = game.coalition_for(Player.BLUE)
        expenses = getattr(coalition, "last_turn_expenses", {}) or {}
        total_spent = sum(expenses.values())
        gross = income.total
        net = gross - total_spent
        balance = coalition.budget

        root = QVBoxLayout(self)
        root.addWidget(self._summary(gross, total_spent, net, balance))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        detail = QVBoxLayout(content)
        detail.addWidget(self._income_box(income))
        detail.addWidget(self._expenses_box(expenses, total_spent))
        detail.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        root.addLayout(buttons)

    def _summary(
        self, gross: float, spent: float, net: float, balance: float
    ) -> QFrame:
        frame = QFrame()
        frame.setProperty("style", "summary-box")
        grid = QGridLayout(frame)
        grid.addWidget(_label("Gross income"), 0, 0)
        grid.addWidget(_label(_money(gross, signed=True), "green", right=True), 0, 1)
        grid.addWidget(_label("HQ auto-spending"), 1, 0)
        grid.addWidget(_label(_money(-spent, signed=True), "expense", right=True), 1, 1)
        grid.addWidget(_hline(), 2, 0, 1, 2)
        grid.addWidget(_label("NET THIS TURN", bold=True), 3, 0)
        grid.addWidget(
            _label(
                _money(net, signed=True),
                "net" if net >= 0 else "net-neg",
                right=True,
            ),
            3,
            1,
        )
        grid.addWidget(_label("Available balance"), 4, 0)
        grid.addWidget(_label(_money(balance), "balance", right=True), 4, 1)
        return frame

    def _income_box(self, income: Income) -> QGroupBox:
        box = QGroupBox(f"Income - multiplier x{income.multiplier:.2f}")
        layout = QVBoxLayout(box)
        gross_pre = income.total_buildings + income.from_bases
        layout.addWidget(
            _label(
                f"{_money(gross_pre)} -> {_money(income.total)}", "muted", right=True
            )
        )

        layout.addWidget(_label("Bases", bold=True))
        bases = QGridLayout()
        control_points = reversed(
            sorted(income.control_points, key=lambda c: c.income_per_turn)
        )
        for i, cp in enumerate(control_points):
            bases.addWidget(_label(f"    {cp.name}"), i, 0)
            bases.addWidget(_label(_money(cp.income_per_turn), right=True), i, 1)
        layout.addLayout(bases)
        layout.addWidget(_hline())

        layout.addWidget(_label("Buildings", bold=True))
        by_category: dict[str, List[BuildingIncome]] = {}
        for building in income.buildings:
            by_category.setdefault(building.category, []).append(building)
        for category in sorted(
            by_category, key=lambda c: -sum(b.income for b in by_category[c])
        ):
            rows = sorted(by_category[category], key=lambda b: -b.income)
            subtotal = sum(b.income for b in rows)
            layout.addWidget(self._category_group(category, subtotal, rows))
        return box

    def _category_group(
        self, category: str, subtotal: float, rows: List[BuildingIncome]
    ) -> QGroupBox:
        box = QGroupBox(f"{category.upper()} - {_money(subtotal)}")
        box.setCheckable(True)
        box.setChecked(False)  # collapsed by default; only subtotals show

        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setContentsMargins(0, 0, 0, 0)
        for i, building in enumerate(rows):
            dead = round(building.income) == 0
            style = "muted" if dead else None
            grid.addWidget(_label(f"    {building.name}", style), i, 0)
            grid.addWidget(
                _label(
                    f"{building.number} x {building.income_per_building}M =",
                    "muted",
                    right=True,
                ),
                i,
                1,
            )
            grid.addWidget(_label(_money(building.income), style, right=True), i, 2)

        outer = QVBoxLayout(box)
        outer.setContentsMargins(6, 0, 6, 6)
        outer.addWidget(inner)
        inner.setVisible(False)
        box.toggled.connect(inner.setVisible)
        return box

    def _expenses_box(
        self, expenses: dict[str, float], total_spent: float
    ) -> QGroupBox:
        box = QGroupBox("HQ auto-spending - last turn")
        grid = QGridLayout(box)
        settings = self.game.settings
        row = 0
        for key, label, flag in _EXPENSE_CATEGORIES:
            enabled = bool(getattr(settings, flag, False))
            amount = expenses.get(key, 0.0)
            grid.addWidget(_label(label), row, 0)
            grid.addWidget(
                _label(
                    " ON " if enabled else " OFF",
                    "pill-on" if enabled else "pill-off",
                    center=True,
                ),
                row,
                1,
            )
            zero = (not enabled) or round(amount) == 0
            grid.addWidget(
                _label(
                    _money(0) if zero else _money(-amount, signed=True),
                    "muted" if zero else "expense",
                    right=True,
                ),
                row,
                2,
            )
            row += 1

        grid.addWidget(_hline(), row, 0, 1, 3)
        grid.addWidget(_label("Total spent by HQ", bold=True), row + 1, 0)
        grid.addWidget(
            _label(_money(-total_spent, signed=True), "expense", right=True),
            row + 1,
            2,
        )
        return box
