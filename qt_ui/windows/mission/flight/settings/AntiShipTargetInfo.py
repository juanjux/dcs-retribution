"""Debug widget showing the rotated AttackUnit target list for an Anti-Ship flight.

Mirrors the round-robin logic in
game/missiongenerator/aircraft/waypoints/antishipingress.py so the user can see,
at plan time, which ship each flight in the package will target first when the
mission is generated. Hidden for non-Anti-Ship flights.

Read-only for now; intended as the foundation for a manual target selector.
"""

from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from game.ato.flight import Flight
from game.ato.flighttype import FlightType
from game.ato.package import Package
from game.theater import NavalControlPoint, TheaterGroundObject


class AntiShipTargetInfo(QGroupBox):
    def __init__(self, flight: Flight, package: Package) -> None:
        super().__init__("Anti-Ship target (debug)")
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
            layout.addWidget(QLabel(f"Unexpected target type: {type(target).__name__}"))
            return

        all_units = []  # (unit_id, name, alive)
        for g in tgo_groups:
            for u in g.units:
                all_units.append((u.id, u.name, u.alive))

        live = [(uid, name) for uid, name, alive in all_units if alive]
        dead = [(uid, name) for uid, name, alive in all_units if not alive]

        if not live:
            layout.addWidget(QLabel("No live units in target."))
            return

        # Index among Anti-Ship flights only, to match what the mission
        # generator does (game/missiongenerator/aircraft/waypoints/antishipingress.py).
        antiship_flights = [
            f for f in package.flights if f.flight_type == FlightType.ANTISHIP
        ]
        try:
            idx = antiship_flights.index(flight)
        except ValueError:
            idx = 0
        offset = idx % len(live)
        rotated = live[offset:] + live[:offset]

        layout.addWidget(
            QLabel(
                f"Flight index (among Anti-Ship): {idx} of {len(antiship_flights)}  |  "
                f"Live units: {len(live)}  |  Rotation offset: {offset}"
            )
        )
        layout.addWidget(QLabel("Target order (first = primary):"))
        for i, (uid, name) in enumerate(rotated):
            marker = "→ " if i == 0 else "   "
            label = QLabel(f"{marker}{str(uid).zfill(4)} | {name}")
            if i == 0:
                font = label.font()
                font.setBold(True)
                label.setFont(font)
            layout.addWidget(label)

        if dead:
            layout.addWidget(QLabel("Filtered out (dead):"))
            for uid, name in dead:
                layout.addWidget(QLabel(f"   {str(uid).zfill(4)} | {name} [DEAD]"))
