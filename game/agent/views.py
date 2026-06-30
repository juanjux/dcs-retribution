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


class SquadronView(BaseModel):
    id: str
    name: str
    aircraft: str
    base: str
    owned: int | None = None  # aircraft on hand (omitted when 0)
    untasked: int | None = None  # available to task (omitted when 0)
    pending: int | None = None  # arriving next turn (omitted when 0)
    pilots: int
    grounded: bool | None = (
        None  # base is enemy-held — can't sortie this turn (else omitted)
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
    kind: str  # sam / ship / building / front
    suggested_task: str  # DEAD / ANTISHIP / STRIKE / CAS
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
    blue_ground_lost: int | None = None
    red_ground_lost: int | None = None
    red_air_killers: dict[str, int] | None = None  # what killed red's aircraft
    blue_air_killers: dict[str, int] | None = None  # what killed blue's aircraft


class TurnContextView(BaseModel):
    side: str
    situation: SituationView
    economy: EconomyView
    control_points: list[ControlPointView]
    air_wing: list[SquadronView]
    targets: list[TargetView]  # enemy objects this side can strike (aim by id)
    threats: list[ThreatView]  # blue's strongest air-defense umbrellas, ranked by reach
    naval: list[NavalView]  # YOUR movable ship groups (reposition with move_ship)
    buyable_ground: list[GroundUnitView]  # ground units this faction can buy


class SettingsView(BaseModel):
    """The campaign settings the OPFOR planner reads (and never changes)."""

    opfor_aggressiveness_pct: int  # risk-tolerance hint the player set for red
    map_coalition_visibility: str  # fog-of-war level (drives the intel filter)
    desired_player_mission_duration_min: int  # TOT window the player flies within
    player_income_multiplier: float
    enemy_income_multiplier: float
    pilot_replenishment_per_squadron: int | None = (
        None  # new pilots each squadron regains per turn (up to the limit); omitted = no pilot limits (unlimited)
    )
    squadron_pilot_limit: int | None = (
        None  # max active pilots per squadron (omitted = no limit)
    )


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
    return ControlPointView(
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
    )


def build_squadron(sq: Squadron, player: Player | None = None) -> SquadronView:
    # A squadron stranded at an enemy-held base cannot generate sorties — the
    # engine's mission planner excludes it — so flag it instead of advertising
    # phantom flyable aircraft to the planner.
    grounded = player is not None and sq.location.captured != player
    return SquadronView(
        id=str(sq.id),
        name=str(sq),
        aircraft=sq.aircraft.display_name,
        base=sq.location.name,
        owned=sq.owned_aircraft or None,
        untasked=sq.untasked_aircraft or None,
        pending=sq.pending_deliveries or None,
        pilots=sq.number_of_available_pilots,
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
    if kind == "ship":
        grp = getattr(tgo, "control_point", None)
        group_id = str(grp.id) if grp is not None else None
    return TargetView(
        id=str(tgo.id),
        name=tgo.name,
        kind=kind,
        suggested_task=task,
        pos=[_r(ll.lat), _r(ll.lng)],
        threat_nm=threat or None,
        group_id=group_id,
        damage=_damage_word(tgo),
    )


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
    return NavalView(
        id=str(obj.id),
        name=obj.name,
        kind=kind,
        pos=[_r(ll.lat), _r(ll.lng)],
        move_range_nm=int(obj.max_move_distance.nautical_miles),
        destination=dest,
        threat_nm=threat or None,
        damage=_damage_word(obj),
    )


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
        # than its escort ship groups below)
        if getattr(cp, "moveable", False) and getattr(cp, "is_fleet", False):
            out.append(_naval_view(game, cp, "carrier"))
        for tgo in cp.ground_objects:
            if not isinstance(tgo, ShipGroundObject) or not tgo.moveable:
                continue
            if getattr(tgo, "is_dead", False):
                continue
            out.append(_naval_view(game, tgo, "ship"))
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
        targets=targets,
        threats=build_threats(targets),
        naval=build_my_naval(game, side),
        buyable_ground=build_buyable_ground(game, side),
    )


def build_settings(game: Game) -> SettingsView:
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
    )


def build_flight(flight) -> FlightView:
    missing = flight.missing_pilots
    missing_count = len(missing) if hasattr(missing, "__len__") else int(missing)
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
                blue_ground_lost=loss.get("blue_ground_lost") or None,
                red_ground_lost=loss.get("red_ground_lost") or None,
                red_air_killers=loss.get("red_air_killers") or None,
                blue_air_killers=loss.get("blue_air_killers") or None,
            )
        )
    return out
