"""Read DTOs for the OPFOR-AI feature.

Pure functions over a ``Game`` (no ``GameContext``, no Qt) so they are unit-testable
and importable without PySide6. ``service.py`` wires these to the live game.

Token economy: these payloads go to the LLM **every turn**, so they are frugal —
numbers are rounded,
coordinates are bare ``[lat, lng]`` pairs, TOT is ``HH:MM``, and "boring" fields
(zero counts, empty strings) are left ``None`` so the transport drops them with
``exclude_none``. Convention, stated once in ``/howtoplay``: an absent numeric field
means 0. The one-time docs (start/howtoplay) are exempt — only per-turn data is.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dcs.mapping import Point as DcsPoint
from pydantic import BaseModel

from game.income import Income
from game.theater.player import Player

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.squadrons.squadron import Squadron
    from game.theater import ControlPoint


_SIDE_TO_PLAYER = {"red": Player.RED, "blue": Player.BLUE}

# game.check_win_loss() is blue-centric (WIN == the human/blue won). Re-express it
# from RED's point of view, which is who the OPFOR planner is.
_CAMPAIGN_STATE_FROM_RED = {
    "CONTINUE": "ongoing",
    "WIN": "red_losing",  # blue reached a winning condition
    "LOSS": "red_winning",  # blue lost all its points
}


def player_for_side(side: str) -> Player:
    try:
        return _SIDE_TO_PLAYER[side.lower()]
    except KeyError:
        raise ValueError(f"side must be 'red' or 'blue', got {side!r}")


def coalition_for_side(game: Game, side: str) -> Coalition:
    return game.coalition_for(player_for_side(side))


def _r(value: float, ndigits: int = 5) -> float:
    return round(float(value), ndigits)


def _enum_str(value: object) -> str | None:
    if value is None:
        return None
    member_value = getattr(value, "value", None)
    if member_value is not None:
        return str(member_value)
    return getattr(value, "name", None) or str(value)


# --- DTOs (omitted-when-None fields carry their "boring" default implicitly) ---


class SituationView(BaseModel):
    turn: int
    date: str
    time_of_day: str
    campaign_state: str | None = None  # set only when not "ongoing"


class EconomyView(BaseModel):
    budget: int
    income_next_turn: int


class ControlPointView(BaseModel):
    id: str
    name: str
    type: str
    owner: str  # red / blue / neutral
    pos: list[float]  # [lat, lng]
    sqns: int | None = None  # based-squadron count (omitted when 0)
    parking_free: int | None = None  # free aircraft slots (room to buy/station here)
    parking_total: int | None = None  # total aircraft slots
    can_recruit_ground: bool | None = None  # has a factory/front — buy ground here
    links: list[str] | None = None  # adjacent control-point ids (land moves / fronts)
    ground: dict[str, int] | None = None  # armor on hand here (unit name -> count)
    motorpool: int | None = (
        None  # vehicles of this base's UNDEPLOYED reserve that spawn in a strikeable
        # motorpool depot — what an enemy BAI strike here can destroy (and what you
        # lose the purchase price of). Omitted when the base has no motorpool or
        # nothing in reserve. Yours: deploy it or defend it. Enemy: a fat number is a
        # cheap attrition target (see also targets[] kind:motorpool)
    )
    can_launch: bool | None = (
        None  # False = this base CANNOT launch aircraft this turn (runway cratered/under
        # repair, or carrier hull sunk); omitted when it can. IMPORTANT: a base being
        # repaired does NOT appear in turn_context.repairs (already paid for) yet still
        # can't sortie until runway_repair_turns_remaining hits 0 — do NOT plan flights
        # from a base with can_launch:false.
    )
    runway_repair_turns_remaining: int | None = (
        None  # turns until a repairing runway is operational again (omitted when the base
        # can launch, or when the runway is damaged-but-unpaid — that shows in repairs)
    )


class SquadronView(BaseModel):
    id: str
    name: str
    aircraft: str
    base: str
    owned: int | None = None  # aircraft on hand (omitted when 0)
    untasked: int | None = None  # available to task (omitted when 0)
    flyable: int | None = (
        None  # aircraft you can actually LAUNCH now = min(untasked, pilots), 0 if grounded —
        # the real number to plan with (untasked can exceed available pilots); omitted when 0
    )
    pending: int | None = None  # arriving next turn (omitted when 0)
    pilots: int
    max_ac: int | None = (
        None  # squadron airframe cap: buy/aircraft refuses once owned+pending reaches
        # it (a cap of 1 marks an irreplaceable airframe, e.g. a lone AWACS); omitted
        # when the campaign disables per-squadron aircraft limits
    )
    grounded: bool | None = (
        None  # can't sortie this turn: base enemy-held OR runway cratered / hull sunk
        # (else omitted). flyable is 0 while grounded.
    )


class FlightView(BaseModel):
    id: str
    task: str | None
    aircraft: str
    count: int
    squadron: str
    start: str | None = None
    dep: str | None = None
    clients: int | None = None  # player-controlled seats (omitted when 0)
    uncrewed: int | None = None  # missing pilots — present only when >0 (an alert)
    loadout: str | None = None  # payload name ("Retribution Anti-ship" / "Custom (AI)")
    weapons: dict[int, str] | None = (
        None  # pylon number -> weapon clsid — what this flight actually carries
    )


class PackageView(BaseModel):
    index: int  # position in the ATO (stable within a turn snapshot)
    target: str
    task: str | None
    tot: str | None  # time over target, HH:MM
    desc: str | None = None
    flights: list[FlightView]


class TargetView(BaseModel):
    id: str
    name: str
    kind: str  # sam / ship / building / motorpool / front
    suggested_task: str  # DEAD / ANTISHIP / STRIKE / BAI / CAS
    pos: list[float]  # [lat, lng]
    threat_nm: int | None = (
        None  # air-defense umbrella radius (nm) — danger to ANY flight transiting it,
        # not only the attacker; ships carry it too (naval SAMs like SM-6 reach far)
    )
    friendly_cp_id: str | None = None  # fronts only: your control point (for stances)
    enemy_cp_id: str | None = None  # fronts only: the enemy control point
    group_id: str | None = (
        None  # ships: their naval-group control-point id (concentrate)
    )
    iads_role: str | None = (
        None  # what this site is to the enemy IADS, when it is part of one: PowerSource /
        # ConnectionNode / CommandCenter / Ewr / Sam / SamAsEwr. Tells a code-named
        # building apart from a generic one — a "PowerSource" is a radar's mains supply,
        # not a warehouse. Omitted for anything outside the IADS. See GET /iads for the
        # links (which node each one feeds).
    )
    composition: dict[str, int] | None = (
        None  # ships: alive-hull count per class, e.g. {"Constellation": 2} — so you can
        # spot Aegis escorts (Constellation/Ticonderoga) and count hulls before an ANTISHIP
        # strike, instead of seeing only the group's aggregate threat
    )
    damage: str | None = None  # 'lightly/heavily damaged' (omitted at full strength)


class ThreatView(BaseModel):
    """An enemy air-defense umbrella ranked by reach — the route-shaping threats to
    avoid or suppress. Same ``id`` as the matching target, so you can DEAD/ANTISHIP it
    directly."""

    id: str  # same id as the target in targets[] — task DEAD (sam) / ANTISHIP (ship) on it
    name: str
    kind: str  # sam / ship (ships project naval-SAM umbrellas — SM-6 etc.)
    threat_nm: int  # umbrella radius (nm): your flights are engaged within it
    pos: list[float]  # [lat, lng]


class IadsNodeView(BaseModel):
    """One site in an IADS, with what it depends on."""

    id: str  # same id as in targets[] — plan DEAD or STRIKE against it directly
    name: str
    role: str  # Sam / SamAsEwr / Ewr / CommandCenter / PowerSource / ConnectionNode
    alive: bool  # false = already destroyed; its dependants are already degraded
    depends_on: list[str] | None = (
        None  # ids of the sites feeding this one (power, comms, command). Kill one of
        # these and this node goes down without touching the node itself — that is the
        # whole point of striking the network instead of the launchers.
    )


class IadsView(BaseModel):
    """The enemy IADS as a graph. Empty when the campaign runs no advanced IADS."""

    advanced: bool  # false = Skynet is not wiring power/comms, so only the sites matter
    nodes: list[IadsNodeView]


class NavalView(BaseModel):
    """One of YOUR movable naval groups — reposition it with move_ship."""

    id: str  # group id — pass to move_ship (ships: a tgo id; carriers: a control-point id)
    name: str
    kind: str  # ship (combatant group) / carrier (CV/LHA control point)
    pos: list[float]  # [lat, lng]
    move_range_nm: int  # max reposition per turn (great-circle, over water)
    destination: list[float] | None = (
        None  # pending move target [lat, lng] (omitted when holding)
    )
    threat_nm: int | None = (
        None  # its own air-defense umbrella reach — position it to cover what matters
    )
    damage: str | None = None  # 'lightly/heavily damaged' (omitted at full strength)
    composition: dict[str, int] | None = (
        None  # alive hull count per class, e.g. {"Type 052C": 1, "Type 054A": 2}; lets
        # you see which hulls are still up (not just the aggregate damage %)
    )
    cruise_missiles_remaining: int | None = (
        None  # land-attack cruise missiles this group has left FOR THE WHOLE CAMPAIGN.
        # Never regenerates, cannot be bought or resupplied, and sinks with the hull —
        # spend it on targets aircraft would pay dearly to reach. Omitted when the group
        # carries none or the campaign has cruise missile strikes switched off.
    )


class RepairView(BaseModel):
    """One of YOUR damaged assets you can pay to repair — dead SAM/EWR units, a building,
    or a cratered runway. The fix is instant or takes a few turns, per campaign settings.
    """

    id: str  # repair target id: a ground-object/building tgo id, or a control-point id (runway)
    name: str
    kind: str  # aa / ewr / oil / factory / ammo / runway / ... (what's damaged; economy
    # buildings use their category, so 'oil'/'factory' flag an income asset worth restoring)
    cost: int  # budget to repair it (sum of its dead units, or the flat runway/building cost)
    dead_units: int | None = (
        None  # dead units it would bring back (omitted for a runway)
    )
    income_per_turn: int | None = (
        None  # economy buildings only: the income this asset restores each turn once
        # repaired — prioritise a dead oil/factory over cosmetic damage (a strangled
        # budget is usually a dead income building you can rebuild here)
    )


class GroundUnitView(BaseModel):
    name: str
    price: int
    kind: str  # front (tanks/IFVs) / artillery


class TurnForcesView(BaseModel):
    """Force totals at a past turn — the attrition trend the planner reacts to.

    Loss fields are present only for turns whose mission was flown + debriefed.
    """

    turn: int
    blue_aircraft: int
    blue_vehicles: int
    red_aircraft: int
    red_vehicles: int
    blue_air_lost: int | None = None
    red_air_lost: int | None = None
    blue_air_crashed: int | None = (
        None  # of blue_air_lost, how many were non-combat (crash/collision, no shooter)
    )
    red_air_crashed: int | None = (
        None  # of red_air_lost, how many were non-combat (crash/collision, no shooter)
    )
    blue_ground_lost: int | None = None
    red_ground_lost: int | None = None
    #: What died, by airframe: {"Mi-24P": 8, "Su-25": 6}. A headline count does not
    #: say whether a side lost its Hinds or its Frogfoots, and the two mean different
    #: things for the next turn.
    red_air_lost_by_type: dict[str, int] | None = None
    blue_air_lost_by_type: dict[str, int] | None = None
    #: What did the killing, by WEAPON alone: {"R-37M": 20}. Judge a loadout from this
    #: rather than from *_air_killers below, which falls back from the shooter to the
    #: weapon and so mixes airframes and missiles in one dict.
    red_air_kills_by_weapon: dict[str, int] | None = None
    blue_air_kills_by_weapon: dict[str, int] | None = None
    #: Which airframe killed which: {"Su-57": {"F-16C_50": 9, "F15EX": 4}} reads "red's
    #: Su-57s were shot down 9 times by F-16Cs and 4 by F-15EXs". One nesting deep, and
    #: aggregated, so it grows with the number of TYPES in the fight, not with kills.
    red_air_kills_by_victim: dict[str, dict[str, int]] | None = None
    blue_air_kills_by_victim: dict[str, dict[str, int]] | None = None
    red_air_killers: dict[str, int] | None = None  # what killed red's aircraft
    blue_air_killers: dict[str, int] | None = None  # what killed blue's aircraft
    blue_air_combat: int | None = (
        None  # of blue_air_lost, how many were SHOT DOWN (= lost - crashed); the
    )
    # weapon breakdown is blue_air_killers, the remainder are non-combat blue_air_crashed
    red_air_combat: int | None = None  # of red_air_lost, how many were shot down
    blue_sites_lost: dict[str, int] | None = (
        None  # blue site/naval UNITS destroyed this turn, per unit-type id — ships by
    )
    # class ({"Type_052C": 1}) + SAM launchers/radars: the concrete result of RED's strikes
    red_sites_lost: dict[str, int] | None = (
        None  # red site/naval units destroyed this turn — the result of BLUE's strikes
    )


class TurnContextView(BaseModel):
    side: str
    situation: SituationView
    economy: EconomyView
    control_points: list[ControlPointView]
    air_wing: list[SquadronView]
    idle_flyable: (
        int  # total aircraft you can LAUNCH right now that are still untasked (sum of
    )
    # each squadron's `flyable`). Standing reminder — if this is >0 when you finish the turn you
    # left force on the ramp: task it (more/bigger/staggered BARCAPs, a probe, extra saturation)
    # or hold it on purpose. DRIVE IT TOWARD 0. (0 shown as confirmation.)
    targets: list[TargetView]  # enemy objects this side can strike (aim by id)
    threats: list[ThreatView]  # blue's strongest air-defense umbrellas, ranked by reach
    naval: list[NavalView]  # YOUR movable ship groups (reposition with move_ship)
    repairs: list[
        RepairView
    ]  # YOUR damaged assets you can pay to repair (with `repair`)
    buyable_ground: list[GroundUnitView]  # ground units this faction can buy


class SettingsView(BaseModel):
    """The campaign settings the OPFOR planner reads (and never changes)."""

    opfor_aggressiveness_pct: int  # risk-tolerance hint the player set for red
    map_coalition_visibility: str  # fog-of-war level (drives the intel filter)
    desired_player_mission_duration_min: int  # TOT window the player flies within
    player_income_multiplier: float
    enemy_income_multiplier: float
    crashes_dont_count: (
        bool  # if True, a non-combat air loss (crash/collision, no credited
    )
    # shooter) does NOT deplete the squadron or kill the pilot — see *_air_crashed in prev_turns
    pilot_replenishment_per_squadron: int | None = (
        None  # new pilots each squadron regains per turn (up to the limit); omitted = no pilot limits (unlimited)
    )
    squadron_pilot_limit: int | None = (
        None  # max active pilots per squadron (omitted = no limit)
    )
    runway_repair_turns: int = (
        4  # turns a cratered runway takes to repair; a base's
        # runway_repair_turns_remaining (in control_points) counts down from this
    )
    cruise_missile_strikes: bool = (
        False  # ships with land-attack cruise missiles can hit shore targets. When
        # False, `cruise_missiles_remaining` never appears in naval[] and no raid flies
    )
    cruise_missile_auto_raids: bool = (
        False  # each turn, both sides automatically commit one cruise missile raid at
        # their best reachable enemy ground object. Spends YOUR magazine without asking
    )


class UnitTypeOption(BaseModel):
    name: str
    price: int


class GroupSlotView(BaseModel):
    group_name: str
    optional: bool
    default_count: int
    max_count: int
    unit_types: list[UnitTypeOption]


class LayoutOption(BaseModel):
    force_group: str
    layout: str
    price: int  # default price (all groups at default unit type + group_size)
    groups: list[GroupSlotView]


class GroundObjectOptionsView(BaseModel):
    tgo_id: str
    name: str
    role: str  # "air_defense" | "ground_force" | "naval" | "defenses"
    refund: int  # tgo.value, refunded when rebuilding
    budget: int
    options: list[LayoutOption]


# --- builders ---


def build_situation(game: Game) -> SituationView:
    state = _CAMPAIGN_STATE_FROM_RED.get(game.check_win_loss().name, "ongoing")
    return SituationView(
        turn=game.turn,
        date=game.current_day.isoformat(),
        time_of_day=game.current_turn_time_of_day.name,
        campaign_state=None if state == "ongoing" else state,
    )


def build_economy(game: Game, side: str) -> EconomyView:
    player = player_for_side(side)
    return EconomyView(
        budget=round(game.coalition_for(player).budget),
        income_next_turn=round(Income(game, player).total),
    )


def _parking(cp) -> tuple[int, int] | None:
    """(used, total) aircraft-parking slots at a base, or None if it has none."""
    from game.theater import ParkingType

    try:
        pt = ParkingType(fixed_wing=True, fixed_wing_stol=True, rotary_wing=True)
        total = cp.total_aircraft_parking(pt)
        if total <= 0:
            return None
        return total - cp.unclaimed_parking(pt), total
    except Exception:
        return None


def _motorpool_exposed(game: Game, cp: ControlPoint) -> int | None:
    """Vehicles of this base's undeployed reserve that render in a strikeable
    motorpool, i.e. what an enemy BAI strike here could actually destroy.

    None (omitted) unless the base has an authored motorpool and something in
    reserve. The spawn cap is per control point — its motorpools share one reserve
    pool (MotorpoolPopulator._populate_cp) — so the exposure is capped once here.
    """
    try:
        from game.ground_forces.ai_ground_planner import reserve_armor_for
        from game.theater.theatergroundobject import MotorpoolGroundObject

        cap = game.settings.motorpool_spawn_cap
        if not game.settings.motorpool_enabled or cap <= 0:
            return None
        if not any(isinstance(tgo, MotorpoolGroundObject) for tgo in cp.ground_objects):
            return None
        return min(sum(reserve_armor_for(cp).values()), cap) or None
    except Exception:
        return None


def build_control_point(game: Game, cp: ControlPoint) -> ControlPointView:
    # Mirror game/server/leaflet.py: build a terrain-aware Point before converting.
    ll = DcsPoint(cp.position.x, cp.position.y, game.theater.terrain).latlng()
    sqns = sum(1 for _ in cp.squadrons)
    park = _parking(cp)
    armor = getattr(getattr(cp, "base", None), "armor", None)
    ground = {ut.display_name: n for ut, n in armor.items() if n} if armor else None
    links = [str(n.id) for n in getattr(cp, "connected_points", [])] or None
    try:
        recruit = bool(cp.has_ground_unit_source(game)) or None
    except Exception:
        recruit = None
    operational = cp.runway_is_operational()
    try:
        repair_turns = cp.runway_status.repair_turns_remaining
    except Exception:
        repair_turns = None  # carriers/LHAs/off-map have no repairable runway
    return ControlPointView(
        motorpool=_motorpool_exposed(game, cp),
        id=str(cp.id),
        name=cp.name,
        type=cp.cptype.name,
        owner=cp.captured.value.lower(),
        pos=[_r(ll.lat), _r(ll.lng)],
        sqns=sqns or None,
        parking_free=(park[1] - park[0]) if park else None,
        parking_total=park[1] if park else None,
        can_recruit_ground=recruit,
        links=links,
        ground=ground or None,
        can_launch=(False if not operational else None),
        runway_repair_turns_remaining=repair_turns,
    )


def _squadron_flyable(sq: Squadron, grounded: bool) -> int:
    """Aircraft this squadron can actually launch this turn: min(untasked, available pilots),
    0 if grounded (enemy-held base or cratered runway / sunk hull) or pilotless. Pilots don't
    cap it when pilot limits are off. This is what the planner can really field — untasked
    alone overstates it."""
    if grounded or sq.untasked_aircraft <= 0:
        return 0
    if not sq.pilot_limits_enabled:
        return sq.untasked_aircraft
    return min(sq.untasked_aircraft, sq.number_of_available_pilots)


def _squadron_grounded(sq: Squadron, player: Player | None) -> bool:
    """The squadron can't launch this turn: its base is enemy-held, or the runway is
    cratered / the carrier hull is sunk. The engine's mission planner excludes it either
    way, so flag it rather than advertise phantom flyable aircraft to the planner."""
    if player is not None and sq.location.captured != player:
        return True
    return not sq.location.runway_is_operational()


def idle_flyable_total(game: Game, side: str) -> int:
    """Total launchable-now aircraft still untasked across the side's air wing (the headline
    'force left on the ramp' number)."""
    player = player_for_side(side)
    return sum(
        _squadron_flyable(sq, _squadron_grounded(sq, player))
        for sq in coalition_for_side(game, side).air_wing.iter_squadrons()
    )


def build_squadron(sq: Squadron, player: Player | None = None) -> SquadronView:
    # A squadron that can't sortie (enemy-held base, or a cratered runway / sunk
    # hull) is excluded by the engine's mission planner, so flag it instead of
    # advertising phantom flyable aircraft to the planner.
    grounded = _squadron_grounded(sq, player)
    return SquadronView(
        id=str(sq.id),
        name=str(sq),
        aircraft=sq.aircraft.display_name,
        base=sq.location.name,
        owned=sq.owned_aircraft or None,
        untasked=sq.untasked_aircraft or None,
        flyable=_squadron_flyable(sq, grounded) or None,
        pending=sq.pending_deliveries or None,
        pilots=sq.number_of_available_pilots,
        max_ac=(sq.max_size if sq.settings.enable_squadron_aircraft_limits else None),
        grounded=grounded or None,
    )


def _damage_word(tgo) -> str | None:
    """Short damage state for a target, or None if at full strength."""
    try:
        units = list(tgo.units)
        if not units:
            return None
        alive = sum(1 for u in units if getattr(u, "alive", True))
        total = len(units)
        if alive >= total:
            return None
        if alive == 0:
            return "destroyed"
        return "lightly damaged" if alive / total > 0.6 else "heavily damaged"
    except Exception:
        return None


def _unit_composition(tgo) -> dict[str, int] | None:
    """Alive-unit count per class for a target group. For ships: hulls per class, so the
    planner can identify Aegis escorts (Constellation/Ticonderoga). For SAM sites: alive
    launchers/radars per type, exposing PARTIAL damage (2 of 4 TELs left), not just
    alive/dead.
    """
    comp: dict[str, int] = {}
    for u in getattr(tgo, "units", []):
        if not getattr(u, "alive", True):
            continue
        name = None
        try:
            ut = u.unit_type
            name = getattr(ut, "display_name", None) if ut else None
        except Exception:
            name = None
        if not name:
            name = getattr(getattr(u, "type", None), "name", None)
        if name:
            comp[str(name)] = comp.get(str(name), 0) + 1
    return comp or None


def _build_target(game: Game, tgo, kind: str, task: str) -> TargetView:
    ll = DcsPoint(tgo.position.x, tgo.position.y, game.theater.terrain).latlng()
    threat = None
    max_range = getattr(tgo, "max_threat_range", None)
    if max_range is not None:
        try:
            rng = max_range()
            threat = int(rng.nautical_miles) if rng else None
        except Exception:
            threat = None
    group_id = None
    composition = None
    if kind == "ship":
        grp = getattr(tgo, "control_point", None)
        group_id = str(grp.id) if grp is not None else None
        composition = _unit_composition(tgo)
    elif kind == "sam":
        # Alive launchers/radars per type — shows partial battle damage on a SAM site
        # (e.g. TELs killed but the radar still up), not just alive/dead.
        composition = _unit_composition(tgo)
    return TargetView(
        id=str(tgo.id),
        name=tgo.name,
        kind=kind,
        suggested_task=task,
        pos=[_r(ll.lat), _r(ll.lng)],
        threat_nm=threat or None,
        group_id=group_id,
        composition=composition,
        damage=_damage_word(tgo),
        iads_role=_iads_role(tgo),
    )


def _iads_role(tgo) -> str | None:
    """This site's role in the IADS, or None if it plays no part in one.

    A ground object carries the role on its groups, so a power station reads as
    "PowerSource" instead of an anonymous code-named building. Point defenses and
    plain objects report nothing, matching what Skynet actually wires up.
    """
    from game.theater.theatergroup import IadsGroundGroup

    for group in getattr(tgo, "groups", []):
        if isinstance(group, IadsGroundGroup) and group.iads_role.participate:
            return str(group.iads_role.value)
    return None


def build_targets(game: Game, side: str) -> list[TargetView]:
    from game.commander.objectivefinder import ObjectiveFinder

    player = player_for_side(side)
    finder = ObjectiveFinder(game, player)
    targets: list[TargetView] = []
    for sam in finder.enemy_air_defenses():
        targets.append(_build_target(game, sam, "sam", "DEAD"))
    for ship in finder.enemy_ships():
        targets.append(_build_target(game, ship, "ship", "ANTISHIP"))
    for building in finder.strike_targets():
        targets.append(_build_target(game, building, "building", "STRIKE"))
    # Motorpools are their own finder: strike_targets() only yields buildings, so
    # without this the LLM could not see (or hit) the enemy's undeployed armor
    # reserve that the human player and the built-in AI commander both target.
    for motorpool in finder.motorpool_targets():
        targets.append(_build_target(game, motorpool, "motorpool", "BAI"))
    for front in game.theater.conflicts():
        friendly_cp = front.red_cp if player.is_red else front.blue_cp
        enemy_cp = front.blue_cp if player.is_red else front.red_cp
        ll = DcsPoint(front.position.x, front.position.y, game.theater.terrain).latlng()
        targets.append(
            TargetView(
                id=str(front.id),
                name=front.name,
                kind="front",
                suggested_task="CAS",
                pos=[_r(ll.lat), _r(ll.lng)],
                friendly_cp_id=str(friendly_cp.id),
                enemy_cp_id=str(enemy_cp.id),
            )
        )
    return targets


def build_own_sams(game: Game, side: str) -> list[TargetView]:
    """Your own live SAM sites (friendly IADS) — for drawing your air-defense
    umbrellas alongside the enemy's. Not part of the text turn_context."""
    from game.commander.objectivefinder import ObjectiveFinder
    from game.theater.theatergroundobject import IadsGroundObject

    finder = ObjectiveFinder(game, player_for_side(side))
    out: list[TargetView] = []
    for cp in finder.friendly_control_points():
        for go in cp.ground_objects:
            if not go.is_dead and isinstance(go, IadsGroundObject):
                out.append(_build_target(game, go, "sam", "DEAD"))
    return out


_THREAT_TOP_N = (
    12  # cap the ranked digest; the full per-target ranges stay in targets[]
)


def build_threats(targets: list[TargetView]) -> list[ThreatView]:
    """The strongest enemy air-defense umbrellas (radar SAMs + SAM-armed ships), ranked
    by reach — the route-shaping threats. A frugal digest derived from ``targets`` so the
    planner doesn't have to sort them itself; the long-range ones dominate, which is
    exactly what a strike route must avoid or suppress."""
    ranked = sorted(
        (t for t in targets if t.kind in ("sam", "ship") and t.threat_nm),
        key=lambda t: t.threat_nm or 0,
        reverse=True,
    )
    return [
        ThreatView(
            id=t.id, name=t.name, kind=t.kind, threat_nm=t.threat_nm or 0, pos=t.pos
        )
        for t in ranked[:_THREAT_TOP_N]
    ]


def _naval_view(game: Game, obj, kind: str) -> NavalView:
    """A NavalView from either a ShipGroundObject (kind='ship') or a movable naval
    control point / carrier (kind='carrier') — both expose position, max_move_distance,
    and target_position the same way."""
    ll = DcsPoint(obj.position.x, obj.position.y, game.theater.terrain).latlng()
    dest = None
    tp = getattr(obj, "target_position", None)
    if tp is not None:
        dll = DcsPoint(tp.x, tp.y, game.theater.terrain).latlng()
        dest = [_r(dll.lat), _r(dll.lng)]
    threat = None
    max_range = getattr(obj, "max_threat_range", None)
    if callable(max_range):
        try:
            rng = max_range()
            threat = int(rng.nautical_miles) if rng else None
        except Exception:
            threat = None
    comp = _unit_composition(obj)
    hull_owner = obj
    if comp is None:
        # A carrier/LHA is a control point whose hulls live in its is_control_point
        # ship ground object rather than on the CP itself; dig them out so carriers
        # report composition too.
        for sub in getattr(obj, "ground_objects", []):
            if getattr(sub, "is_control_point", False):
                comp = _unit_composition(sub)
                hull_owner = sub
                break
    return NavalView(
        id=str(obj.id),
        name=obj.name,
        kind=kind,
        pos=[_r(ll.lat), _r(ll.lng)],
        move_range_nm=int(obj.max_move_distance.nautical_miles),
        destination=dest,
        threat_nm=threat or None,
        damage=_damage_word(obj),
        composition=comp,
        cruise_missiles_remaining=_cruise_missiles_remaining(game, hull_owner),
    )


def _cruise_missiles_remaining(game: Game, tgo) -> int | None:
    """The group's campaign stock of land-attack cruise missiles, or None when it has
    none — an ordinary frigate should not carry a noisy `0` through the transport. A
    naval group can hold several TheaterGroups, so sum them: the LLM tasks the group,
    not the individual hull rows."""
    from game.cruise_raids import tgo_magazines

    total = sum(remaining for _, remaining in tgo_magazines(game, tgo))
    return total or None


def _fleet_has_living_hull(cp) -> bool:
    """Whether a fleet control point still has any hull afloat. A dead FLAGSHIP only
    stops aviation (that's what ``runway_is_operational`` measures); surviving escorts
    keep sailing, and the map UI still lets the player drag such a fleet — so the AI
    must keep seeing and moving it too (else the survivors become invisible ghosts)."""
    for tgo in getattr(cp, "ground_objects", []):
        if getattr(tgo, "is_control_point", False):
            return any(u.alive for u in tgo.units)
    return False


def build_my_naval(game: Game, side: str) -> list[NavalView]:
    """The side's OWN repositionable naval groups — combatant ship groups
    (ShipGroundObject) AND carriers/LHAs (movable naval control points). These are what
    ``move_ship`` can reposition; the LLM can't see them via the enemy-only ``targets``
    list, so surface them here with their move range and any pending destination."""
    from game.theater.theatergroundobject import ShipGroundObject

    player = player_for_side(side)
    out: list[NavalView] = []
    for cp in game.theater.controlpoints:
        if cp.captured != player:
            continue
        # the carrier/LHA itself is a movable control point (a different id namespace
        # than its escort ship groups below) — skip it only when EVERY hull is sunk
        # (nothing left to move), mirroring the is_dead skip for ship groups below.
        # NOT runway_is_operational: that is the carrier-AVIATION check, and a fleet
        # that lost its flagship still sails (composition reports the survivors).
        if (
            getattr(cp, "moveable", False)
            and getattr(cp, "is_fleet", False)
            and _fleet_has_living_hull(cp)
        ):
            out.append(_naval_view(game, cp, "carrier"))
        for tgo in cp.ground_objects:
            if not isinstance(tgo, ShipGroundObject) or not tgo.moveable:
                continue
            if getattr(tgo, "is_dead", False):
                continue
            out.append(_naval_view(game, tgo, "ship"))
    return out


def _tgo_repairables(tgo) -> tuple[int, list]:
    """(total_cost, [(unit, cost), …]) for a ground object's dead, not-already-repairing
    units, mirroring the player's manual-repair UI. A BUILDING (oil/factory/ammo/…) is
    repaired as a WHOLE for one ``repair_cost()`` — its income statics have no unit_type
    (so their unit-level ``repairable`` is False), yet the building itself is repairable
    whenever it has a repair cost; this was the gap that hid oil/econ from ``repairs``.
    Other ground objects are priced per dead unit. Empty list = nothing to repair here.
    """
    from game.theater.theatergroundobject import BuildingGroundObject

    if isinstance(tgo, BuildingGroundObject):
        if not getattr(tgo, "repairable", False):
            return 0, []
        dead = [
            u
            for u in tgo.statics
            if not getattr(u, "alive", True)
            and getattr(u, "repair_turns_remaining", None) is None
        ]
        if not dead:
            return 0, []
        try:
            cost = int(tgo.repair_cost())
        except Exception:
            cost = 0
        if cost <= 0:
            return 0, []
        # Billed once for the whole building: the first dead static carries the cost,
        # the rest carry 0 so they all revive without being charged again.
        return cost, [(dead[0], cost)] + [(u, 0) for u in dead[1:]]

    out: list = []
    total = 0
    for u in tgo.units:
        if getattr(u, "alive", True) or not getattr(u, "repairable", False):
            continue
        if getattr(u, "repair_turns_remaining", None) is not None:
            continue  # already under repair
        ut = getattr(u, "unit_type", None)
        cost = int(getattr(ut, "price", 0)) if ut else 0
        if cost <= 0:
            continue
        total += cost
        out.append((u, cost))
    return total, out


def build_repairs(game: Game, side: str) -> list[RepairView]:
    """The side's OWN damaged-but-repairable assets it can pay to fix: dead SAM/EWR units,
    buildings, and cratered runways. (Repairs also happen automatically from leftover
    budget at end of turn — this list is what you can choose to fix *now*.)"""
    from game.config import RUNWAY_REPAIR_COST
    from game.theater.theatergroundobject import BuildingGroundObject

    player = player_for_side(side)
    out: list[RepairView] = []
    for cp in game.theater.controlpoints:
        if cp.captured != player:
            continue
        try:
            if getattr(cp, "runway_can_be_repaired", False):
                out.append(
                    RepairView(
                        id=str(cp.id),
                        name=cp.name,
                        kind="runway",
                        cost=int(RUNWAY_REPAIR_COST),
                    )
                )
        except Exception:
            pass
        for tgo in cp.ground_objects:
            cost, units = _tgo_repairables(tgo)
            if cost <= 0 or not units:
                continue
            # Category is the kind for everything: SAM sites -> aa/ewr, economy buildings
            # -> oil/factory/ammo (so a dead income asset is identifiable, not just "building").
            kind = str(getattr(tgo, "category", None) or "ground")
            income = None
            if isinstance(tgo, BuildingGroundObject):
                from game.config import REWARDS

                income = int(REWARDS.get(kind, 0)) or None
            out.append(
                RepairView(
                    id=str(tgo.id),
                    name=tgo.name,
                    kind=kind,
                    cost=cost,
                    dead_units=len(units),
                    income_per_turn=income,
                )
            )
    return out


def build_buyable_ground(game: Game, side: str) -> list[GroundUnitView]:
    faction = coalition_for_side(game, side).faction
    out: list[GroundUnitView] = []
    for kind, units in (
        ("front", faction.frontline_units),
        ("artillery", faction.artillery_units),
    ):
        for u in sorted(units, key=lambda x: x.display_name):
            out.append(
                GroundUnitView(
                    name=u.display_name, price=int(getattr(u, "price", 0)), kind=kind
                )
            )
    return out


def build_turn_context(game: Game, side: str = "red") -> TurnContextView:
    side = side.lower()
    coalition = coalition_for_side(game, side)
    targets = build_targets(game, side)
    return TurnContextView(
        side=side,
        situation=build_situation(game),
        economy=build_economy(game, side),
        control_points=[
            build_control_point(game, cp) for cp in game.theater.controlpoints
        ],
        air_wing=[
            build_squadron(sq, player_for_side(side))
            for sq in coalition.air_wing.iter_squadrons()
        ],
        idle_flyable=idle_flyable_total(game, side),
        targets=targets,
        threats=build_threats(targets),
        naval=build_my_naval(game, side),
        repairs=build_repairs(game, side),
        buyable_ground=build_buyable_ground(game, side),
    )


def build_settings(game: Game) -> SettingsView:
    from game.theater.controlpoint import RUNWAY_REPAIR_TURNS

    s = game.settings
    return SettingsView(
        opfor_aggressiveness_pct=s.opfor_autoplanner_aggressiveness,
        map_coalition_visibility=getattr(
            s.map_coalition_visibility, "name", str(s.map_coalition_visibility)
        ),
        desired_player_mission_duration_min=int(
            s.desired_player_mission_duration.total_seconds() // 60
        ),
        player_income_multiplier=s.player_income_multiplier,
        enemy_income_multiplier=s.enemy_income_multiplier,
        crashes_dont_count=s.ignore_non_combat_air_losses,
        pilot_replenishment_per_squadron=(
            int(s.squadron_replenishment_rate)
            if getattr(s, "enable_squadron_pilot_limits", True)
            else None
        ),
        squadron_pilot_limit=(
            int(s.squadron_pilot_limit)
            if getattr(s, "enable_squadron_pilot_limits", True)
            else None
        ),
        runway_repair_turns=RUNWAY_REPAIR_TURNS,
        cruise_missile_strikes=s.cruise_missile_strikes,
        cruise_missile_auto_raids=s.cruise_missile_auto_raids,
    )


def _flight_loadout(flight):
    """(loadout name, {pylon: clsid}) from the flight's first member, or (None, None)."""
    try:
        member = next(iter(flight.iter_members()), None)
    except Exception:
        member = None
    loadout = getattr(member, "loadout", None)
    if loadout is None:
        return None, None
    weapons = {
        num: weapon.clsid
        for num, weapon in loadout.pylons.items()
        if weapon is not None
    }
    return loadout.name, (weapons or None)


def build_flight(flight) -> FlightView:
    missing = flight.missing_pilots
    missing_count = len(missing) if hasattr(missing, "__len__") else int(missing)
    loadout_name, weapons = _flight_loadout(flight)
    return FlightView(
        id=str(flight.id),
        task=_enum_str(flight.flight_type),
        aircraft=flight.unit_type.display_name,
        count=flight.count,
        squadron=str(flight.squadron),
        start=_enum_str(flight.start_type),
        dep=getattr(flight.departure, "name", None),
        clients=flight.client_count or None,
        uncrewed=missing_count or None,
        loadout=loadout_name,
        weapons=weapons,
    )


def build_package(index: int, pkg) -> PackageView:
    tot = pkg.time_over_target
    desc = getattr(pkg, "custom_name", None)  # the planner stores the rationale here
    if not desc:
        desc = pkg.package_description
        if callable(desc):
            desc = desc()
    return PackageView(
        index=index,
        target=getattr(pkg.target, "name", str(pkg.target)),
        task=_enum_str(pkg.primary_task),
        tot=tot.strftime("%H:%M") if tot else None,
        desc=desc or None,
        flights=[build_flight(f) for f in pkg.flights],
    )


def build_packages(game: Game, side: str = "red") -> list[PackageView]:
    ato = coalition_for_side(game, side).ato
    return [build_package(i, p) for i, p in enumerate(ato.packages)]


def build_prev_turns(game: Game, n: int = 3) -> list[TurnForcesView]:
    """The last ``n`` turns' force totals (blue=allied, red=enemy in game_stats),
    merged with that turn's debriefed losses when available."""
    data = game.game_stats.data_per_turn
    losses_by_turn = {
        d.get("turn"): d for d in getattr(game, "debrief_history", []) or []
    }
    start = max(0, len(data) - n)
    out: list[TurnForcesView] = []
    for i in range(start, len(data)):
        td = data[i]
        loss = losses_by_turn.get(i, {})
        out.append(
            TurnForcesView(
                turn=i,
                blue_aircraft=td.allied_units.aircraft_count,
                blue_vehicles=td.allied_units.vehicles_count,
                red_aircraft=td.enemy_units.aircraft_count,
                red_vehicles=td.enemy_units.vehicles_count,
                blue_air_lost=loss.get("blue_air_lost") or None,
                red_air_lost=loss.get("red_air_lost") or None,
                blue_air_crashed=loss.get("blue_air_crashed") or None,
                red_air_crashed=loss.get("red_air_crashed") or None,
                blue_ground_lost=loss.get("blue_ground_lost") or None,
                red_ground_lost=loss.get("red_ground_lost") or None,
                red_air_lost_by_type=loss.get("red_air_lost_by_type") or None,
                blue_air_lost_by_type=loss.get("blue_air_lost_by_type") or None,
                red_air_kills_by_weapon=loss.get("red_air_kills_by_weapon") or None,
                blue_air_kills_by_weapon=loss.get("blue_air_kills_by_weapon") or None,
                red_air_kills_by_victim=loss.get("red_air_kills_by_victim") or None,
                blue_air_kills_by_victim=loss.get("blue_air_kills_by_victim") or None,
                red_air_killers=loss.get("red_air_killers") or None,
                blue_air_killers=loss.get("blue_air_killers") or None,
                blue_air_combat=(
                    (loss.get("blue_air_lost", 0) - loss.get("blue_air_crashed", 0))
                    or None
                ),
                red_air_combat=(
                    (loss.get("red_air_lost", 0) - loss.get("red_air_crashed", 0))
                    or None
                ),
                blue_sites_lost=loss.get("blue_sites_lost") or None,
                red_sites_lost=loss.get("red_sites_lost") or None,
            )
        )
    return out


# --- ground-object rebuild (parity with the player's Buy-ground-object dialog) ---


def _ground_object_role_and_tasks(tgo):
    """(GroupRole, [GroupTask]) usable to rebuild a ground object, mirroring
    QGroundObjectBuyMenu (SAM/EWR/armor/ship/missile/coastal). Raises ValueError for a
    TGO type the dialog can't rebuild (e.g. a building)."""
    from game.data.groups import GroupRole, GroupTask
    from game.theater.theatergroundobject import (
        CoastalSiteGroundObject,
        EwrGroundObject,
        MissileSiteGroundObject,
        SamGroundObject,
        ShipGroundObject,
        VehicleGroupGroundObject,
    )

    tasks: list[GroupTask] = []
    # EWR before SAM: EwrGroundObject is a subclass of IadsGroundObject like SAM, but
    # SamGroundObject is not in its MRO — order is defensive, not load-bearing.
    if isinstance(tgo, EwrGroundObject):
        role = GroupRole.AIR_DEFENSE
        tasks.append(GroupTask.EARLY_WARNING_RADAR)
    elif isinstance(tgo, SamGroundObject):
        role = GroupRole.AIR_DEFENSE
    elif isinstance(tgo, VehicleGroupGroundObject):
        role = GroupRole.GROUND_FORCE
    elif isinstance(tgo, ShipGroundObject):
        role = GroupRole.NAVAL
        tasks.append(GroupTask.NAVY)
    elif isinstance(tgo, MissileSiteGroundObject):
        role = GroupRole.DEFENSES
        tasks.append(GroupTask.MISSILE)
    elif isinstance(tgo, CoastalSiteGroundObject):
        role = GroupRole.DEFENSES
        tasks.append(GroupTask.COASTAL)
    else:
        raise ValueError(
            f"{getattr(tgo, 'name', tgo)} is a {type(tgo).__name__}, which can't be "
            f"rebuilt (only SAM/EWR/armor/ship/missile/coastal sites)"
        )
    if not tasks:
        tasks = role.tasks
    return role, tasks


def ground_object_role_tasks(tgo):
    """The GroupTasks whose ForceGroups can rebuild ``tgo`` (see the dialog mapping)."""
    return _ground_object_role_and_tasks(tgo)[1]


def _resolve_tgo(game: Game, tgo_id: str, side: str):
    """Resolve a ground-object id to a TGO you own, or raise ValueError."""
    from uuid import UUID

    try:
        tgo = game.db.tgos.get(UUID(str(tgo_id)))
    except (KeyError, ValueError, AttributeError, TypeError):
        raise ValueError(f"no ground object with id {tgo_id!r}")
    if tgo.control_point.captured != player_for_side(side):
        raise ValueError(f"{tgo.name} is not yours")
    return tgo


def _layout_option(force_group, layout) -> LayoutOption | None:
    """Build a LayoutOption for one force-group + layout, or None if it has no usable
    unit group. Mirrors the QTgoLayoutGroupRow LayoutException skip (a unit_group with no
    unit types AND no statics is dropped)."""
    slots: list[GroupSlotView] = []
    price = 0
    for tgo_group in layout.groups:
        for unit_group in tgo_group.unit_groups:
            unit_types = [
                UnitTypeOption(name=ut.display_name, price=int(ut.price))
                for ut in force_group.unit_types_for_group(unit_group)
            ]
            has_static = (
                next(force_group.statics_for_group(unit_group), None) is not None
            )
            if not unit_types and not has_static:
                continue  # unusable by this faction — skip (LayoutException parity)
            default_count = unit_group.group_size
            slots.append(
                GroupSlotView(
                    group_name=tgo_group.group_name,
                    optional=unit_group.optional,
                    default_count=default_count,
                    max_count=unit_group.max_size,
                    unit_types=unit_types,
                )
            )
            # Default price: non-optional (or would-be-enabled) groups at the first unit
            # type * default count. Statics-only groups price at 0 (no unit types).
            if not unit_group.optional and unit_types:
                price += default_count * unit_types[0].price
    if not slots:
        return None
    return LayoutOption(
        force_group=force_group.name,
        layout=layout.name,
        price=int(price),
        groups=slots,
    )


def build_ground_object_options(
    game: Game, side: str, tgo_id: str
) -> GroundObjectOptionsView:
    """What a ground object (SAM/EWR/armor/ship/missile/coastal site) can be rebuilt into
    and at what cost — the read behind the player's Buy-ground-object dialog. Lists every
    force-group + layout available to the faction for this TGO's role, each layout's
    selectable unit types and counts, and the default net price context (the old site's
    ``value`` is refunded on rebuild)."""
    tgo = _resolve_tgo(game, tgo_id, side)
    role, tasks = _ground_object_role_and_tasks(tgo)
    coalition = coalition_for_side(game, side)
    options: list[LayoutOption] = []
    for force_group in coalition.armed_forces.groups_for_tasks(tasks):
        for layout in force_group.layouts:
            try:
                option = _layout_option(force_group, layout)
            except Exception:
                continue  # one bad layout must not sink the whole response
            if option is not None:
                options.append(option)
    return GroundObjectOptionsView(
        tgo_id=str(tgo.id),
        name=tgo.name,
        role=role.name.lower(),
        refund=int(tgo.value),
        budget=round(coalition.budget),
        options=options,
    )


def build_iads(game: Game, side: str) -> IadsView:
    """The ENEMY IADS as a graph: every participating site and what feeds it.

    The player sees these links on the campaign map, so the planner gets them too.
    Only the opponent's half is returned — this is a targeting aid, not a view of
    one's own network. Dead nodes are kept: knowing a power station is already down
    is what tells you the radars behind it are blind.
    """
    player = player_for_side(side)
    network = game.theater.iads_network
    nodes: list[IadsNodeView] = []
    for node in network.nodes:
        tgo = node.group.ground_object
        if tgo.is_friendly(player):
            continue  # ours, not a target
        if not node.group.iads_role.participate:
            continue
        depends = [
            str(conn.ground_object.id)
            for conn in node.connections.values()
            if conn.ground_object.id != tgo.id
        ]
        nodes.append(
            IadsNodeView(
                id=str(tgo.id),
                name=tgo.name,
                role=str(node.group.iads_role.value),
                alive=node.group.alive_units > 0,
                depends_on=sorted(set(depends)) or None,
            )
        )
    return IadsView(advanced=network.advanced_iads, nodes=nodes)
