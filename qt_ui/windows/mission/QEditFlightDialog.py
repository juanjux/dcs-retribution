"""Dialog window for editing flights."""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QInputDialog,
    QMessageBox,
    QVBoxLayout,
)

from game.ato.flight import Flight
from game.ato.flightplans.planningerror import PlanningError
from game.ato.flightplans.refueledit import (
    RefuelVerdict,
    add_refuel_waypoint,
    can_offer_a_tanker,
    plan_tanker_for,
    planned_tanker_name,
    refuel_verdict,
    refuelling_system,
    remove_refuel_waypoint,
)
from game.squadrons import Squadron
from game.server import EventStream
from game.sim import GameUpdateEvents
from qt_ui.models import GameModel, PackageModel
from qt_ui.uiconstants import EVENT_ICONS
from qt_ui.windows.mission.flight.QFlightPlanner import QFlightPlanner


class QEditFlightDialog(QDialog):
    """Dialog window for editing flight plans and loadouts."""

    def __init__(
        self,
        game_model: GameModel,
        package_model: PackageModel,
        flight: Flight,
        parent=None,
    ) -> None:
        super().__init__(parent=parent)

        self.game_model = game_model
        self.flight = flight
        self.package_model = package_model
        self.events = GameUpdateEvents()

        self.setWindowTitle("Edit flight")
        self.setWindowIcon(EVENT_ICONS["strike"])
        self.setModal(True)

        layout = QVBoxLayout()

        self.flight_planner = QFlightPlanner(package_model, flight, game_model)
        self.flight_planner.squadron_changed.connect(self.on_squadron_change)
        layout.addWidget(self.flight_planner)

        self.setLayout(layout)
        self.finished.connect(self.on_close)

    def on_squadron_change(self, flight: Flight):
        self.events = GameUpdateEvents().delete_flight(self.flight)
        self.events = self.events.new_flight(flight)
        self.game_model.ato_model.client_slots_changed.emit()
        self.flight = flight
        self.reject()
        new_dialog = QEditFlightDialog(
            self.game_model, self.package_model, flight, self.parent()
        )
        new_dialog.show()

    def on_close(self, _result) -> None:
        self._recreate_package_if_standoff_changed()
        self._offer_to_move_the_refuelling_waypoint()
        self.events = self.events.update_flight(self.flight)
        EventStream.put_nowait(self.events)
        self.game_model.ato_model.client_slots_changed.emit()

    def _recreate_package_if_standoff_changed(self) -> None:
        """Move the ingress point when the package's stand-off range changed.

        Editing the payload does not rebuild the flight plan, so the ingress point can
        be left at a distance that no longer matches the loadout (e.g. a Kh-22 was
        added or removed). The package waypoints remember the stand-off range they were
        built with, so if it now differs we offer to regenerate the package's flight
        plans (which resets their routes).
        """
        package = self.flight.package
        waypoints = package.waypoints
        if waypoints is None:
            return
        if waypoints.standoff_range == package.max_standoff_range():
            return

        result = QMessageBox.question(
            self,
            "Update flight plan?",
            (
                "The stand-off weapons in this package changed, so the ingress point "
                "should move to match the new launch range. This will regenerate the "
                "flight plan(s) for the package and reset any manual route changes. "
                "Continue?"
            ),
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        package.waypoints = None
        for flight in package.flights:
            try:
                flight.recreate_flight_plan()
                self.events = self.events.update_flight(flight)
            except PlanningError:
                logging.exception(
                    "Could not regenerate flight plan after stand-off change"
                )

    def _offer_to_move_the_refuelling_waypoint(self) -> None:
        """Ask again about the tanker, now that the player has had their way.

        The planner decides this while it builds the plan, and never again. Taking the
        drop tanks off, or taking the route down low, leaves a flight short of fuel
        with nothing noticing -- which is exactly what it looks like from the outside:
        "I made it not have enough and it did not plan me a tanker."

        Unlike the stand-off question above, saying yes here does NOT rebuild the plan.
        Rebuilding would throw away the edits that made the flight short in the first
        place, which is the opposite of helpful.
        """
        verdict = refuel_verdict(self.flight)
        if verdict is RefuelVerdict.NOTHING_TO_DO:
            return

        if verdict is RefuelVerdict.SHOULD_ADD:
            tanker = planned_tanker_name(self.flight)
            if tanker is not None:
                found = f"{tanker} is flying this turn, so there is one to meet."
            else:
                found = (
                    "No tanker is planned this turn, so the waypoint will do nothing "
                    "until you plan one."
                )
            title = "Add a refuelling waypoint?"
            question = (
                "This flight no longer has the fuel for its route. A refuelling "
                f"waypoint can be added on the way home. {found}"
                "\n\nThe rest of the route is left exactly as you set it."
            )
        else:
            title = "Remove the refuelling waypoint?"
            question = (
                "This flight now carries comfortably more fuel than its route asks "
                "for, so it no longer needs the detour to the tanker. Remove the "
                "refuelling waypoint?"
                "\n\nThe rest of the route is left exactly as you set it."
            )

        result = QMessageBox.question(
            self,
            title,
            question,
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        if verdict is RefuelVerdict.SHOULD_ADD:
            changed = add_refuel_waypoint(self.flight)
            if changed:
                self._offer_to_plan_a_tanker()
        else:
            changed = remove_refuel_waypoint(self.flight)
        if changed:
            self.events = self.events.update_flight(self.flight)

    def _offer_to_plan_a_tanker(self) -> None:
        """Having given the flight somewhere to meet a tanker, offer it a tanker.

        The waypoint alone is not fuel: the DCS task sends the group to the *nearest*
        tanker it can find, so if the turn has none airborne it finds nothing. If the
        wing has one sitting idle, planning it into this package puts its orbit at the
        very point the waypoint was placed at, which is the only way to be sure the
        two agree.
        """
        available = can_offer_a_tanker(self.flight)
        if not available:
            return

        squadron = self._choose_tanker(available)
        if squadron is None:
            return

        self._plan_the_tanker(squadron)

    def _choose_tanker(self, available: list[Squadron]) -> Optional[Squadron]:
        """Which tanker to send, when the wing has more than one kind sitting idle.

        Nothing in the unit data says whether a receiver has a probe or a receptacle,
        so this is not a choice that can be made for the player -- send a Hornet to a
        boom-only KC-135 and it comes home empty. Each option says which system it
        offers; picking is a second's work for someone who knows what they are flying.
        """
        if len(available) == 1:
            squadron = available[0]
            result = QMessageBox.question(
                self,
                "Add a tanker to this package?",
                (
                    f"{squadron.name} has a {squadron.aircraft} free at "
                    f"{squadron.location}, refuelling by {refuelling_system(squadron)}."
                    " It can be planned into this package, orbiting at the refuelling "
                    "point, which is clear of enemy air defences.\n\n"
                    "Without one, the flight will go looking for whatever tanker "
                    "happens to be airborne."
                ),
                QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            return squadron if result == QMessageBox.StandardButton.Yes else None

        labels = [
            f"{squadron.aircraft} ({refuelling_system(squadron)}) —"
            f" {squadron.name} at {squadron.location}"
            for squadron in available
        ]
        choice, accepted = QInputDialog.getItem(
            self,
            "Add a tanker to this package?",
            (
                "A tanker can be planned into this package, orbiting at the refuelling "
                "point, which is clear of enemy air defences. Which one?\n\n"
                "A receiver with a probe cannot take fuel from a boom."
            ),
            labels,
            0,
            False,
        )
        if not accepted:
            return None
        return available[labels.index(choice)]

    def _plan_the_tanker(self, squadron: Squadron) -> None:
        tanker = plan_tanker_for(self.flight, squadron)
        self.package_model.add_flight(tanker)
        try:
            tanker.recreate_flight_plan()
            self.package_model.update_tot()
            self.events = self.events.new_flight(tanker)
        except PlanningError:
            logging.exception("Could not plan the tanker")
            self.package_model.delete_flight(tanker)
            QMessageBox.critical(
                self,
                "Could not plan the tanker",
                "The tanker could not be given a flight plan, so it has not been "
                "added. The refuelling waypoint is still there.",
                QMessageBox.StandardButton.Ok,
            )
