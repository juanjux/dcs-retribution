"""Read DTOs for the OPFOR-AI feature.

Pure functions over a ``Game`` (no ``GameContext``, no Qt) so they are unit-testable
and importable without PySide6. ``service.py`` wires these to the live game.
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


class LatLng(BaseModel):
    lat: float
    lng: float


class SituationView(BaseModel):
    turn: int
    date: str
    time_of_day: str
    campaign_state: str  # ongoing / red_winning / red_losing (RED's perspective)


class EconomyView(BaseModel):
    budget: float
    income_next_turn: float


class ControlPointView(BaseModel):
    id: str
    name: str
    type: str
    owner: str  # red / blue / neutral
    position: LatLng
    squadron_count: int


class SquadronView(BaseModel):
    id: str
    name: str
    aircraft: str
    base: str
    owned_aircraft: int
    untasked_aircraft: int
    pending_deliveries: int
    available_pilots: int


class TurnContextView(BaseModel):
    side: str
    situation: SituationView
    economy: EconomyView
    control_points: list[ControlPointView]
    air_wing: list[SquadronView]


class SettingsView(BaseModel):
    """The campaign settings the OPFOR planner reads (and never changes)."""

    opfor_aggressiveness_pct: int  # risk tolerance hint the player set for red
    map_coalition_visibility: str  # fog-of-war level (drives the intel filter)
    desired_player_mission_duration_min: int  # TOT window the player flies within
    player_income_multiplier: float
    enemy_income_multiplier: float


class FlightView(BaseModel):
    id: str
    task: str | None
    aircraft: str
    count: int
    squadron: str
    squadron_id: str
    client_slots: int  # player-controlled seats
    missing_pilots: int  # uncrewed seats — must be 0 before the turn can start
    departure: str | None
    start_type: str | None


class PackageView(BaseModel):
    index: int  # position in the ATO (stable within a turn snapshot)
    target: str
    primary_task: str | None
    time_over_target: str | None
    description: str | None
    flights: list[FlightView]


def _latlng(game: Game, point: DcsPoint) -> LatLng:
    # Mirror game/server/leaflet.py: build a terrain-aware Point before converting.
    ll = DcsPoint(point.x, point.y, game.theater.terrain).latlng()
    return LatLng(lat=ll.lat, lng=ll.lng)


def build_situation(game: Game) -> SituationView:
    return SituationView(
        turn=game.turn,
        date=game.current_day.isoformat(),
        time_of_day=game.current_turn_time_of_day.name,
        campaign_state=_CAMPAIGN_STATE_FROM_RED.get(
            game.check_win_loss().name, "ongoing"
        ),
    )


def build_economy(game: Game, side: str) -> EconomyView:
    player = player_for_side(side)
    return EconomyView(
        budget=game.coalition_for(player).budget,
        income_next_turn=Income(game, player).total,
    )


def build_control_point(game: Game, cp: ControlPoint) -> ControlPointView:
    return ControlPointView(
        id=str(cp.id),
        name=cp.name,
        type=cp.cptype.name,
        owner=cp.captured.value.lower(),
        position=_latlng(game, cp.position),
        squadron_count=sum(1 for _ in cp.squadrons),
    )


def build_squadron(sq: Squadron) -> SquadronView:
    return SquadronView(
        id=str(sq.id),
        name=str(sq),
        aircraft=sq.aircraft.display_name,
        base=sq.location.name,
        owned_aircraft=sq.owned_aircraft,
        untasked_aircraft=sq.untasked_aircraft,
        pending_deliveries=sq.pending_deliveries,
        available_pilots=sq.number_of_available_pilots,
    )


def build_turn_context(game: Game, side: str = "red") -> TurnContextView:
    side = side.lower()
    coalition = coalition_for_side(game, side)
    return TurnContextView(
        side=side,
        situation=build_situation(game),
        economy=build_economy(game, side),
        control_points=[
            build_control_point(game, cp) for cp in game.theater.controlpoints
        ],
        air_wing=[build_squadron(sq) for sq in coalition.air_wing.iter_squadrons()],
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
    )


def _enum_str(value: object) -> str | None:
    if value is None:
        return None
    member_value = getattr(value, "value", None)
    if member_value is not None:
        return str(member_value)
    return getattr(value, "name", None) or str(value)


def build_flight(flight) -> FlightView:
    missing = flight.missing_pilots
    missing_count = len(missing) if hasattr(missing, "__len__") else int(missing)
    return FlightView(
        id=str(flight.id),
        task=_enum_str(flight.flight_type),
        aircraft=flight.unit_type.display_name,
        count=flight.count,
        squadron=str(flight.squadron),
        squadron_id=str(flight.squadron.id),
        client_slots=flight.client_count,
        missing_pilots=missing_count,
        departure=getattr(flight.departure, "name", None),
        start_type=_enum_str(flight.start_type),
    )


def build_package(index: int, pkg) -> PackageView:
    tot = pkg.time_over_target
    desc = pkg.package_description
    if callable(desc):
        desc = desc()
    return PackageView(
        index=index,
        target=getattr(pkg.target, "name", str(pkg.target)),
        primary_task=_enum_str(pkg.primary_task),
        time_over_target=tot.isoformat() if tot else None,
        description=desc or None,
        flights=[build_flight(f) for f in pkg.flights],
    )


def build_packages(game: Game, side: str = "red") -> list[PackageView]:
    ato = coalition_for_side(game, side).ato
    return [build_package(i, p) for i, p in enumerate(ato.packages)]
