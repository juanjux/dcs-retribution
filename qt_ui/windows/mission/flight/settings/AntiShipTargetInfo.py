"""Per-flight target selector for an Anti-Ship flight.

Lets the user pick which ship the flight should target first. The dropdown is
pre-selected to the round-robin pick (same logic the mission generator uses);
changing the selection sets an explicit override that the generator will honour
(see game/missiongenerator/aircraft/waypoints/antishipingress.py).

Hidden for non-Anti-Ship flights.
"""

from typing import List, Tuple

from PySide6.QtWidgets import QComboBox, QGroupBox, QLabel, QVBoxLayout

from game.ato.flight import Flight
from game.ato.flighttype import FlightType
from game.ato.package import Package
from game.theater import NavalControlPoint, TheaterGroundObject


class AntiShipTargetInfo(QGroupBox):
    def __init__(self, flight: Flight, package: Package) -> None:
        super().__init__("Anti-Ship target")
        self.flight = flight
        self.package = package

        layout = QVBoxLayout()
        self.setLayout(layout)

        if flight.flight_type != FlightType.ANTISHIP:
            self.setVisible(False)
            return

        target = package.target
        if isinstance(target, NavalControlPoint):
            tgo_groups = target.find_main_tgo().groups
        elif isinstance(target, TheaterGroundObject):
            tgo_groups = target.groups
        else:
            layout.addWidget(
                QLabel(f"Unexpected target type: {type(target).__name__}")
            )
            return

        live: List[Tuple[int, str]] = []
        dead: List[Tuple[int, str]] = []
        for g in tgo_groups:
            for u in g.units:
                (live if u.alive else dead).append((u.id, u.name))

        if not live:
            layout.addWidget(QLabel("No live units in target."))
            return

        # Round-robin pick (matches the mission generator's logic). Used as the
        # default selection when there is no explicit override yet.
        antiship_flights = [
            f for f in package.flights if f.flight_type == FlightType.ANTISHIP
        ]
        try:
            rr_idx = antiship_flights.index(flight)
        except ValueError:
            rr_idx = 0
        rr_offset = rr_idx % len(live)
        rr_default_unit_id = live[rr_offset][0]

        # If a stored override points at a unit that is now dead, ignore it so
        # we don't pre-select something that won't actually be hit.
        live_ids = {uid for uid, _ in live}
        initial_unit_id = (
            flight.target_unit_id_override
            if flight.target_unit_id_override in live_ids
            else rr_default_unit_id
        )

        layout.addWidget(QLabel("First target (round-robin default):"))
        self.combo = QComboBox()
        initial_index = 0
        for i, (uid, name) in enumerate(live):
            tag = "  (round-robin)" if uid == rr_default_unit_id else ""
            self.combo.addItem(f"{str(uid).zfill(4)} | {name}{tag}", uid)
            if uid == initial_unit_id:
                initial_index = i
        self.combo.setCurrentIndex(initial_index)
        # currentIndexChanged only fires on actual changes, so opening the
        # dialog without touching the dropdown does not set an override.
        self.combo.currentIndexChanged.connect(  # type: ignore[attr-defined]
            self._on_change
        )
        layout.addWidget(self.combo)

        if dead:
            layout.addWidget(QLabel("Filtered out (dead):"))
            for uid, name in dead:
                layout.addWidget(QLabel(f"   {str(uid).zfill(4)} | {name} [DEAD]"))

    def _on_change(self, _index: int) -> None:
        self.flight.target_unit_id_override = self.combo.currentData()
