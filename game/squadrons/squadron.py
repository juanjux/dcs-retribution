from __future__ import annotations

import logging
import random
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Union
from typing import Optional, Sequence, TYPE_CHECKING
from uuid import uuid4, UUID

from dcs.country import Country
from dcs.unit import Skill
from faker import Faker

from game.ato import Flight, FlightType, Package
from game.settings import AutoAtoBehavior, Settings
from game.theater import ParkingType
from game.theater.player import Player
from .pilot import Pilot, PilotStatus
from game.dcs.skills import CADET_SKILL, SKILL_LADDER, skill_for_experience
from game.squadrons import morale as morale_rules
from game.squadrons.morale import TURNS_BEFORE_LEAVE_IS_MISSED, shifted_skill

from .pilotnames import faker_for_country
from .pilotranks import Rank, rank_for_skill, ranks_for
from ..db.database import Database
from ..radio.radios import RadioFrequency
from ..utils import meters, nautical_miles

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.dcs.aircrafttype import AircraftType
    from game.theater import ControlPoint, MissionTarget
    from .operatingbases import OperatingBases
    from .squadrondef import SquadronDef


@dataclass
class Squadron:
    id: UUID = field(init=False, default_factory=uuid4)

    name: str
    nickname: Optional[str]
    country: Country
    role: str
    aircraft: AircraftType
    max_size: int
    livery: Optional[str]
    livery_set: list[str]  # will override livery if not empty
    primary_task: FlightType
    auto_assignable_mission_types: set[FlightType]
    radio_presets: dict[Union[str, int], list[RadioFrequency]]
    operating_bases: OperatingBases
    female_pilot_percentage: int

    #: The pool of pilots that have not yet been assigned to the squadron. This only
    #: happens when a preset squadron defines more preset pilots than the squadron limit
    #: allows. This pool will be consumed before random pilots are generated.
    pilot_pool: list[Pilot]

    current_roster: list[Pilot] = field(default_factory=list, init=False, hash=False)
    available_pilots: list[Pilot] = field(
        default_factory=list, init=False, hash=False, compare=False
    )

    coalition: Coalition = field(hash=False, compare=False)
    flight_db: Database[Flight] = field(hash=False, compare=False)
    settings: Settings = field(hash=False, compare=False)

    location: ControlPoint
    destination: Optional[ControlPoint] = field(
        init=False, hash=False, compare=False, default=None
    )

    owned_aircraft: int = field(init=False, hash=False, compare=False, default=0)
    untasked_aircraft: int = field(init=False, hash=False, compare=False, default=0)
    pending_deliveries: int = field(init=False, hash=False, compare=False, default=0)

    #: Aircraft the squadron started the campaign with (set at turn 0).
    initial_aircraft: int = field(init=False, hash=False, compare=False, default=0)
    #: Cumulative aircraft lost in combat over the whole campaign.
    destroyed_aircraft: int = field(init=False, hash=False, compare=False, default=0)
    #: Cumulative aircraft purchased and delivered over the whole campaign.
    purchased_aircraft: int = field(init=False, hash=False, compare=False, default=0)

    use_livery_set: bool = False  # if livery-set should be used when present

    def __setstate__(self, state: dict[str, Any]) -> None:
        if "id" not in state:
            state["id"] = uuid4()
        if "use_livery_set" not in state:
            state["use_livery_set"] = len(state.get("livery_set", [])) > 0
        if "initial_aircraft" not in state:
            # Best-effort for campaigns started before this counter existed:
            # approximate the starting force with the current owned count.
            state["initial_aircraft"] = state.get("owned_aircraft", 0)
        if "destroyed_aircraft" not in state:
            state["destroyed_aircraft"] = 0
        if "purchased_aircraft" not in state:
            state["purchased_aircraft"] = 0
        self.__dict__.update(state)

    def __str__(self) -> str:
        if self.nickname is None:
            return self.name
        return f'{self.name} "{self.nickname}"'

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Squadron):
            return False
        return self.id == other.id

    def __post_init__(self) -> None:
        self._livery_pool: list[str] = []

    @property
    def player(self) -> Player:
        return self.coalition.player

    @property
    def base_skill(self) -> Skill:
        """The lowest rung this coalition's pilots may fly at.

        Live Pilots puts every wing on the bottom rung, because a rank that starts at
        Veteran has nowhere to climb from. It does that here rather than by writing
        Cadet into the difficulty settings: those belong to the player, they are what
        the wing returns to when the feature is switched off, and overwriting them
        leaked a Cadet air force into the next campaign started from them.
        """
        if self.settings.live_pilots_enabled:
            return CADET_SKILL
        return self.difficulty_skill

    @property
    def difficulty_skill(self) -> Skill:
        """The skill the player set for this coalition on the difficulty page."""
        if self.player.is_blue:
            return Skill(self.settings.player_skill)
        return Skill(self.settings.enemy_skill)

    def pilot_skill(self, pilot: Pilot) -> Skill:
        """The effective DCS skill the pilot flies at.

        Earned, not counted: a pilot flies at the highest rung his experience has paid
        for. The coalition's setting is the floor rather than the starting point, so
        raising the difficulty lifts the whole wing at once and never demotes a veteran.
        Levelling only applies when the ``ai_pilot_levelling`` setting is enabled.
        """
        if not self.settings.ai_pilot_levelling:
            return self.base_skill
        return skill_for_experience(pilot.record.xp, self.base_skill)

    def rank_order(self, pilot: Pilot) -> tuple[int, int]:
        """Sort key placing the senior pilot first, the most experienced first within
        a rank.

        Constant while Live Pilots is off: no rank is on display then, so ordering a
        roster by a number nobody can see would look arbitrary.
        """
        if self.pilot_rank(pilot) is None:
            return 0, 0
        try:
            rung = SKILL_LADDER.index(self.pilot_skill(pilot))
        except ValueError:
            rung = 0
        return -rung, -pilot.record.xp

    @property
    def morale_in_play(self) -> bool:
        """Morale rides on Live Pilots and can be switched off on its own.

        Switched off it does nothing at all: no drift, no leave running down, and
        nobody grounded for a figure the player cannot see.
        """
        return self.settings.live_pilots_enabled and getattr(
            self.settings, "morale_enabled", True
        )

    def mission_skill(self, pilot: Pilot) -> Skill:
        """The rung he will actually fly at, once his state of mind is counted.

        Kept apart from :meth:`pilot_skill` on purpose. Rank is derived from that one,
        so shifting it for morale would demote a Major to Captain on a bad week and
        promote him back on a good one. Only the mission file reads this.
        """
        if not self.morale_in_play:
            return self.pilot_skill(pilot)
        return shifted_skill(self.pilot_skill(pilot), pilot.morale, self.settings)

    def pilot_rank(self, pilot: Pilot) -> Optional[Rank]:
        """The rank the pilot holds, or None while Live Pilots is switched off.

        A rank is a renaming of the DCS skill level rather than a second ladder:
        competence is the only thing the engine can be told about, so promotion
        and skill have to be the same step.
        """
        if not self.settings.live_pilots_enabled:
            return None
        ladder = ranks_for(
            self.settings.live_pilots_rank_names,
            self.country,
            (
                (
                    self.settings.live_pilots_rank_cadet_short,
                    self.settings.live_pilots_rank_cadet_full,
                ),
                (
                    self.settings.live_pilots_rank_average_short,
                    self.settings.live_pilots_rank_average_full,
                ),
                (
                    self.settings.live_pilots_rank_good_short,
                    self.settings.live_pilots_rank_good_full,
                ),
                (
                    self.settings.live_pilots_rank_high_short,
                    self.settings.live_pilots_rank_high_full,
                ),
                (
                    self.settings.live_pilots_rank_excellent_short,
                    self.settings.live_pilots_rank_excellent_full,
                ),
            ),
        )
        return rank_for_skill(self.pilot_skill(pilot), ladder)

    def assign_to_base(self, base: ControlPoint) -> None:
        self.location = base
        logging.debug(f"Assigned {self} to {base}")

    @property
    def pilot_limits_enabled(self) -> bool:
        return self.settings.enable_squadron_pilot_limits

    def random_round_robin_livery_from_set(self) -> str:
        livery = random.choice(self.livery_set)
        self._livery_pool.append(livery)
        self.livery_set.remove(livery)
        if not self.livery_set:
            self.livery_set = self._livery_pool
            self._livery_pool = []
        return livery

    def set_auto_assignable_mission_types(
        self, mission_types: Iterable[FlightType]
    ) -> None:
        self.auto_assignable_mission_types = {
            t for t in mission_types if self.capable_of(t)
        }

    def claim_new_pilot_if_allowed(self) -> Optional[Pilot]:
        if self.pilot_limits_enabled:
            return None
        self._recruit_pilots(1)
        return self.available_pilots.pop()

    def claim_available_pilot(self) -> Optional[Pilot]:
        if not self.available_pilots:
            return self.claim_new_pilot_if_allowed()

        # For opfor, so player/AI option is irrelevant.
        if self.player != Player.BLUE:
            return self.available_pilots.pop()

        preference = self.settings.auto_ato_behavior

        # No preference, so the first pilot is fine.
        if preference is AutoAtoBehavior.Default:
            return self.available_pilots.pop()

        prefer_players = preference is AutoAtoBehavior.Prefer
        for pilot in self.available_pilots:
            if pilot.player == prefer_players:
                self.available_pilots.remove(pilot)
                return pilot

        # No pilot was found that matched the user's preference.
        #
        # If they chose to *never* assign players and only players remain in the pool,
        # we cannot fill the slot with the available pilots.
        #
        # If they only *prefer* players and we're out of players, just return an AI
        # pilot.
        if not prefer_players:
            return self.claim_new_pilot_if_allowed()
        return self.available_pilots.pop()

    def claim_pilot(self, pilot: Pilot) -> None:
        if pilot not in self.available_pilots:
            raise ValueError(
                f"Cannot assign {pilot} to {self} because they are not available"
            )
        self.available_pilots.remove(pilot)

    def return_pilot(self, pilot: Pilot) -> None:
        self.available_pilots.append(pilot)

    def return_pilots(self, pilots: Sequence[Pilot]) -> None:
        # Return in reverse so that returning two pilots and then getting two more
        # results in the same ordering. This happens commonly when resetting rosters in
        # the UI, when we clear the roster because the UI is updating, then end up
        # repopulating the same size flight from the same squadron.
        self.available_pilots.extend(reversed(pilots))

    def _recruit_pilots(self, count: int) -> None:
        new_pilots = self.pilot_pool[:count]
        self.pilot_pool = self.pilot_pool[count:]
        count -= len(new_pilots)
        # Resolve the squadron's faker once per batch, not once per pilot: the
        # country/locale is fixed for a squadron's lifetime, so hundreds of
        # identical ``faker_for_country`` lookups per campaign collapse to one.
        faker = self.faker
        for _ in range(count):
            if random.randint(1, 100) > self.female_pilot_percentage:
                new_pilots.append(Pilot(faker.name_male()))
            else:
                new_pilots.append(Pilot(faker.name_female()))
        self.current_roster.extend(new_pilots)
        self.available_pilots.extend(new_pilots)

    def populate_for_turn_0(self, squadrons_start_full: bool) -> None:
        if any(p.status is not PilotStatus.Active for p in self.pilot_pool):
            raise ValueError("Squadrons can only be created with active pilots.")
        self._recruit_pilots(self.settings.squadron_pilot_limit)
        if squadrons_start_full:
            parking_type = ParkingType().from_squadron(self)
            self.owned_aircraft = min(
                self.max_size, self.location.unclaimed_parking(parking_type)
            )
        self.initial_aircraft = self.owned_aircraft

    def end_turn(self) -> None:
        if self.destination is not None:
            self.relocate_to(self.destination)
        self.tend_the_wounded()
        self.tend_morale(self.coalition.game.turn)
        self.replenish_lost_pilots()
        self.deliver_orders()

    def tend_morale(self, turn: int) -> None:
        """A turn of ordinary life: leave served, drift, and the cost of no rest.

        Everything that happens *to* a pilot in a mission is applied by the results
        processor. This is only what the passage of time does.
        """
        if not self.morale_in_play:
            return
        for pilot in list(self.current_roster):
            if not pilot.alive:
                continue

            # What he had at this point one turn ago, so the next turn can say whether
            # he is sliding. Taken before anything moves him.
            was = pilot.morale
            pilot.morale_last_turn = was

            if pilot.on_leave:
                pilot.move_morale(
                    morale_rules.ON_LEAVE, self.pilot_skill(pilot), self.settings, turn
                )
                pilot.serve_a_turn_of_leave(turn)
                continue

            # Judged on the state he arrived in. The drift below lifts a man who is
            # merely low, so asking afterwards would read the wrong number.
            was_at_rock_bottom = was <= morale_rules.REFUSES_TO_FLY_AT

            pilot.turns_since_leave += 1
            if pilot.turns_since_leave > TURNS_BEFORE_LEAVE_IS_MISSED:
                # It gets worse the longer it goes on: one event per turn beyond the
                # fifth, so the eighth turn costs three times the sixth.
                overdue = pilot.turns_since_leave - TURNS_BEFORE_LEAVE_IS_MISSED
                for _ in range(overdue):
                    pilot.move_morale(
                        morale_rules.NO_LEAVE,
                        self.pilot_skill(pilot),
                        self.settings,
                        turn,
                    )
            before_drift = pilot.morale
            pilot.morale = morale_rules.clamp(
                pilot.morale + morale_rules.drift(pilot.morale)
            )
            pilot.note_morale_change(before_drift, "time passing", turn)

            if was_at_rock_bottom:
                pilot.turns_at_zero += 1
                # A roll, not a countdown: every turn a man is left at the bottom is a
                # turn he might not come back from, and rank is what holds him there.
                if random.random() < morale_rules.desertion_chance(
                    self.pilot_skill(pilot)
                ):
                    logging.info(
                        f"{pilot.name} has deserted {self} after "
                        f"{pilot.turns_at_zero} turns at rock bottom"
                    )
                    pilot.desert()
                    continue
            else:
                pilot.turns_at_zero = 0

            if not pilot.wants_leave and random.random() < (
                morale_rules.leave_request_chance(
                    pilot.morale,
                    getattr(self.settings, "morale_leave_request_chance", 8),
                )
            ):
                pilot.wants_leave = True
                pilot.leave_turns_requested = morale_rules.requested_leave_turns(
                    pilot.morale
                )

    def cancel_leave(self, pilot: Pilot) -> None:
        """Call a man back before his leave is up, and pay for it.

        The cost hangs on this, not on :meth:`Pilot.return_from_leave` -- a pilot whose
        leave simply ran out has had his rest and owes nothing.
        """
        if not pilot.on_leave:
            raise RuntimeError("Only pilots on leave may have it cancelled")
        # Goes through the ordinary return, which refuses when the squadron is full.
        self.return_from_leave(pilot)
        if self.morale_in_play:
            pilot.move_morale(
                morale_rules.LEAVE_CANCELLED,
                self.pilot_skill(pilot),
                self.settings,
                self.coalition.game.turn,
            )

    def discharge(self, pilot: Pilot) -> None:
        """Throw a pilot out. He leaves the roster and joins the roll below it."""
        pilot.discharge()
        logging.info(f"{pilot.name} was discharged from {self}")

    def tend_the_wounded(self) -> None:
        """One turn of every wound served; the last one puts the pilot back to work."""
        turn = self.coalition.game.turn
        for pilot in self.wounded_pilots:
            pilot.serve_a_turn_wounded(turn)

    def replenish_lost_pilots(self) -> None:
        if self.pilot_limits_enabled and self.replenish_count > 0:
            self._recruit_pilots(self.replenish_count)

    def return_all_pilots_and_aircraft(self) -> None:
        # A man at rock bottom is not offered, the same way a wounded one is not. He is
        # still on the books and still counts against the squadron's establishment.
        if self.morale_in_play:
            self.available_pilots = [
                p for p in self.active_pilots if not p.refuses_to_fly
            ]
        else:
            self.available_pilots = list(self.active_pilots)
        # Aircraft already sold this turn (negative pending) must not return to the
        # taskable pool; otherwise a turn re-initialisation would let the same units
        # be sold (and flown) again, refunding their price every time.
        self.untasked_aircraft = self.owned_aircraft + min(0, self.pending_deliveries)

    @staticmethod
    def send_on_leave(pilot: Pilot, turns: int = 0, turn: int = -1) -> None:
        """Open-ended from the Air Wing button; for a fixed spell from a granted request."""
        pilot.send_on_leave(turns, turn)

    def return_from_leave(self, pilot: Pilot) -> None:
        if not self.has_unfilled_pilot_slots:
            raise RuntimeError(
                f"Cannot return {pilot} from leave because {self} is full"
            )
        pilot.return_from_leave()

    @property
    def faker(self) -> Faker:
        # Name the squadron's pilots in their own nation's convention (the
        # squadron flies under its own DCS country, #627), falling back to a
        # faker built from the faction's locale list for unmapped /
        # multinational countries. See game/squadrons/pilotnames.py.
        return faker_for_country(self.country, self.coalition.faction.locales)

    def _pilots_with_status(self, status: PilotStatus) -> list[Pilot]:
        return [p for p in self.current_roster if p.status == status]

    def _pilots_without_status(self, status: PilotStatus) -> list[Pilot]:
        return [p for p in self.current_roster if p.status != status]

    @property
    def pilot_limit(self) -> int:
        return self.settings.squadron_pilot_limit

    @property
    def expected_pilots_next_turn(self) -> int:
        return len(self.active_pilots) + self.replenish_count

    @property
    def replenish_count(self) -> int:
        return min(
            self.settings.squadron_replenishment_rate,
            self._number_of_unfilled_pilot_slots,
        )

    @property
    def active_pilots(self) -> list[Pilot]:
        return self._pilots_with_status(PilotStatus.Active)

    @property
    def pilots_on_leave(self) -> list[Pilot]:
        return self._pilots_with_status(PilotStatus.OnLeave)

    @property
    def wounded_pilots(self) -> list[Pilot]:
        return self._pilots_with_status(PilotStatus.Wounded)

    @property
    def deserted_pilots(self) -> list[Pilot]:
        return self._pilots_with_status(PilotStatus.Deserted)

    @property
    def number_of_pilots_including_inactive(self) -> int:
        return len(self.current_roster)

    @property
    def living_pilots(self) -> list[Pilot]:
        return [p for p in self.current_roster if p.alive]

    @property
    def dead_pilots(self) -> list[Pilot]:
        """The ones who are not coming back, however they went."""
        return [p for p in self.current_roster if not p.alive]

    @property
    def _number_of_unfilled_pilot_slots(self) -> int:
        # A wounded pilot is still on the books, so his slot is not free to recruit
        # into. Otherwise the squadron backfills every casualty and finds itself over
        # its own limit the turn the wounded come back.
        return self.pilot_limit - len(self.active_pilots) - len(self.wounded_pilots)

    @property
    def number_of_available_pilots(self) -> int:
        return len(self.available_pilots)

    def can_provide_pilots(self, count: int) -> bool:
        return not self.pilot_limits_enabled or self.number_of_available_pilots >= count

    @property
    def has_available_pilots(self) -> bool:
        return not self.pilot_limits_enabled or bool(self.available_pilots)

    @property
    def has_unfilled_pilot_slots(self) -> bool:
        return not self.pilot_limits_enabled or self._number_of_unfilled_pilot_slots > 0

    def capable_of(self, task: FlightType) -> bool:
        """Returns True if the squadron is capable of performing the given task.

        A squadron may be capable of performing a task even if it will not be
        automatically assigned to it.
        """
        return self.aircraft.capable_of(task)

    def can_auto_assign(self, task: FlightType) -> bool:
        return task in self.auto_assignable_mission_types

    def can_auto_assign_mission(
        self,
        location: MissionTarget,
        task: FlightType,
        size: int,
        heli: bool,
        this_turn: bool,
        ignore_range: bool = False,
    ) -> bool:
        if (
            self.location.cptype.name in ["FOB", "FARP"]
            and not self.aircraft.helicopter
        ):
            # AI harriers can't handle FOBs/FARPs
            # AI has a hard time taking off and will not land back at FOB/FARP
            # thus, disable auto-planning
            return False
        if not self.can_auto_assign(task):
            return False
        if this_turn and not self.can_fulfill_flight(size):
            return False

        if task in [FlightType.ESCORT, FlightType.SEAD_ESCORT]:
            if heli and not self.aircraft.helicopter and not self.aircraft.lha_capable:
                return False
            if not heli and self.aircraft.helicopter:
                return False

        if heli and task == FlightType.REFUELING:
            return False

        if ignore_range:
            return True

        distance_to_target = meters(location.distance_to(self.location))
        max_plane_dist = nautical_miles(
            self.coalition.game.settings.max_mission_range_planes
        )
        max_heli_dist = nautical_miles(
            self.coalition.game.settings.max_mission_range_helicopters
        )
        if self.aircraft.helicopter:
            return distance_to_target <= max(
                self.aircraft.max_mission_range, max_heli_dist
            )
        return distance_to_target <= max(
            self.aircraft.max_mission_range, max_plane_dist
        )

    def operates_from(self, control_point: ControlPoint) -> bool:
        if not control_point.can_operate(self.aircraft):
            return False
        if control_point.is_carrier:
            return self.operating_bases.carrier
        elif control_point.is_lha:
            return self.operating_bases.lha
        else:
            return self.operating_bases.shore

    def pilot_at_index(self, index: int) -> Pilot:
        return self.current_roster[index]

    def claim_inventory(self, count: int) -> None:
        if self.untasked_aircraft < count:
            raise ValueError(
                f"Cannot remove {count} from {self.name}. Only have "
                f"{self.untasked_aircraft}."
            )
        self.untasked_aircraft -= count

    def can_fulfill_flight(self, count: int) -> bool:
        return self.can_provide_pilots(count) and self.untasked_aircraft >= count

    def refund_orders(self, count: Optional[int] = None) -> None:
        if count is None:
            count = self.pending_deliveries
        self.coalition.adjust_budget(self.aircraft.price * count)
        self.pending_deliveries -= count

    def deliver_orders(self) -> None:
        self.cancel_overflow_orders()
        self.purchased_aircraft += self.pending_deliveries
        self.owned_aircraft += self.pending_deliveries
        self.pending_deliveries = 0

    def relocate_to(self, destination: ControlPoint) -> None:
        if not destination.is_friendly(self.coalition.player):
            logging.warning(
                f"Cannot relocate {self} to {destination.name} - destination is no longer friendly. "
                f"Cancelling relocation order."
            )
            self.destination = None
            return
        self.location = destination
        if self.location == self.destination:
            self.destination = None

    def cancel_overflow_orders(self) -> None:
        from game.theater import ParkingType

        if self.pending_deliveries <= 0:
            return
        parking_type = ParkingType().from_aircraft(
            self.aircraft, self.coalition.game.settings.ground_start_ai_planes
        )
        overflow = -self.location.unclaimed_parking(parking_type)
        if overflow > 0:
            sell_count = min(overflow, self.pending_deliveries)
            logging.debug(
                f"{self.location} is overfull by {overflow} aircraft. Cancelling "
                f"orders for {sell_count} aircraft to make room."
            )
            self.refund_orders(sell_count)

    @property
    def max_fulfillable_aircraft(self) -> int:
        return max(self.number_of_available_pilots, self.untasked_aircraft)

    @property
    def untasked_crewed_aircraft(self) -> int:
        """Untasked aircraft that also have a free pilot to fly them — the real number
        launchable this turn. ``untasked_aircraft`` alone can exceed the pilots on hand;
        this caps it. Equals ``untasked_aircraft`` when pilot limits are disabled."""
        if not self.pilot_limits_enabled:
            return self.untasked_aircraft
        return min(self.untasked_aircraft, self.number_of_available_pilots)

    @property
    def expected_size_next_turn(self) -> int:
        return self.owned_aircraft + self.pending_deliveries

    def has_aircraft_capacity_for(self, n: int) -> bool:
        if not self.settings.enable_squadron_aircraft_limits:
            return True
        remaining = self.max_size - self.owned_aircraft - self.pending_deliveries
        return remaining >= n

    @property
    def arrival(self) -> ControlPoint:
        return self.location if self.destination is None else self.destination

    def plan_relocation(self, destination: ControlPoint, now: datetime) -> None:
        from game.theater import ParkingType

        if destination == self.location:
            logging.warning(
                f"Attempted to plan relocation of {self} to current location "
                f"{destination}. Ignoring."
            )
            return
        if destination == self.destination:
            logging.warning(
                f"Attempted to plan relocation of {self} to current destination "
                f"{destination}. Ignoring."
            )
            return

        parking_type = ParkingType().from_squadron(self)
        if self.expected_size_next_turn > destination.unclaimed_parking(parking_type):
            raise RuntimeError(f"Not enough parking for {self} at {destination}.")
        if not destination.can_operate(self.aircraft):
            raise RuntimeError(f"{self} cannot operate at {destination}.")
        self.destination = destination
        self.replan_ferry_flights(now)

    def cancel_relocation(self) -> None:
        from game.theater import ParkingType

        if self.destination is None:
            logging.warning(
                f"Attempted to cancel relocation of squadron with no transfer order. "
                "Ignoring."
            )
            return

        parking_type = ParkingType().from_squadron(self)
        if self.expected_size_next_turn > self.location.unclaimed_parking(parking_type):
            raise RuntimeError(f"Not enough parking for {self} at {self.location}.")
        self.destination = None
        self.cancel_ferry_flights()

    def replan_ferry_flights(self, now: datetime) -> None:
        self.cancel_ferry_flights()
        self.plan_ferry_flights(now)

    def cancel_ferry_flights(self) -> None:
        for package in self.coalition.ato.packages:
            # Copy the list so our iterator remains consistent throughout the removal.
            for flight in list(package.flights):
                if flight.squadron == self and flight.flight_type is FlightType.FERRY:
                    package.remove_flight(flight)
            if not package.flights:
                self.coalition.ato.remove_package(package)

    def plan_ferry_flights(self, now: datetime) -> None:
        if self.destination is None:
            raise RuntimeError(
                f"Cannot plan ferry flights for {self} because there is no destination."
            )
        remaining = self.untasked_aircraft
        if not remaining:
            return

        package = Package(self.destination, self.flight_db)
        while remaining:
            size = min(remaining, self.aircraft.max_group_size)
            self.plan_ferry_flight(package, size)
            remaining -= size
        package.set_tot_asap(now)
        self.coalition.ato.add_package(package)

    def plan_ferry_flight(self, package: Package, size: int) -> None:
        start_type = self.location.required_aircraft_start_type
        if start_type is None:
            start_type = self.settings.default_start_type

        flight = Flight(
            package,
            self,
            size,
            FlightType.FERRY,
            start_type,
            divert=None,
        )
        package.add_flight(flight)
        flight.recreate_flight_plan()

    @classmethod
    def create_from(
        cls,
        squadron_def: SquadronDef,
        primary_task: FlightType,
        max_size: int,
        base: ControlPoint,
        coalition: Coalition,
        game: Game,
    ) -> Squadron:
        squadron_def.claimed = True
        return Squadron(
            squadron_def.name,
            squadron_def.nickname,
            squadron_def.country,
            squadron_def.role,
            squadron_def.aircraft,
            max_size,
            squadron_def.livery,
            squadron_def.livery_set,
            primary_task,
            squadron_def.auto_assignable_mission_types,
            squadron_def.radio_presets,
            squadron_def.operating_bases,
            squadron_def.female_pilot_percentage,
            squadron_def.pilot_pool,
            coalition,
            game.db.flights,
            game.settings,
            base,
        )
