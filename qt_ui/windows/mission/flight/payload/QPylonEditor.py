import logging
import operator
from typing import Optional

from PySide6.QtWidgets import QComboBox, QWidget, QHBoxLayout, QPushButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from game import Game
from game.ato.flight import Flight
from game.ato.flightmember import FlightMember
from game.ato.loadouts import Loadout, aargm_er_active
from game.data.weapons import Pylon, Weapon
from .QWeaponSettingsDialog import QWeaponSettingsDialog


class QPylonEditor(QWidget):
    def __init__(
        self, game: Game, flight: Flight, flight_member: FlightMember, pylon: Pylon
    ) -> None:
        super().__init__()
        self.flight = flight
        self.flight_member = flight_member
        self.pylon = pylon
        self.game = game
        self.has_added_clean_item = False

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create combobox for weapon selection
        self.weapon_combo = QComboBox()
        current = self.flight_member.loadout.pylons.get(self.pylon.number)

        self.weapon_combo.addItem("None", None)
        if self.game.settings.restrict_weapons_by_date:
            weapons = pylon.available_on(
                self.game.date, flight.squadron.coalition.faction
            )
        else:
            weapons = pylon.allowed
        allowed = self._with_aargm_er(sorted(weapons, key=operator.attrgetter("name")))
        for i, weapon in enumerate(allowed):
            self.weapon_combo.addItem(self._weapon_label(weapon), weapon)
            if current == weapon:
                self.weapon_combo.setCurrentIndex(i + 1)

        self.weapon_combo.currentIndexChanged.connect(self.on_pylon_change)
        layout.addWidget(self.weapon_combo, 1)

        # Create settings button (initially hidden)
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon.fromTheme("preferences-system"))
        self.settings_button.setText("⚙")  # Gear emoji as fallback
        self.settings_button.setMaximumWidth(30)
        self.settings_button.setToolTip("Configure weapon settings")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.settings_button.setVisible(False)
        layout.addWidget(self.settings_button)

        self.update_settings_button_visibility()

    def _with_aargm_er(self, allowed: list[Weapon]) -> list[Weapon]:
        # The SYNTAX AARGM-ER mod only wires {PPC_AGM-88G} onto the F/A-18C's pylons; when
        # it also applies to a Super Hornet, offer it on that airframe's HARM-capable
        # pylons too so it shows in the dropdown (the default loadout already mounts it).
        mods = getattr(self.flight.squadron.coalition.faction, "mod_settings", None)
        if not aargm_er_active(mods, self.flight.unit_type.dcs_unit_type.id):
            return allowed
        aargm = Weapon.with_clsid("{PPC_AGM-88G}")
        if aargm is None or aargm in allowed:
            return allowed
        if not any(w.weapon_group.name == "AGM-88C HARM" for w in allowed):
            return allowed
        return allowed + [aargm]

    def _weapon_label(self, weapon: Weapon) -> str:
        mods = getattr(self.flight.squadron.coalition.faction, "mod_settings", None)
        aircraft_id = self.flight.unit_type.dcs_unit_type.id
        # SYNTAX AGM-88G AARGM-ER mod: clear mod-attributed name on any F/A-18 the mod
        # applies to (base toggle = all Hornets, realistic toggle = Super Hornets only).
        if weapon.clsid == "{PPC_AGM-88G}" and aargm_er_active(mods, aircraft_id):
            return "AGM-88G AARGM-ER High Speed Anti-Radiation Missile (SYNTAX mod)"
        # SYNTAX AGM-158C LRASM mod: it redefines the {AGM_84D} Harpoon in place, so any
        # {AGM_84D} carrier (the Hornet family) now fires a LRASM -- label it as such.
        if weapon.clsid == "{AGM_84D}" and getattr(mods, "fa18c_lrasm", False):
            return "AGM-158C LRASM Long Range Anti-Ship Missile (SYNTAX mod)"
        # SYNTAX AGM-158B JASSM-ER mod: it redefines the {AGM-154A} JSOW-A in place, so any
        # {AGM-154A} carrier (F/A-18C, F-15E, F-16) now fires a JASSM-ER -- label it so.
        if weapon.clsid == "{AGM-154A}" and getattr(mods, "fa18c_jassm", False):
            return "AGM-158B JASSM-ER Long Range Cruise Missile (SYNTAX mod)"
        return weapon.name

    def update_settings_button_visibility(self) -> None:
        """Show/hide settings button based on whether current weapon has settings."""
        weapon = self.weapon_combo.currentData()
        if weapon is not None and weapon.has_settings():
            self.settings_button.setVisible(True)
        else:
            self.settings_button.setVisible(False)

    def open_settings_dialog(self) -> None:
        """Open the weapon settings dialog."""
        weapon = self.weapon_combo.currentData()
        if weapon is None:
            return

        current_settings = self.flight_member.loadout.pylon_settings.get(
            self.pylon.number
        )

        dialog = QWeaponSettingsDialog(weapon, current_settings, self)
        if dialog.exec():
            # Save the settings
            settings_dict = dialog.get_settings_dict()
            self.flight_member.loadout.pylon_settings[self.pylon.number] = settings_dict
            logging.info(
                f"Updated settings for pylon {self.pylon.number}: {settings_dict}"
            )

    def on_pylon_change(self) -> None:
        selected: Optional[Weapon] = self.weapon_combo.currentData()
        self.flight_member.loadout.pylons[self.pylon.number] = selected

        # Clear settings when weapon changes
        if self.pylon.number in self.flight_member.loadout.pylon_settings:
            del self.flight_member.loadout.pylon_settings[self.pylon.number]

        self.update_settings_button_visibility()

        if selected is None:
            logging.debug(f"Pylon {self.pylon.number} emptied")
        else:
            logging.debug(f"Pylon {self.pylon.number} changed to {selected.name}")

    def weapon_from_loadout(self, loadout: Loadout) -> Optional[Weapon]:
        weapon = loadout.pylons.get(self.pylon.number)
        if weapon is None:
            return None
        # TODO: Fix pydcs to support the <CLEAN> "weapon".
        # These are not exported in the pydcs weapon map, which causes the pydcs pylon
        # exporter to fail to include them in the supported list. Since they aren't
        # known to be compatible (and we can't show them as compatible for *every*
        # pylon, because they aren't), we won't have populated a "Clean" weapon when
        # creating the selection list, so it's not selectable. To work around this, add
        # the item to the list the first time it's encountered for the pylon.
        #
        # A similar hack exists in Pylon to support forcibly equipping this even when
        # it's not known to be compatible.
        if weapon.clsid == "<CLEAN>":
            if not self.has_added_clean_item:
                self.weapon_combo.addItem("Clean", weapon)
                self.has_added_clean_item = True
        return weapon

    def matching_weapon_name(self, loadout: Loadout) -> str:
        if self.game.settings.restrict_weapons_by_date:
            # Always apply target overrides for AI, only for players if setting is enabled
            should_apply_overrides = (
                not self.flight_member.is_player
                or self.game.settings.apply_target_overrides_to_loadouts
            )
            target = self.flight.package.target if should_apply_overrides else None
            loadout = loadout.degrade_for_date(
                self.flight.unit_type,
                self.game.date,
                self.flight.squadron.coalition.faction,
                target,
            )
        weapon = self.weapon_from_loadout(loadout)
        if weapon is None:
            return "None"
        return self._weapon_label(weapon)

    def set_flight_member(self, flight_member: FlightMember) -> None:
        self.flight_member = flight_member
        self.set_from(self.flight_member.loadout)

    def set_from(self, loadout: Loadout) -> None:
        self.weapon_combo.setCurrentText(self.matching_weapon_name(loadout))
        self.update_settings_button_visibility()
