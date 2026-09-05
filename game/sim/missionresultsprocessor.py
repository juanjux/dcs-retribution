from __future__ import annotations

import logging
import random
from typing import Any, Iterator, Optional, TYPE_CHECKING

from game.debriefing import Debriefing
from game.squadrons.experience import (
    PilotDeath,
    PilotPromotion,
    PilotWound,
    WOUNDED_TURNS,
    XP_AIR_KILL,
    XP_DAMAGE_SHARE,
    XP_GROUND_KILL,
    XP_MISSION_COMPLETE,
    XP_SHIP_KILL,
    XP_UNKNOWN_KILL,
    XP_WOUNDED,
    building_xp,
    turns_phrase,
    survival_chance,
)
from game.ground_forces.combat_stance import CombatStance
from game.squadrons.pilot import Pilot
from game.squadrons.xplog import XpLog
from game.profiling import logged_duration
from game.theater import ControlPoint
from .gameupdateevents import GameUpdateEvents
from ..ato.airtaaskingorder import AirTaskingOrder

if TYPE_CHECKING:
    from ..game import Game
    from ..coalition import Coalition
    from ..ato.flight import Flight
    from ..dcs.aircrafttype import AircraftType
    from ..theater.missiontarget import MissionTarget


MINOR_DEFEAT_INFLUENCE = 0.1
DEFEAT_INFLUENCE = 0.3
STRONG_DEFEAT_INFLUENCE = 0.5


class MissionResultsProcessor:
    def __init__(self, game: Game) -> None:
        self.game = game
        # TEMPORARY: see game.squadrons.xplog. Remove with the rest of it.
        self._xp_log: Optional[XpLog] = None

    @property
    def xp_log(self) -> XpLog:
        """TEMPORARY: the turn's experience ledger, written out at the end of it."""
        if self._xp_log is None:
            self._xp_log = XpLog(getattr(self.game, "turn", "?"))
        return self._xp_log

    def commit(self, debriefing: Debriefing, events: GameUpdateEvents) -> None:
        with logged_duration("Committing mission results"):
            with logged_duration("commit_air_losses"):
                self.commit_air_losses(debriefing)
            with logged_duration("commit_pilot_experience"):
                self.commit_pilot_experience(debriefing)
            with logged_duration("commit_front_line_losses"):
                self.commit_front_line_losses(debriefing)
            with logged_duration("commit_motorpool_losses"):
                self.commit_motorpool_losses(debriefing)
            with logged_duration("commit_convoy_losses"):
                self.commit_convoy_losses(debriefing)
            with logged_duration("commit_cargo_ship_losses"):
                self.commit_cargo_ship_losses(debriefing)
            with logged_duration("commit_airlift_losses"):
                self.commit_airlift_losses(debriefing)
            with logged_duration("commit_ground_losses"):
                self.commit_ground_losses(debriefing, events)
            with logged_duration("commit_damaged_runways"):
                self.commit_damaged_runways(debriefing)
            with logged_duration("commit_cruise_missiles"):
                self.commit_cruise_missiles(debriefing)
            with logged_duration("commit_naval_magazines"):
                self.commit_naval_magazines(debriefing)
            # Score the front line before capturing bases: casualty_count
            # attributes a dead front-line unit to its origin CP regardless of
            # side, so a base's defenders (origin == that base) would be
            # miscounted as the new owner's casualties once a capture flips
            # ownership, turning a win into a defeat.
            with logged_duration("commit_front_line_battle_impact"):
                self.commit_front_line_battle_impact(debriefing, events)
            with logged_duration("commit_captures"):
                self.commit_captures(debriefing, events)
            # After captures: base ownership is final, so we can tell whether a
            # "remain at destination" assault reached a base we now hold.
            with logged_duration("commit_air_assault_remain"):
                self.commit_air_assault_remain(debriefing)
            with logged_duration("record_carcasses"):
                self.record_carcasses(debriefing)
            self.game.record_debrief(debriefing)

    def commit_air_losses(self, debriefing: Debriefing) -> None:
        for loss in debriefing.air_losses.losses:
            if self.game.settings.ignore_non_combat_air_losses and (
                debriefing.is_non_combat_loss(loss)
            ):
                # Campaign doctrine: a non-combat write-off (crash/collision/no
                # credited shooter) does not deplete the squadron or kill the pilot.
                logging.info(
                    f"Ignoring non-combat loss of {loss.flight.unit_type} from "
                    f"{loss.flight.squadron}"
                )
                continue
            if loss.pilot is not None and (
                not loss.pilot.player
                or not self.game.settings.invulnerable_player_pilots
            ):
                self._resolve_pilot_fate(loss, debriefing)
            squadron = loss.flight.squadron
            aircraft = loss.flight.unit_type
            available = squadron.owned_aircraft
            if available <= 0:
                logging.error(
                    f"Found killed {aircraft} from {squadron} but that airbase has "
                    "none available."
                )
                continue

            logging.info(f"{aircraft} destroyed from {squadron}")
            squadron.owned_aircraft -= 1
            squadron.destroyed_aircraft += 1

    def commit_air_assault_remain(self, debriefing: Debriefing) -> None:
        """Resolve helo air-assault flights flagged to remain at the objective.

        A "remain" flight is committed forward and never flies home, so its origin
        loses the whole flight -- no matter how the sim classified each airframe (kill,
        crash, or landed-and-abandoned). If we hold the objective once captures are
        resolved, the airframes that made it redeploy there (a free forward ferry);
        otherwise every one is written off. Must run after commit_captures so base
        ownership is final.
        """
        for coalition in self.game.coalitions:
            for package in coalition.ato.packages:
                for flight in package.flights:
                    if not getattr(flight, "remain_at_destination", False):
                        continue
                    if not flight.is_helo:
                        continue
                    origin = flight.squadron
                    # Take the whole flight off the origin. commit_air_losses already
                    # removed the losses it counts, so subtract only the remainder --
                    # otherwise a non-combat "crash" write-back silently keeps a
                    # committed helo that should be gone.
                    to_remove = flight.count - self._depleting_air_losses(
                        debriefing, flight
                    )
                    if to_remove > 0:
                        origin.owned_aircraft = max(
                            0, origin.owned_aircraft - to_remove
                        )
                    objective = self._objective_control_point(flight.package.target)
                    if objective is not None and objective.captured == coalition.player:
                        arrived = debriefing.air_losses.surviving_flight_members(flight)
                        if arrived > 0:
                            self._ferry_to_captured_base(
                                flight.unit_type, arrived, objective, coalition
                            )
                            logging.info(
                                f"{arrived} {flight.unit_type} remained at captured "
                                f"{objective} (from {origin})"
                            )
                    else:
                        where = objective.name if objective is not None else "objective"
                        logging.info(
                            f"Remain flight of {flight.unit_type} from {origin} lost: "
                            f"{where} not captured"
                        )

    def _depleting_air_losses(self, debriefing: Debriefing, flight: Flight) -> int:
        """This flight's air losses that commit_air_losses removed from the squadron,
        skipping the non-combat write-offs it forgives (so survivor math lines up)."""
        count = 0
        for loss in debriefing.air_losses.losses:
            if loss.flight != flight:
                continue
            if self.game.settings.ignore_non_combat_air_losses and (
                debriefing.is_non_combat_loss(loss)
            ):
                continue
            count += 1
        return count

    @staticmethod
    def _objective_control_point(target: MissionTarget) -> ControlPoint | None:
        if isinstance(target, ControlPoint):
            return target
        control_point = getattr(target, "control_point", None)
        return control_point if isinstance(control_point, ControlPoint) else None

    def _ferry_to_captured_base(
        self,
        aircraft: AircraftType,
        count: int,
        base: ControlPoint,
        coalition: Coalition,
    ) -> None:
        # Reinforce an existing squadron of the type already at the base...
        for squadron in base.squadrons:
            if squadron.aircraft == aircraft:
                squadron.owned_aircraft += count
                return
        # ...otherwise stand up a new squadron for the ferried aircraft.
        from ..ato import FlightType
        from ..squadrons.squadron import Squadron

        squadron_def = coalition.air_wing.squadron_def_generator.generate_for_aircraft(
            aircraft
        )
        squadron = Squadron.create_from(
            squadron_def,
            FlightType.AIR_ASSAULT,
            count,
            base,
            coalition,
            self.game,
        )
        squadron.owned_aircraft = count
        coalition.air_wing.add_squadron(squadron)

    def _resolve_pilot_fate(self, loss: Any, debriefing: Debriefing) -> None:
        """Kill the pilot, or let his rank save him, or let the medics reach him.

        Two rolls, in that order. The first is bought with rank and needs both Live
        Pilots and the rank survival switch; the second is flat and needs only Live
        Pilots, so a wound can still spare a pilot in a campaign that does not want
        rank deciding who lives. Neither switched on means losing the aircraft loses
        the pilot, exactly as before.
        """
        settings = self.game.settings
        pilot = loss.pilot
        squadron = loss.flight.squadron
        record = self._describe_loss(loss, debriefing)
        # However this ends for him, he did not bring the aircraft home.
        debriefing.pilot_outcomes.lost_aircraft.add(id(pilot))
        rolls = settings.live_pilots_enabled and settings.live_pilots_rank_survival
        chance = (
            survival_chance(squadron.pilot_skill(pilot), settings) if rolls else 0.0
        )
        survived = rolls and random.random() < chance

        def note(outcome: str) -> None:
            """One line per loss, written once both rolls are settled.

            Recording the first roll on its own said "died" about pilots the medics
            then saved two lines later.
            """
            if rolls or settings.live_pilots_enabled:
                self.xp_log.fate(
                    pilot, squadron, squadron.pilot_rank(pilot), chance, outcome
                )

        if survived:
            note("walked away")
            debriefing.pilot_outcomes.survivors.append(record)
            logging.info(f"{pilot.name} survived the loss of his aircraft")
            return

        if settings.live_pilots_enabled and (
            random.random() < settings.live_pilots_wounded_chance / 100
        ):
            turns = random.randint(*WOUNDED_TURNS)
            pilot.wound(turns)
            debriefing.pilot_outcomes.wounded.append(
                PilotWound(pilot.name, str(squadron), turns)
            )
            note(f"wounded, out for {turns_phrase(turns)}")
            logging.info(
                f"{pilot.name} was wounded and is out for {turns_phrase(turns)}"
            )
            return

        note("died")
        pilot.kill()
        debriefing.pilot_outcomes.deaths.append(record)

    def _describe_loss(self, loss: Any, debriefing: Debriefing) -> PilotDeath:
        squadron = loss.flight.squadron
        detail = debriefing.kill_info_by_unit_id.get(id(loss))
        killer, friendly = self._describe_killer(
            detail, debriefing, squadron.player.is_blue
        )
        return PilotDeath(
            pilot_name=loss.pilot.name if loss.pilot is not None else "Unknown pilot",
            squadron=str(squadron),
            aircraft=str(loss.flight.unit_type),
            killed_by=killer,
            friendly_fire=friendly,
        )

    def _describe_killer(
        self,
        detail: Optional[dict[str, Any]],
        debriefing: Debriefing,
        victim_is_blue: bool,
    ) -> tuple[Optional[str], bool]:
        """Name whoever did it, as precisely as the data allows.

        DCS credits exactly one initiator per kill and has no notion of an assist, so
        this is whoever landed the killing blow. In order of preference: the roster
        pilot behind the killing aircraft, the human's own name, the airframe or
        vehicle type. No initiator at all means nobody shot him down.
        """
        if not detail:
            return "a crash", False

        name: Optional[str] = None
        friendly = False
        initiator = detail.get("initiator")
        if initiator:
            killer = debriefing.unit_map.flight(str(initiator))
            if killer is not None:
                friendly = killer.flight.squadron.player.is_blue == victim_is_blue
                if killer.pilot is not None:
                    name = killer.pilot.name

        if name is None:
            name = detail.get("initiator_player") or detail.get("initiator_type")
        if name is None:
            return None, friendly

        airframe = detail.get("initiator_type")
        if airframe and airframe != name:
            name = f"{name} ({airframe})"
        weapon = detail.get("weapon")
        if weapon and weapon != airframe:
            name = f"{name} with {weapon}"
        return name, friendly

    def _victim_is_blue(self, victim: Any) -> Optional[bool]:
        """Which side the destroyed thing belonged to, where that can be established."""
        flight = getattr(victim, "flight", None)
        if flight is not None:
            return bool(flight.squadron.player.is_blue)
        for attr in ("origin", "airfield"):
            origin = getattr(victim, attr, None)
            if origin is not None and hasattr(origin, "captured"):
                return bool(origin.captured.is_blue)
        for attr in ("theater_unit", "ground_unit"):
            unit = getattr(victim, attr, None)
            tgo = getattr(unit, "ground_object", None)
            if tgo is not None:
                return bool(tgo.control_point.captured.is_blue)
        convoy = getattr(victim, "convoy", None)
        if convoy is not None:
            return bool(convoy.player_owned.is_blue)
        return None

    def _kill_xp(self, victim: Any) -> int:
        """What destroying this was worth.

        Proportionality comes from the pieces: a refinery is four platforms, each with
        its own death, so two of them is half a refinery. DCS reports no damage
        magnitude anywhere, so nothing divides an element any finer -- hurting one
        without destroying it is paid as an assist instead, at XP_DAMAGE_SHARE.
        """
        if victim is None:
            return 0
        if getattr(victim, "flight", None) is not None:
            return XP_AIR_KILL
        if getattr(victim, "convoy", None) is not None:
            return XP_GROUND_KILL
        if hasattr(victim, "unit_type") and getattr(victim, "origin", None) is not None:
            return XP_GROUND_KILL  # front line and motorpool vehicles

        unit = getattr(victim, "theater_unit", None) or getattr(
            victim, "ground_unit", None
        )
        if unit is None:
            return 0
        unit_type = getattr(unit, "unit_type", None)
        if unit_type is not None:
            from game.dcs.shipunittype import ShipUnitType

            if isinstance(unit_type, ShipUnitType):
                return XP_SHIP_KILL
            return XP_GROUND_KILL
        # No unit type: a static or a scenery objective, paid by what it is worth.
        tgo = getattr(unit, "ground_object", None)
        if tgo is None:
            return XP_UNKNOWN_KILL
        return building_xp(getattr(tgo, "category", None))

    def _credited_events(
        self, details: Any, debriefing: Debriefing
    ) -> Iterator[tuple[Pilot, str, Any]]:
        """(pilot, target name, target) for every record naming an aircrew and a victim.

        Shared by kills and hits, which the plugin writes in the same shape. Anything
        that cannot be resolved to a roster pilot is dropped, as is anything he did to
        his own side.
        """
        for detail in details:
            if not isinstance(detail, dict):
                continue
            initiator = detail.get("initiator")
            target = detail.get("target")
            if not initiator or not target:
                continue
            killer = debriefing.unit_map.flight(str(initiator))
            if killer is None or killer.pilot is None:
                continue
            victim = debriefing.resolve_killed_object(str(target))
            victim_blue = self._victim_is_blue(victim)
            if victim_blue is not None and (
                victim_blue == killer.flight.squadron.player.is_blue
            ):
                continue  # nobody is paid for shooting his own side
            yield killer.pilot, str(target), victim

    def _experience_from_kills(
        self, debriefing: Debriefing
    ) -> tuple[dict[int, int], set[tuple[int, str]]]:
        """What each pilot earned for what he destroyed, keyed by pilot identity.

        Also returns the (pilot, target) pairs it paid for, so the damage pass does not
        pay a second time for the hit that finished the job.
        """
        earned: dict[int, int] = {}
        credited: set[tuple[int, str]] = set()
        for pilot, target, victim in self._credited_events(
            debriefing.state_data.kill_details, debriefing
        ):
            credited.add((id(pilot), target))
            xp = self._kill_xp(victim)
            if xp:
                earned[id(pilot)] = earned.get(id(pilot), 0) + xp
                self.xp_log.award(pilot, xp, "destroyed", victim, target)
        return earned, credited

    def _experience_from_damage(
        self, debriefing: Debriefing, credited: set[tuple[int, str]]
    ) -> dict[int, int]:
        """A share of the kill for hurting something without finishing it.

        This is a real assist rather than a guess: DCS names the shooter on every hit,
        and the plugin records the first one each aircraft lands on each target, so a
        pilot is paid once for the destroyer he left burning however long he worked on
        it. The pilot credited with the kill is skipped -- that kill already paid him.
        """
        earned: dict[int, int] = {}
        for pilot, target, victim in self._credited_events(
            debriefing.state_data.hit_details, debriefing
        ):
            if (id(pilot), target) in credited:
                continue
            xp = int(self._kill_xp(victim) * XP_DAMAGE_SHARE)
            if xp:
                earned[id(pilot)] = earned.get(id(pilot), 0) + xp
                self.xp_log.award(pilot, xp, "damaged", victim, target)
        return earned

    def _commit_pilot_experience(
        self, ato: AirTaskingOrder, debriefing: Debriefing, earned: dict[int, int]
    ) -> None:
        for package in ato.packages:
            for flight in package.flights:
                squadron = flight.squadron
                for idx, pilot in enumerate(flight.roster.iter_pilots()):
                    if pilot is None:
                        logging.error(
                            f"Cannot award experience to pilot #{idx} of {flight} "
                            "because no pilot is assigned"
                        )
                        continue
                    pilot.record.missions_flown += 1
                    if not pilot.alive:
                        # Losses are committed before this runs. He earned it and did
                        # not live to collect it.
                        self.xp_log.uncollected(
                            pilot, squadron, earned.get(id(pilot), 0)
                        )
                        continue

                    before = squadron.pilot_rank(pilot)
                    had = pilot.record.xp
                    # A pilot who lost the aircraft did not complete the mission. If
                    # the medics reached him, the wound is his consolation -- smaller
                    # than the sortie, so being shot down is never the better outcome.
                    extras = []
                    if id(pilot) not in debriefing.pilot_outcomes.lost_aircraft:
                        extras.append(
                            ("returned", "mission complete", XP_MISSION_COMPLETE)
                        )
                    if pilot.wounded:
                        extras.append(
                            (
                                "wounded",
                                f"out for {turns_phrase(pilot.wounded_turns)}",
                                XP_WOUNDED,
                            )
                        )
                    pilot.record.xp += earned.get(id(pilot), 0) + sum(
                        xp for _, _, xp in extras
                    )
                    after = squadron.pilot_rank(pilot)
                    promotion = None
                    if before is not None and after is not None and after != before:
                        promotion = f"{before.abbreviation} -> {after.abbreviation}"
                        debriefing.pilot_outcomes.promotions.append(
                            PilotPromotion(
                                pilot_name=pilot.name,
                                squadron=str(squadron),
                                from_rank=before.abbreviation,
                                to_rank=after.abbreviation,
                                to_rank_full=after.name,
                                player=pilot.player,
                            )
                        )
                    self.xp_log.collected(
                        pilot, squadron, had, pilot.record.xp, extras, promotion
                    )

    def commit_pilot_experience(self, debriefing: Debriefing) -> None:
        earned, credited = self._experience_from_kills(debriefing)
        for pilot_id, xp in self._experience_from_damage(debriefing, credited).items():
            earned[pilot_id] = earned.get(pilot_id, 0) + xp
        self._commit_pilot_experience(self.game.blue.ato, debriefing, earned)
        self._commit_pilot_experience(self.game.red.ato, debriefing, earned)
        self.xp_log.write()
        self._xp_log = None

    @staticmethod
    def commit_front_line_losses(debriefing: Debriefing) -> None:
        for loss in debriefing.front_line_losses:
            unit_type = loss.unit_type
            control_point = loss.origin
            available = control_point.base.total_units_of_type(unit_type)
            if available <= 0:
                logging.error(
                    f"Found killed {unit_type} from {control_point} but that "
                    "airbase has none available."
                )
                continue

            logging.info(f"{unit_type} destroyed from {control_point}")
            control_point.base.armor[unit_type] -= 1

    @staticmethod
    def commit_motorpool_losses(debriefing: Debriefing) -> None:
        for loss in debriefing.motorpool_losses:
            unit_type = loss.unit_type
            control_point = loss.origin
            available = control_point.base.total_units_of_type(unit_type)
            if available <= 0:
                logging.error(
                    f"Found killed motorpool {unit_type} from {control_point} but "
                    "that base has none available."
                )
                continue
            logging.info(f"Motorpool {unit_type} destroyed from {control_point}")
            control_point.base.armor[unit_type] -= 1

    @staticmethod
    def commit_convoy_losses(debriefing: Debriefing) -> None:
        for loss in debriefing.convoy_losses:
            unit_type = loss.unit_type
            convoy = loss.convoy
            available = loss.convoy.units.get(unit_type, 0)
            convoy_name = f"convoy from {convoy.origin} to {convoy.destination}"
            if available <= 0:
                logging.error(
                    f"Found killed {unit_type} in {convoy_name} but that convoy has "
                    "none available."
                )
                continue

            logging.info(f"{unit_type} destroyed in {convoy_name}")
            convoy.kill_unit(unit_type)

    @staticmethod
    def commit_cargo_ship_losses(debriefing: Debriefing) -> None:
        for ship in debriefing.cargo_ship_losses:
            logging.info(
                f"All units destroyed in cargo ship from {ship.origin} to "
                f"{ship.destination}."
            )
            ship.kill_all()

    @staticmethod
    def commit_airlift_losses(debriefing: Debriefing) -> None:
        for loss in debriefing.airlift_losses:
            transfer = loss.transfer
            airlift_name = f"airlift from {transfer.origin} to {transfer.destination}"
            for unit_type in loss.cargo:
                try:
                    transfer.kill_unit(unit_type)
                    logging.info(f"{unit_type} destroyed in {airlift_name}")
                except KeyError:
                    logging.exception(
                        f"Found killed {unit_type} in {airlift_name} but that airlift "
                        "has none available."
                    )

    @staticmethod
    def commit_ground_losses(debriefing: Debriefing, events: GameUpdateEvents) -> None:
        for ground_object_loss in debriefing.ground_object_losses:
            ground_object_loss.theater_unit.kill(events)
        for scenery_object_loss in debriefing.scenery_object_losses:
            scenery_object_loss.ground_unit.kill(events)

    @staticmethod
    def commit_damaged_runways(debriefing: Debriefing) -> None:
        for damaged_runway in debriefing.damaged_runways:
            damaged_runway.damage_runway()

    def commit_cruise_missiles(self, debriefing: Debriefing) -> None:
        # Debit each launching ship group's campaign magazine by what the cruisemissiles
        # plugin reported fired. The only debit site in the feature, which is what makes
        # regenerating a mission free of charge. No-op when nothing was reported.
        from game.cruise_raids import reconcile_cruise_missiles

        reconcile_cruise_missiles(self.game, debriefing)

    def commit_naval_magazines(self, debriefing: Debriefing) -> None:
        # Debit each naval group's persisted anti-ship magazine by what the
        # navalmagazines plugin reported fired. The only debit site, so re-generating
        # a mission never double-counts, and the weapon set is disjoint from the
        # cruise-missile magazine's so a shot is never charged twice. No-op when
        # nothing was reported.
        from game.naval_magazines import reconcile_naval_magazines

        reconcile_naval_magazines(self.game, debriefing)

    def commit_captures(self, debriefing: Debriefing, events: GameUpdateEvents) -> None:
        for captured in debriefing.base_captures:
            try:
                if captured.captured_by_player.is_blue:
                    self.game.message(
                        f"{captured.control_point} captured!",
                        f"We took control of {captured.control_point}.",
                    )
                else:
                    self.game.message(
                        f"{captured.control_point} lost!",
                        f"The enemy took control of {captured.control_point}.",
                    )

                captured.control_point.capture(
                    self.game, events, captured.captured_by_player
                )
            except Exception:
                logging.exception(f"Could not process base capture {captured}")

        for captured in debriefing.base_captures:
            logging.info(f"Will run redeploy for {captured.control_point}")
            self.redeploy_units(captured.control_point)

    def record_carcasses(self, debriefing: Debriefing) -> None:
        for destroyed_unit in debriefing.state_data.destroyed_statics:
            self.game.add_destroyed_units(destroyed_unit)

    def commit_front_line_battle_impact(
        self, debriefing: Debriefing, events: GameUpdateEvents
    ) -> None:
        for cp in self.game.theater.player_points():
            enemy_cps = [e for e in cp.connected_points if e.captured.is_red]
            for enemy_cp in enemy_cps:
                front_line = cp.front_line_with(enemy_cp)
                front_line.update_position()
                events.update_front_line(front_line)

                print(
                    "Compute frontline progression for : "
                    + cp.name
                    + " to "
                    + enemy_cp.name
                )

                delta = 0.0
                player_won = True
                status_msg: str = ""
                ally_casualties = debriefing.casualty_count(cp)
                enemy_casualties = debriefing.casualty_count(enemy_cp)
                ally_units_alive = cp.base.total_armor
                enemy_units_alive = enemy_cp.base.total_armor

                print(f"Remaining allied units: {ally_units_alive}")
                print(f"Remaining enemy units: {enemy_units_alive}")
                print(f"Allied casualties {ally_casualties}")
                print(f"Enemy casualties {enemy_casualties}")

                ratio = (1.0 + enemy_casualties) / (1.0 + ally_casualties)

                player_aggresive = cp.stances[enemy_cp.id] in [
                    CombatStance.AGGRESSIVE,
                    CombatStance.ELIMINATION,
                    CombatStance.BREAKTHROUGH,
                ]

                if ally_units_alive == 0:
                    player_won = False
                    delta = STRONG_DEFEAT_INFLUENCE
                    status_msg = f"No allied units alive at {cp.name}-{enemy_cp.name} frontline.  Allied ground forces suffer a strong defeat."
                elif enemy_units_alive == 0:
                    player_won = True
                    delta = STRONG_DEFEAT_INFLUENCE
                    status_msg = f"No enemy units alive at {cp.name}-{enemy_cp.name} frontline.  Allied ground forces win a strong victory."
                elif cp.stances[enemy_cp.id] == CombatStance.RETREAT:
                    player_won = False
                    delta = STRONG_DEFEAT_INFLUENCE
                    status_msg = f"Allied forces are retreating along the {cp.name}-{enemy_cp.name} frontline, suffering a strong defeat."
                else:
                    if enemy_casualties > ally_casualties:
                        player_won = True
                        if cp.stances[enemy_cp.id] == CombatStance.BREAKTHROUGH:
                            delta = STRONG_DEFEAT_INFLUENCE
                            status_msg = f"Allied forces break through the {cp.name}-{enemy_cp.name} frontline, winning a strong victory"
                        else:
                            if ratio > 3:
                                delta = STRONG_DEFEAT_INFLUENCE
                                status_msg = f"Enemy casualties massively outnumber allied casualties along the {cp.name}-{enemy_cp.name} frontline.  Allied forces win a strong victory."
                            elif ratio < 1.5:
                                delta = MINOR_DEFEAT_INFLUENCE
                                status_msg = f"Enemy casualties minorly outnumber allied casualties along the {cp.name}-{enemy_cp.name} frontline.  Allied forces win a minor victory."
                            else:
                                delta = DEFEAT_INFLUENCE
                                status_msg = f"Enemy casualties outnumber allied casualties along the {cp.name}-{enemy_cp.name} frontline.  Allied forces claim a victory."
                    elif ally_casualties > enemy_casualties:
                        if (
                            ally_units_alive > 2 * enemy_units_alive
                            and player_aggresive
                        ):
                            # Even with casualties if the enemy is overwhelmed, they are going to lose ground
                            player_won = True
                            delta = MINOR_DEFEAT_INFLUENCE
                            status_msg = f"Despite suffering losses, allied forces still outnumber enemy forces along the {cp.name}-{enemy_cp.name} frontline.  Due to allied force's aggressive posture, allied forces claim a minor victory."
                        elif (
                            ally_units_alive > 3 * enemy_units_alive
                            and player_aggresive
                        ):
                            player_won = True
                            delta = STRONG_DEFEAT_INFLUENCE
                            status_msg = f"Despite suffering losses, allied forces still heavily outnumber enemy forces along the {cp.name}-{enemy_cp.name} frontline.  Due to allied force's aggressive posture, allied forces claim a major victory."
                        else:
                            # But if the enemy is not outnumbered, we lose
                            player_won = False
                            if cp.stances[enemy_cp.id] == CombatStance.BREAKTHROUGH:
                                delta = STRONG_DEFEAT_INFLUENCE
                                status_msg = f"Allied casualties outnumber enemy casualties along the {cp.name}-{enemy_cp.name} frontline.  Allied forces have overextended themselves, suffering a major defeat."
                            else:
                                delta = DEFEAT_INFLUENCE
                                status_msg = f"Allied casualties outnumber enemy casualties along the {cp.name}-{enemy_cp.name} frontline.  Allied forces suffer a defeat."

                    # No progress with defensive strategies
                    if player_won and cp.stances[enemy_cp.id] in [
                        CombatStance.DEFENSIVE,
                        CombatStance.AMBUSH,
                    ]:
                        print(
                            f"Allied forces have adopted a defensive stance along the {cp.name}-{enemy_cp.name} "
                            f"frontline, making only limited progress."
                        )
                        delta = MINOR_DEFEAT_INFLUENCE

                # Handle the case where there are no casualties at all on either side but both sides still have units
                if delta == 0.0:
                    print(status_msg)
                    self.game.message(
                        "Frontline Report",
                        f"Our ground forces from {cp.name} reached a stalemate with enemy forces from {enemy_cp.name}.",
                    )
                else:
                    if player_won:
                        print(status_msg)
                        cp.base.affect_strength(delta)
                        enemy_cp.base.affect_strength(-delta)
                        self.game.message(
                            "Frontline Report",
                            f"Our ground forces from {cp.name} are making progress toward {enemy_cp.name}. {status_msg}",
                        )
                    else:
                        print(status_msg)
                        enemy_cp.base.affect_strength(delta)
                        cp.base.affect_strength(-delta)
                        self.game.message(
                            "Frontline Report",
                            f"Our ground forces from {cp.name} are losing ground against the enemy forces from "
                            f"{enemy_cp.name}. {status_msg}",
                        )

    def redeploy_units(self, cp: ControlPoint) -> None:
        """ "
        Auto redeploy units to newly captured base
        """
        enemy_connected_cps = [
            ocp for ocp in cp.connected_points if cp.captured != ocp.captured
        ]

        # If the newly captured cp does not have enemy connected cp,
        # then it is not necessary to redeploy frontline units there.
        if len(enemy_connected_cps) == 0:
            return

        ally_connected_cps = [
            ocp
            for ocp in cp.transitive_connected_friendly_destinations()
            if cp.captured == ocp.captured and ocp.base.total_armor
        ]

        settings = cp.coalition.game.settings
        factor = (
            settings.frontline_reserves_factor
            if cp.captured.is_blue
            else settings.frontline_reserves_factor_red
        )

        # From each ally cp, send reinforcements
        for ally_cp in sorted(
            ally_connected_cps,
            key=lambda x: len(
                [cp for cp in x.connected_points if x.captured != cp.captured]
            ),
        ):
            self.redeploy_between(cp, ally_cp)
            if cp.base.total_armor > factor * cp.deployable_front_line_units:
                break

    def redeploy_between(self, destination: ControlPoint, source: ControlPoint) -> None:
        total_units_redeployed = 0
        moved_units = {}

        settings = source.coalition.game.settings
        reserves = max(
            1,
            (
                settings.reserves_procurement_target
                if source.captured.is_blue
                else settings.reserves_procurement_target_red
            ),
        )
        total_units = source.base.total_armor
        reserves_factor = (reserves - 1) / total_units  # slight underestimation

        source_frontline_count = len(
            [cp for cp in source.connected_points if not source.is_friendly_to(cp)]
        )

        move_factor = max(0.0, 1 / (source_frontline_count + 1) - reserves_factor)

        for frontline_unit, count in source.base.armor.items():
            moved_count = int(count * move_factor)
            moved_units[frontline_unit] = moved_count
            total_units_redeployed += moved_count

        destination.base.commission_units(moved_units)
        source.base.commit_losses(moved_units)

        # Also transfer pending deliveries.
        for unit_type, count in list(source.ground_unit_orders.units.items()):
            move_count = int(count * move_factor)
            source.ground_unit_orders.sell({unit_type: move_count})
            destination.ground_unit_orders.order({unit_type: move_count})
            total_units_redeployed += move_count

        if total_units_redeployed > 0:
            self.game.message(
                "Units redeployed",
                f"{total_units_redeployed}  units have been redeployed from "
                f"{source.name} to {destination.name}",
            )
