"""Embedded "Mission in Progress" command panel.

Replaces the floating QWaitingForMissionResultWindow(QDialog) while the player
flies a turn in DCS. It is inserted into the central splitter slot where the live
map normally lives (the map is hidden meanwhile, which also dodges the Qt6
GL/QtWebEngine compositing deadlock that a modal-over-map used to hit), and the
surrounding chrome is covered with DimScrim overlays so the panel reads as modal.

Design (widget tree + QSS) by Claude Design; data wiring here. The owner
(QTopPanel) drives it: install_scrims(...), then push data with update_*()/
ingest_debriefing() on each poll + a ~1s timer, and wires the footer buttons.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from game.debriefing import Debriefing
from game.theater import Player

ICONS = "./resources/ui"

#: scoreboard category -> (SideLossCounts attr, label, icon). Icons are existing PNGs.
SCORE_CATEGORIES = [
    ("aircraft", "Aircraft", f"{ICONS}/events/air_intercept.png"),
    ("front_line", "Front-line units", f"{ICONS}/events/infantry.PNG"),
    ("convoy", "Convoy units", f"{ICONS}/events/convoy.png"),
    ("cargo_ships", "Shipping cargo", f"{ICONS}/events/naval_intercept.PNG"),
    ("airlift_cargo", "Airlift cargo", f"{ICONS}/events/delivery.PNG"),
    ("ground_objects", "Ground objects", f"{ICONS}/events/strike.PNG"),
    ("scenery", "Scenery", f"{ICONS}/misc/generator.png"),
    ("bases_lost", "Bases", f"{ICONS}/airbase.png"),
]

ICON_AIR = f"{ICONS}/events/air_intercept.png"
ICON_GROUND = f"{ICONS}/events/strike.PNG"
ICON_CAPTURE = f"{ICONS}/events/capture.PNG"
ICON_CHECK = f"{ICONS}/misc/proceed.png"


def _label(text: str, style: Optional[str] = None) -> QLabel:
    lbl = QLabel(text)
    if style:
        lbl.setProperty("style", style)
    return lbl


def _v(*children, spacing: int = 0, margins=(0, 0, 0, 0)) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    for c in children:
        if isinstance(c, (QHBoxLayout, QVBoxLayout, QGridLayout)):
            lay.addLayout(c)
        else:
            lay.addWidget(c)
    return w


def _fmt_td(td: timedelta) -> str:
    secs = max(0, int(td.total_seconds()))
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _prettify_dcs_name(raw: Optional[str]) -> Optional[str]:
    """'weapons.missiles.AIM_120C' -> 'AIM 120C'; 'FA-18C_hornet' -> 'FA-18C hornet'."""
    if not raw:
        return None
    name = str(raw)
    if "." in name:
        name = name.rsplit(".", 1)[-1]
    return name.replace("_", " ").strip() or None


class DimScrim(QWidget):
    """Translucent, click-eating overlay that tracks a target widget's geometry."""

    def __init__(self, target: QWidget, parent: QWidget) -> None:
        super().__init__(parent)
        self._target = target
        self.setProperty("style", "dim-scrim")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        target.installEventFilter(self)
        self._sync()
        self.raise_()
        self.show()

    def eventFilter(self, obj, event):
        if obj is self._target and event.type() in (
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.Move,
            QtCore.QEvent.Type.Show,
        ):
            self._sync()
        return False

    def _sync(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        top_left = self._target.mapTo(parent, self._target.rect().topLeft())
        self.setGeometry(
            top_left.x(), top_left.y(), self._target.width(), self._target.height()
        )
        self.raise_()


class EventRow(QFrame):
    def __init__(
        self, icon_path: str, text: str, verb: str, side: str, time_str: str
    ) -> None:
        super().__init__()
        self.setProperty("style", "mip-event")
        self.setProperty("side", side)  # "blue" | "red" | "neutral"

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 11, 16, 11)
        lay.setSpacing(11)

        icon = QLabel()
        icon.setPixmap(
            QPixmap(icon_path).scaledToHeight(
                18, Qt.TransformationMode.SmoothTransformation
            )
        )
        icon.setFixedWidth(20)
        lay.addWidget(icon)

        text_lbl = _label(text, "mip-event-text")
        text_lbl.setWordWrap(True)
        verb_lbl = _label(verb, "mip-event-verb")
        verb_lbl.setProperty("side", side)
        lay.addWidget(_v(text_lbl, verb_lbl), stretch=1)

        lay.addWidget(_label(time_str, "mip-event-time"))


class MissionProgressPanel(QFrame):
    """The embedded waiting/progress panel. Build once, then push data into it."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setProperty("style", "mission-panel")
        self.setProperty("state", "in-progress")
        self.setMinimumSize(800, 600)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._scrims: list[DimScrim] = []
        # event-feed diff bookkeeping (debriefing is re-parsed cumulatively each poll)
        self._shown_blue_air = 0
        self._shown_enemy_air = 0
        self._seen_captures: set[str] = set()
        self._shown_ground_by_cat: dict[str, int] = {}
        self._completed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._build_stats_strip())
        root.addWidget(self._build_main_row(), stretch=1)
        root.addWidget(self._build_footer())

    # ---- header ---------------------------------------------------------- #
    def _build_header(self) -> QFrame:
        bar = QFrame()
        bar.setProperty("style", "mip-header")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(22, 16, 22, 16)
        lay.setSpacing(18)

        self.spinner = QLabel()
        self._spinner_movie = QMovie(f"{ICONS}/loader.gif")
        self.spinner.setMovie(self._spinner_movie)
        self.spinner.setFixedSize(26, 26)
        self.spinner.setScaledContents(True)
        self._spinner_movie.start()
        lay.addWidget(self.spinner)

        self.title = _label("MISSION IN PROGRESS", "mip-title")
        self.subtitle = _label("FLYING TURN IN DCS — AWAITING RESULT", "mip-subtitle")
        lay.addWidget(_v(self.title, self.subtitle))
        lay.addStretch(1)

        self.elapsed_value = _label("00:00", "mip-timer")
        elapsed_box = _v(_label("ELAPSED", "mip-caption"), self.elapsed_value)
        elapsed_box.layout().setAlignment(Qt.AlignmentFlag.AlignRight)
        lay.addWidget(elapsed_box)
        return bar

    # ---- stats strip ----------------------------------------------------- #
    def _build_stats_strip(self) -> QFrame:
        strip = QFrame()
        strip.setProperty("style", "mip-stats")
        lay = QHBoxLayout(strip)
        lay.setContentsMargins(22, 14, 22, 14)
        lay.setSpacing(14)

        self.rw_start = _label("--:--:--", "mip-stat-value")
        self.rw_now = _label("--:--:--", "mip-stat-value")
        lay.addWidget(
            self._clock_group(
                "REAL WORLD", [("START", self.rw_start), ("NOW", self.rw_now)]
            )
        )

        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        lay.addWidget(vline)

        self.ig_time = _label("-- --- --:--", "mip-stat-value")
        self.ig_elapsed = _label("0:00:00", "mip-stat-value")
        self.ingame_caption = _label("IN-GAME — TURN ?", "mip-stat-label")
        self.ingame_group = self._clock_group(
            None,
            [("MISSION TIME", self.ig_time), ("DCS MISSION", self.ig_elapsed)],
            caption_widget=self.ingame_caption,
        )
        lay.addWidget(self.ingame_group)
        lay.addStretch(1)

        chips = QWidget()
        chip_lay = QHBoxLayout(chips)
        chip_lay.setContentsMargins(0, 0, 0, 0)
        chip_lay.setSpacing(8)
        self.wind_chip = _label("— wind", "mip-chip")
        self.cloud_chip = _label("—", "mip-chip")
        self.temp_chip = _label("—", "mip-chip")
        self.tod_chip = _label("—", "mip-chip")
        for c in (self.wind_chip, self.cloud_chip, self.temp_chip, self.tod_chip):
            chip_lay.addWidget(c)
        lay.addWidget(chips)
        return strip

    def _clock_group(
        self,
        caption: Optional[str],
        cells: list[tuple[str, QLabel]],
        caption_widget: Optional[QLabel] = None,
    ) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        cap = caption_widget or _label(caption or "", "mip-stat-label")
        grid.addWidget(cap, 0, 0, 1, len(cells))
        for col, (cell_cap, value_lbl) in enumerate(cells):
            grid.addWidget(_label(cell_cap, "mip-stat-label"), 1, col)
            grid.addWidget(value_lbl, 2, col)
        return w

    # ---- main row -------------------------------------------------------- #
    def _build_main_row(self) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(22, 18, 22, 18)
        left_lay.setSpacing(16)
        left_lay.addWidget(self._build_exchange_card())
        left_lay.addWidget(self._build_scoreboard(), stretch=1)
        lay.addWidget(left, stretch=3)

        lay.addWidget(self._build_feed())
        return row

    def _build_exchange_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("style", "mip-card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(22)

        lay.addWidget(
            _v(
                _label("EXCHANGE RATIO", "mip-stat-label"),
                _label("kills : losses", "mip-stat-label"),
            )
        )

        self.ratio_value = _label("", "mip-ratio")
        self.ratio_value.setTextFormat(Qt.TextFormat.RichText)
        self.ratio_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.ratio_value, stretch=1)
        self._set_ratio(0, 0)

        self.own_total = _label("0", "mip-counter-num")
        self.enemy_total = _label("0", "mip-counter-num")
        totals = QWidget()
        t_lay = QHBoxLayout(totals)
        t_lay.setContentsMargins(0, 0, 0, 0)
        t_lay.setSpacing(22)
        t_lay.addWidget(_v(self.own_total, _label("OWN LOSSES", "mip-counter-label")))
        t_lay.addWidget(
            _v(self.enemy_total, _label("ENEMY LOSSES", "mip-counter-label"))
        )
        lay.addWidget(totals)
        return card

    def _set_ratio(self, own: int, enemy: int) -> None:
        if own == 0 and enemy == 0:
            ratio = "—"
        elif own == 0:
            ratio = f"{enemy} : 0"
        else:
            ratio = f"{enemy / own:.1f} : 1"
        # First number = our kills (enemy losses) → blue; second = our losses → red.
        self.ratio_value.setText(
            f'<span style="color:#3592C4">{ratio.split(" : ")[0]}</span>'
            f' <span style="color:#6F7F8B">:</span> '
            f'<span style="color:#D84545">{ratio.split(" : ")[1] if " : " in ratio else ""}</span>'
            if " : " in ratio
            else f'<span style="color:#6F7F8B">{ratio}</span>'
        )

    def _build_scoreboard(self) -> QFrame:
        board = QFrame()
        board.setProperty("style", "mip-scoreboard")
        lay = QVBoxLayout(board)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = QWidget()
        header.setProperty("style", "mip-score-header")
        h = QGridLayout(header)
        h.setContentsMargins(16, 0, 0, 0)
        h.setColumnStretch(0, 1)
        h.addWidget(_label("CASUALTIES", "mip-stat-label"), 0, 0)
        blue_col = _label("BLUE · OwnFor", "mip-col-blue")
        red_col = _label("RED · OpFor", "mip-col-red")
        blue_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        red_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(blue_col, 0, 1)
        h.addWidget(red_col, 0, 2)
        h.setColumnMinimumWidth(1, 110)
        h.setColumnMinimumWidth(2, 110)
        lay.addWidget(header)

        grid_host = QWidget()
        self.score_grid = QGridLayout(grid_host)
        self.score_grid.setContentsMargins(0, 0, 0, 0)
        self.score_grid.setSpacing(0)
        self.score_grid.setColumnStretch(0, 1)
        self.score_grid.setColumnMinimumWidth(1, 110)
        self.score_grid.setColumnMinimumWidth(2, 110)
        self.blue_cells: dict[str, QLabel] = {}
        self.red_cells: dict[str, QLabel] = {}
        for r, (key, label, icon_path) in enumerate(SCORE_CATEGORIES):
            self._add_score_row(r, key, label, icon_path)
            self.score_grid.setRowStretch(r, 1)
        lay.addWidget(grid_host, stretch=1)

        lay.addWidget(self._build_flights_footer())
        return board

    def _add_score_row(self, r: int, key: str, label: str, icon_path: str) -> None:
        cell = QWidget()
        cl = QHBoxLayout(cell)
        cl.setContentsMargins(16, 0, 16, 0)
        cl.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(
            QPixmap(icon_path).scaledToHeight(
                18, Qt.TransformationMode.SmoothTransformation
            )
        )
        icon.setFixedWidth(22)
        cl.addWidget(icon)
        cl.addWidget(_label(label, "mip-row-label"))
        cl.addStretch(1)
        self.score_grid.addWidget(cell, r, 0)

        blue = _label("0", "mip-num-blue")
        red = _label("0", "mip-num-red")
        blue.setAlignment(Qt.AlignmentFlag.AlignCenter)
        red.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_grid.addWidget(blue, r, 1)
        self.score_grid.addWidget(red, r, 2)
        self.blue_cells[key] = blue
        self.red_cells[key] = red

    def _build_flights_footer(self) -> QWidget:
        foot = QWidget()
        foot.setProperty("style", "mip-flights")
        lay = QHBoxLayout(foot)
        lay.setContentsMargins(16, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(_label("FLIGHTS", "mip-stat-label"))

        self.cnt_airborne = _label("0", "mip-counter-num")
        self.cnt_combat = _label("0", "mip-counter-num")
        self.cnt_waiting = _label("0", "mip-counter-num")
        for num, cap in [
            (self.cnt_airborne, "airborne"),
            (self.cnt_combat, "in combat"),
            (self.cnt_waiting, "waiting"),
        ]:
            cell = QWidget()
            c = QHBoxLayout(cell)
            c.setContentsMargins(0, 8, 0, 8)
            c.setSpacing(6)
            c.addStretch(1)
            c.addWidget(num)
            c.addWidget(_label(cap, "mip-counter-label"))
            c.addStretch(1)
            lay.addWidget(cell, stretch=1)
        return foot

    # ---- feed ------------------------------------------------------------ #
    def _build_feed(self) -> QFrame:
        feed = QFrame()
        feed.setProperty("style", "mip-feed")
        feed.setFixedWidth(360)
        lay = QVBoxLayout(feed)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = QWidget()
        header.setProperty("style", "mip-feed-header")
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 14, 18, 14)
        h.setSpacing(9)
        self.feed_dot = QLabel("●")
        self.feed_dot.setStyleSheet("color:#82A466; font-size:10px;")
        h.addWidget(self.feed_dot)
        h.addWidget(_label("LIVE EVENTS", "mip-stat-label"))
        h.addStretch(1)
        h.addWidget(_label("~15s behind DCS", "mip-event-time"))
        lay.addWidget(header)

        self.feed_list = QListWidget()
        self.feed_list.setProperty("style", "mip-feed-list")
        self.feed_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.feed_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.feed_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        lay.addWidget(self.feed_list, stretch=1)
        return feed

    def prepend_event(
        self, icon_path: str, text: str, verb: str, side: str, time_str: str
    ) -> None:
        # Don't pass the list to the ctor (that appends); build detached then
        # insert at the top so the newest event leads the feed.
        item = QListWidgetItem()
        row = EventRow(icon_path, text, verb, side, time_str)
        item.setSizeHint(row.sizeHint())
        self.feed_list.insertItem(0, item)
        self.feed_list.setItemWidget(item, row)
        while self.feed_list.count() > 200:
            self.feed_list.takeItem(self.feed_list.count() - 1)

    def prepend_divider(self, text: str) -> None:
        item = QListWidgetItem()
        lbl = _label(text, "mip-feed-divider")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setSizeHint(lbl.sizeHint())
        self.feed_list.insertItem(0, item)
        self.feed_list.setItemWidget(item, lbl)

    # ---- footer ---------------------------------------------------------- #
    def _build_footer(self) -> QFrame:
        bar = QFrame()
        bar.setProperty("style", "mip-footer")
        self._footer_lay = QHBoxLayout(bar)
        self._footer_lay.setContentsMargins(22, 14, 22, 14)
        self._footer_lay.setSpacing(12)

        self.hint = _label(
            "Mission in progress — DCS writes results every ~15s, so events lag a little",
            "mip-footer-hint",
        )
        self.accept_btn = QPushButton("Accept results")
        self.accept_btn.setProperty("style", "btn-success")
        self.manually_submit_btn = QPushButton("Manually Submit  [Advanced]")
        self.manually_submit_btn.setProperty("style", "btn-primary")
        self.abort_btn = QPushButton("Abort mission")
        self.abort_btn.setProperty("style", "btn-danger")

        self._layout_footer(complete=False)
        return bar

    def _layout_footer(self, complete: bool) -> None:
        while self._footer_lay.count():
            it = self._footer_lay.takeAt(0)
            if it.widget():
                it.widget().setParent(None)
        if complete:
            self._footer_lay.addWidget(self.accept_btn)
            self._footer_lay.addStretch(1)
            self._footer_lay.addWidget(self.manually_submit_btn)
            self._footer_lay.addWidget(self.abort_btn)
        else:
            self._footer_lay.addWidget(self.hint)
            self._footer_lay.addStretch(1)
            self._footer_lay.addWidget(self.manually_submit_btn)
            self._footer_lay.addWidget(self.abort_btn)
        self.accept_btn.setVisible(complete)
        self.hint.setVisible(not complete)

    # ---- public data wiring --------------------------------------------- #
    def update_clocks(
        self,
        real_start: datetime,
        real_now: datetime,
        sim_time: Optional[datetime],
        sim_elapsed: Optional[timedelta],
        turn: int,
    ) -> None:
        self.elapsed_value.setText(_fmt_td(real_now - real_start))
        self.rw_start.setText(real_start.strftime("%H:%M:%S"))
        self.rw_now.setText(real_now.strftime("%H:%M:%S"))
        if sim_time is not None:
            self.ig_time.setText(sim_time.strftime("%d %b %H:%M"))
        if sim_elapsed is not None:
            self.ig_elapsed.setText(_fmt_td(sim_elapsed))
        self.ingame_caption.setText(f"IN-GAME — TURN {turn}")

    def update_conditions(
        self, wind: str, clouds: str, temperature_c: Optional[float], tod: str
    ) -> None:
        self.wind_chip.setText(wind)
        self.cloud_chip.setText(clouds)
        self.temp_chip.setText(
            f"{round(temperature_c)}°C" if temperature_c is not None else "—"
        )
        self.tod_chip.setText(tod)

    def update_casualties(self, blue, red) -> None:
        own_total = enemy_total = 0
        for key, _label_, _icon in SCORE_CATEGORIES:
            b = getattr(blue, key, 0)
            r = getattr(red, key, 0)
            self.blue_cells[key].setText(str(b))
            self.red_cells[key].setText(str(r))
            own_total += b
            enemy_total += r
        self.own_total.setText(str(own_total))
        self.enemy_total.setText(str(enemy_total))
        self._set_ratio(own_total, enemy_total)

    def update_flights(self, airborne: int, in_combat: int, waiting: int) -> None:
        self.cnt_airborne.setText(str(airborne))
        self.cnt_combat.setText(str(in_combat))
        self.cnt_waiting.setText(str(waiting))

    def ingest_debriefing(self, debriefing: Debriefing) -> None:
        """Update casualties from a fresh (cumulative) debriefing and prepend any
        new events to the feed since the previous poll."""
        blue_counts = debriefing.loss_counts(Player.BLUE)
        red_counts = debriefing.loss_counts(Player.RED)
        self.update_casualties(blue_counts, red_counts)

        # DCS mission elapsed (from the Lua model_time); the campaign sim is paused
        # while the player flies, so sim_controller.elapsed_time would stay frozen.
        mt = getattr(debriefing.state_data, "model_time", None)
        if mt is not None:
            self.ig_elapsed.setText(_fmt_td(timedelta(seconds=mt)))

        now = datetime.now().strftime("%H:%M:%S")

        # new air losses, attributed with killer + weapon when DCS reported them.
        # Keyed by id(loss): FlyingUnit isn't hashable (holds a Pilot dataclass).
        kill_info = getattr(debriefing, "kill_info_by_unit_id", {})
        player_losses = debriefing.air_losses.player
        for loss in player_losses[self._shown_blue_air :]:
            self._emit_air_loss(loss, kill_info.get(id(loss)), "blue", "LOST", now)
        self._shown_blue_air = len(player_losses)

        enemy_losses = debriefing.air_losses.enemy
        for loss in enemy_losses[self._shown_enemy_air :]:
            self._emit_air_loss(loss, kill_info.get(id(loss)), "red", "DESTROYED", now)
        self._shown_enemy_air = len(enemy_losses)

        # base captures
        for capture in debriefing.base_captures:
            key = getattr(capture.control_point, "name", str(capture))
            if key in self._seen_captures:
                continue
            self._seen_captures.add(key)
            blue = getattr(
                getattr(capture, "captured_by_player", None), "is_blue", True
            )
            side = "blue" if blue else "red"
            self.prepend_event(
                ICON_CAPTURE,
                str(capture.control_point),
                f"CAPTURED BY {'BLUE' if blue else 'RED'}",
                side,
                now,
            )

        # ground/static losses: per side + unit type + killer/weapon when DCS
        # reported one. The categorised lists (not the raw killed_ground_units bucket)
        # match the scoreboard and exclude the thousands of untracked deaths.
        ground_losses = getattr(debriefing, "ground_losses", None)
        if ground_losses is not None:
            self._ingest_ground_losses(ground_losses, now, kill_info)

        if debriefing.state_data.mission_ended and not self._completed:
            self.set_complete(True)

    def _ingest_ground_losses(self, gl, now: str, kill_info: dict) -> None:
        # (side, key, list, label, typed) — typed categories carry a unit type.
        categories = [
            (
                "blue",
                "p_front",
                getattr(gl, "player_front_line", []),
                "front line",
                True,
            ),
            ("red", "e_front", getattr(gl, "enemy_front_line", []), "front line", True),
            ("blue", "p_convoy", getattr(gl, "player_convoy", []), "convoy", True),
            ("red", "e_convoy", getattr(gl, "enemy_convoy", []), "convoy", True),
            (
                "blue",
                "p_ship",
                getattr(gl, "player_cargo_ships", []),
                "cargo ship",
                False,
            ),
            (
                "red",
                "e_ship",
                getattr(gl, "enemy_cargo_ships", []),
                "cargo ship",
                False,
            ),
            (
                "blue",
                "p_obj",
                getattr(gl, "player_ground_objects", []),
                "ground object",
                False,
            ),
            (
                "red",
                "e_obj",
                getattr(gl, "enemy_ground_objects", []),
                "ground object",
                False,
            ),
            ("blue", "p_scen", getattr(gl, "player_scenery", []), "structure", False),
            ("red", "e_scen", getattr(gl, "enemy_scenery", []), "structure", False),
        ]
        for side, key, items, label, typed in categories:
            shown = self._shown_ground_by_cat.get(key, 0)
            new_items = items[shown:]
            self._shown_ground_by_cat[key] = len(items)
            if not new_items:
                continue
            # Build one row string per unit (type + killer/weapon when known), then
            # collapse identical rows into "Nx ..." so we keep per-unit attribution
            # without spamming duplicate lines.
            groups: dict[str, int] = {}
            for it in new_items:
                name = (
                    self._unit_type_name(getattr(it, "unit_type", None))
                    if typed
                    else None
                ) or label.capitalize()
                row = f"{name} ({label})" if typed else name
                killer = self._format_killer(kill_info.get(id(it)), "destroyed by")
                if killer:
                    row = f"{row} — {killer}"
                groups[row] = groups.get(row, 0) + 1
            for row, count in groups.items():
                text = f"{count}x {row}" if count > 1 else row
                self.prepend_event(ICON_GROUND, text, "DESTROYED", side, now)

    @staticmethod
    def _unit_type_name(unit_type) -> Optional[str]:
        if unit_type is None:
            return None
        for attr in ("name", "display_name"):
            value = getattr(unit_type, attr, None)
            if value:
                return str(value)
        return str(unit_type)

    def _emit_air_loss(
        self, loss, detail, side: str, killed_verb: str, now: str
    ) -> None:
        """One air-loss feed row. 'shot down by ...' + LOST/DESTROYED when DCS
        reported a real shooter; otherwise CRASHED (no kill, or a collision)."""
        base = self._air_base_text(loss)
        killer = self._format_killer(detail)
        if killer:
            self.prepend_event(ICON_AIR, f"{base} — {killer}", killed_verb, side, now)
        else:
            self.prepend_event(ICON_AIR, base, "CRASHED", side, now)

    @staticmethod
    def _air_base_text(loss) -> str:
        try:
            ac = loss.flight.unit_type.display_name
        except Exception:
            ac = "Aircraft"
        try:
            return f"{ac} from {loss.flight.squadron}"
        except Exception:
            return ac

    @staticmethod
    def _format_killer(detail, verb: str = "shot down by") -> Optional[str]:
        """Readable '<verb> ...' for a real shooter, or None.

        None means no shooter was credited (it crashed) OR the 'weapon' DCS
        reported is the initiator aircraft itself — i.e. a collision/ram, not a
        kill (e.g. an unarmed CH-47 'killing' a parked Apache, or F/A-18 'killing'
        F/A-18). For air losses those read as CRASHED, not a bogus kill.
        """
        if not detail:
            return None
        initiator_type = detail.get("initiator_type")
        weapon_raw = detail.get("weapon")
        if weapon_raw and weapon_raw == initiator_type:
            return None  # collision: the "weapon" is the aircraft itself
        who = detail.get("initiator_player") or _prettify_dcs_name(initiator_type)
        weapon = _prettify_dcs_name(weapon_raw)
        if who and weapon:
            return f"{verb} {who} ({weapon})"
        if who:
            return f"{verb} {who}"
        if weapon:
            return f"hit by {weapon}"
        return None

    # ---- state switch ---------------------------------------------------- #
    def set_complete(self, complete: bool) -> None:
        self._completed = complete
        self.setProperty("state", "complete" if complete else "in-progress")
        self.style().unpolish(self)
        self.style().polish(self)
        if complete:
            self._spinner_movie.stop()
            self.spinner.setMovie(None)
            self.spinner.setPixmap(
                QPixmap(ICON_CHECK).scaledToHeight(
                    26, Qt.TransformationMode.SmoothTransformation
                )
            )
            self.title.setText("MISSION COMPLETE")
            self.subtitle.setText("RESULTS READY — REVIEW & ACCEPT TO PROCESS THE TURN")
            self.feed_dot.setStyleSheet("color:#6F7F8B; font-size:10px;")
            self.prepend_divider("—— MISSION ENDED ——")
        self._layout_footer(complete=complete)

    # ---- scrims ---------------------------------------------------------- #
    def install_scrims(self, surfaces: list[QWidget], overlay_parent: QWidget) -> None:
        for s in surfaces:
            if s is not None:
                self._scrims.append(DimScrim(s, overlay_parent))

    def remove_scrims(self) -> None:
        for s in self._scrims:
            s.hide()
            s.deleteLater()
        self._scrims.clear()
