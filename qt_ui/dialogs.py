"""Application-wide dialog management."""

from typing import Optional

import shiboken6
from PySide6.QtWidgets import QWidget

from game.ato.flight import Flight
from game.theater.missiontarget import MissionTarget
from .models import GameModel, PackageModel
from .windows.mission.QEditFlightDialog import QEditFlightDialog
from .windows.mission.QPackageDialog import (
    QEditPackageDialog,
    QNewPackageDialog,
)


class Dialog:
    """Dialog management singleton.

    Opens dialogs and keeps references to dialog windows so that their creators
    do not need to worry about the lifetime of the dialog object, and can open
    dialogs without needing to have their own reference to common data like the
    game model.
    """

    #: The game model. Is only None before initialization, as the game model
    #: itself is responsible for handling the case where no game is loaded.
    game_model: Optional[GameModel] = None

    new_package_dialog: Optional[QNewPackageDialog] = None
    edit_package_dialog: Optional[QEditPackageDialog] = None
    edit_flight_dialog: Optional[QEditFlightDialog] = None

    @classmethod
    def set_game(cls, game_model: GameModel) -> None:
        """Sets the game model."""
        cls.game_model = game_model

    @classmethod
    def _remember(cls, name: str, dialog: QWidget) -> None:
        """Hold the dialog, and let go of it when Qt destroys it.

        These are parented to whatever opened them, so closing that window deletes
        the C++ object underneath while this class goes on holding the Python
        wrapper. Touching one of those afterwards raises, which is how a closed
        package dialog left the flight editor unopenable for the rest of the session.
        """
        setattr(cls, name, dialog)
        dialog.destroyed.connect(lambda *_: cls._forget(name, dialog))

    @classmethod
    def _forget(cls, name: str, dialog: QWidget) -> None:
        # By identity, and without touching the object: it is being destroyed, and a
        # newer dialog may already have taken its place here.
        if getattr(cls, name, None) is dialog:
            setattr(cls, name, None)

    @classmethod
    def live_edit_flight_dialog(cls) -> Optional[QEditFlightDialog]:
        """The flight editor, if there is one and Qt has not deleted it."""
        dialog = cls.edit_flight_dialog
        if dialog is None:
            return None
        if not shiboken6.isValid(dialog):
            cls.edit_flight_dialog = None
            return None
        return dialog

    @classmethod
    def open_new_package_dialog(cls, mission_target: MissionTarget, parent=None):
        """Opens the dialog to create a new package with the given target."""
        cls._remember(
            "new_package_dialog",
            QNewPackageDialog(cls.game_model, mission_target, parent=parent),
        )
        assert cls.new_package_dialog is not None
        cls.new_package_dialog.show()

    @classmethod
    def open_edit_package_dialog(cls, package_model: PackageModel):
        """Opens the dialog to edit the given package."""
        cls._remember(
            "edit_package_dialog", QEditPackageDialog(cls.game_model, package_model)
        )
        assert cls.edit_package_dialog is not None
        cls.edit_package_dialog.show()

    @classmethod
    def open_edit_flight_dialog(
        cls, package_model: PackageModel, flight: Flight, parent=None
    ) -> None:
        """Opens the dialog to edit the given flight."""
        cls._remember(
            "edit_flight_dialog",
            QEditFlightDialog(cls.game_model, package_model, flight, parent=parent),
        )
        assert cls.edit_flight_dialog is not None
        cls.edit_flight_dialog.show()
