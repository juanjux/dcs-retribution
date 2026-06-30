"""Write path for the OPFOR-AI feature.

Turns the LLM's intents into real game state by reusing the engine — the same
PackageFulfiller/PackageBuilder the scripted commander uses (see
game/commander/tasks/packageplanningtask.py), so flight planning, squadron
selection, escorts, loadouts and budgeting come for free. Every op returns a
structured per-item result so partial failures are reported, not raised.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union
from uuid import UUID

from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType, ProposedFlight, ProposedMission
from game.commander.packagefulfiller import PackageFulfiller
from game.profiling import MultiEventTracer

from game.agent import schemas, views

if TYPE_CHECKING:
    from game import Game
    from game.theater import MissionTarget


_ESCORTS = {
    "air": EscortType.AirToAir,
    "airtoair": EscortType.AirToAir,
    "cap": EscortType.AirToAir,
    "escort": EscortType.AirToAir,
    "sead": EscortType.Sead,
    "dead": EscortType.Sead,
    "refuel": EscortType.Refuel,
    "tanker": EscortType.Refuel,
}


def _flight_type(name: str) -> FlightType:
    raw = name.strip()
    key = raw.upper().replace(" ", "_").replace("-", "_")
    try:
        return FlightType[key]
    except KeyError:
        pass
    for ft in FlightType:
        if str(getattr(ft, "value", "")).upper() == raw.upper():
            return ft
    raise ValueError(f"unknown task {name!r}")


def _escort_type(name: str | None) -> EscortType | None:
    if not name:
        return None
    key = name.strip().lower().replace(" ", "").replace("-", "")
    try:
        return _ESCORTS[key]
    except KeyError:
        raise ValueError(f"unknown escort type {name!r}")


def _mission_window_min(game: Game) -> int:
    """The player's desired mission duration in whole minutes (the TOT window).

    Settings stores it as a ``timedelta`` named ``desired_player_mission_duration``;
    an earlier ``..._min`` attribute lookup never matched and silently fell back to 60,
    so a non-default window (e.g. 80) was ignored by evaluate/validate."""
    dur = getattr(game.settings, "desired_player_mission_duration", None)
    if dur is None:
        return 60
    try:
        return int(dur.total_seconds() // 60)
    except AttributeError:
        return int(dur)  # tolerate a plain-number setting


def resolve_target(game: Game, target_id: str) -> MissionTarget:
    """Resolve a target id to a control point or ground object."""
    try:
        uid: UUID | None = UUID(str(target_id))
    except (ValueError, AttributeError, TypeError):
        uid = None
    if uid is not None:
        try:
            cp = game.theater.find_control_point_by_id(uid)
        except Exception:
            cp = None  # raises (not returns None) when the id is not a control point
        if cp is not None:
            return cp
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            if str(tgo.id) == str(target_id):
                return tgo
    for front in game.theater.conflicts():
        if str(front.id) == str(target_id):
            return front
    raise ValueError(f"no target with id {target_id!r}")


def _coerce(spec: Union[schemas.PackageSpec, dict]) -> schemas.PackageSpec:
    return (
        spec if isinstance(spec, schemas.PackageSpec) else schemas.PackageSpec(**spec)
    )


def create_packages(
    game: Game, side: str, specs: list[Union[schemas.PackageSpec, dict]]
) -> list[schemas.CreateResult]:
    """Plan one package per spec, reusing PackageFulfiller, and add it to the ATO."""
    coalition = views.coalition_for_side(game, side)
    now = game.conditions.start_time
    results: list[schemas.CreateResult] = []
    with MultiEventTracer() as tracer:
        for raw in specs:
            spec = _coerce(raw)
            target_name = spec.target_id
            try:
                target = resolve_target(game, spec.target_id)
                target_name = getattr(target, "name", spec.target_id)
                proposed = [
                    ProposedFlight(
                        _flight_type(f.task), f.count, _escort_type(f.escort)
                    )
                    for f in spec.flights
                ]
                fulfiller = PackageFulfiller(
                    coalition, game.theater, game.db.flights, game.settings
                )
                package = fulfiller.plan_mission(
                    ProposedMission(target, proposed, asap=spec.asap),
                    1,
                    now,
                    tracer,
                )
                if package is None:
                    results.append(
                        schemas.CreateResult(
                            ok=False,
                            target=target_name,
                            error="could not fulfil — no capable aircraft in range, "
                            "or the mission was scrubbed (e.g. flight into a live SAM)",
                        )
                    )
                    continue
                coalition.ato.add_package(package)
                package.set_tot_asap(now)
                if spec.rationale:
                    package.custom_name = spec.rationale
                index = len(coalition.ato.packages) - 1
                results.append(
                    schemas.CreateResult(
                        ok=True,
                        target=target_name,
                        package=views.build_package(index, package),
                    )
                )
            except Exception as exc:  # report, don't abort the whole batch
                results.append(
                    schemas.CreateResult(ok=False, target=target_name, error=str(exc))
                )
    return results


def evaluate_package(
    game: Game, side: str, spec: Union[schemas.PackageSpec, dict]
) -> schemas.EvaluateResult:
    """Dry-run a package: plan it, compute its time-over-target, and report whether the
    TOT fits the player's mission window — WITHOUT committing it (the plan is rolled
    back). Lets the LLM check feasibility + timing before deciding to create it."""
    coalition = views.coalition_for_side(game, side)
    now = game.conditions.start_time
    spec = _coerce(spec)
    target_name = spec.target_id
    try:
        target = resolve_target(game, spec.target_id)
        target_name = getattr(target, "name", spec.target_id)
        proposed = [
            ProposedFlight(_flight_type(f.task), f.count, _escort_type(f.escort))
            for f in spec.flights
        ]
        with MultiEventTracer() as tracer:
            fulfiller = PackageFulfiller(
                coalition, game.theater, game.db.flights, game.settings
            )
            package = fulfiller.plan_mission(
                ProposedMission(target, proposed, asap=spec.asap), 1, now, tracer
            )
        if package is None or not package.flights:
            return schemas.EvaluateResult(
                ok=False,
                target=target_name,
                error="could not fulfil — no capable aircraft free/in range, or the "
                "mission was scrubbed (e.g. flight into a live SAM)",
            )
        # plan_mission already CLAIMS the aircraft; add then remove so they are released
        # again (a package's aircraft are returned when it leaves the ATO) — net-zero.
        coalition.ato.add_package(package)
        try:
            package.set_tot_asap(now)
            view = views.build_package(-1, package)
            tot = package.time_over_target
            window = _mission_window_min(game)
            tot_min = round((tot - now).total_seconds() / 60) if tot else None
            return schemas.EvaluateResult(
                ok=True,
                target=target_name,
                package=view,
                tot_minutes_into_mission=tot_min,
                mission_window_min=window,
                within_window=(tot_min is not None and tot_min <= window),
            )
        finally:
            coalition.ato.remove_package(package)
    except Exception as exc:
        return schemas.EvaluateResult(ok=False, target=target_name, error=str(exc))


def validate_plan(game: Game, side: str) -> schemas.ValidateResult:
    """Health-check the whole committed plan (no changes): every package's TOT vs the
    mission window and whether any flight is uncrewed (not enough pilots)."""
    coalition = views.coalition_for_side(game, side)
    window = _mission_window_min(game)
    now = game.conditions.start_time
    checks: list[schemas.PackageCheck] = []
    issues: list[str] = []
    for i, pkg in enumerate(coalition.ato.packages):
        view = views.build_package(i, pkg)
        tot = pkg.time_over_target
        tot_min = round((tot - now).total_seconds() / 60) if tot else None
        within = tot_min is not None and tot_min <= window
        uncrewed = sum((f.uncrewed or 0) for f in view.flights)
        if not view.flights:
            issues.append(f"#{i} {view.target}: no flights (empty package)")
        if uncrewed:
            issues.append(
                f"#{i} {view.target}: {uncrewed} uncrewed flight slot(s) — not enough pilots"
            )
        if tot_min is not None and not within:
            issues.append(
                f"#{i} {view.target}: TOT {tot_min} min is past the {window}-min window"
            )
        checks.append(
            schemas.PackageCheck(
                index=i,
                target=view.target,
                tot=view.tot,
                tot_minutes_into_mission=tot_min,
                within_window=within,
                uncrewed=uncrewed or None,
            )
        )
    return schemas.ValidateResult(
        ok=not issues,
        mission_window_min=window,
        packages=checks,
        issues=issues or None,
    )


def _resolve_squadron(game: Game, side: str, squadron_id: str):
    coalition = views.coalition_for_side(game, side)
    for squadron in coalition.air_wing.iter_squadrons():
        if str(squadron.id) == str(squadron_id):
            return squadron
    raise ValueError(f"no squadron with id {squadron_id!r}")


def _resolve_cp(game: Game, cp_id: str):
    try:
        uid = UUID(str(cp_id))
    except (ValueError, AttributeError, TypeError):
        raise ValueError(f"invalid control point id {cp_id!r}")
    try:
        cp = game.theater.find_control_point_by_id(uid)
    except Exception:
        cp = None
    if cp is None:
        raise ValueError(f"no control point with id {cp_id!r}")
    return cp


def delete_package(game: Game, side: str, index: int) -> schemas.OpResult:
    """Remove a package (by its turn_context index). Frees its aircraft/pilots."""
    try:
        ato = views.coalition_for_side(game, side).ato
        if index < 0 or index >= len(ato.packages):
            raise ValueError(f"no package at index {index}")
        pkg = ato.packages[index]
        target = getattr(pkg.target, "name", "?")
        ato.remove_package(pkg)
        return schemas.OpResult(ok=True, detail=f"removed package {index} ({target})")
    except ValueError as exc:
        return schemas.OpResult(ok=False, error=str(exc))


def clear_packages(game: Game, side: str) -> schemas.OpResult:
    """Remove all of ``side``'s packages (start the turn over)."""
    ato = views.coalition_for_side(game, side).ato
    n = len(ato.packages)
    ato.clear()
    return schemas.OpResult(ok=True, detail=f"cleared {n} packages")


def buy_aircraft(
    game: Game, side: str, squadron_id: str, quantity: int = 1
) -> schemas.OpResult:
    """Order ``quantity`` aircraft into a squadron (arrive next turn)."""
    from game.purchaseadapter import AircraftPurchaseAdapter, TransactionError

    try:
        squadron = _resolve_squadron(game, side, squadron_id)
        if squadron.location.captured != views.player_for_side(side):
            raise ValueError(
                f"can't reinforce {squadron} — its base {squadron.location.name} is "
                f"enemy-held (you can only buy into squadrons at your own bases)"
            )
        AircraftPurchaseAdapter(squadron.location).buy(squadron, quantity)
        budget = round(views.coalition_for_side(game, side).budget)
        return schemas.OpResult(
            ok=True,
            detail=f"ordered {quantity} {squadron.aircraft.display_name} for "
            f"{squadron} ({squadron.location.name}); budget now {budget}",
        )
    except (TransactionError, ValueError) as exc:
        return schemas.OpResult(ok=False, error=str(exc))


def sell_aircraft(
    game: Game, side: str, squadron_id: str, quantity: int = 1
) -> schemas.OpResult:
    """Sell ``quantity`` untasked aircraft from a squadron (refunds budget)."""
    from game.purchaseadapter import AircraftPurchaseAdapter, TransactionError

    try:
        squadron = _resolve_squadron(game, side, squadron_id)
        AircraftPurchaseAdapter(squadron.location).sell(squadron, quantity)
        budget = round(views.coalition_for_side(game, side).budget)
        return schemas.OpResult(
            ok=True,
            detail=f"sold {quantity} {squadron.aircraft.display_name} from "
            f"{squadron}; budget now {budget}",
        )
    except (TransactionError, ValueError) as exc:
        return schemas.OpResult(ok=False, error=str(exc))


def buy_ground(
    game: Game, side: str, cp_id: str, unit_name: str, quantity: int = 1
) -> schemas.OpResult:
    """Order ``quantity`` ground units of a type at one of ``side``'s bases."""
    from game.purchaseadapter import GroundUnitPurchaseAdapter, TransactionError

    coalition = views.coalition_for_side(game, side)
    try:
        cp = _resolve_cp(game, cp_id)
        if cp.captured != views.player_for_side(side):
            raise ValueError(f"{cp.name} is not yours")
        buyable = coalition.faction.frontline_units | coalition.faction.artillery_units
        unit = next(
            (u for u in buyable if unit_name in (u.display_name, u.variant_id)),
            None,
        )
        if unit is None:
            raise ValueError(f"{unit_name!r} is not a ground unit this faction can buy")
        if not cp.has_ground_unit_source(game):
            raise ValueError(
                f"{cp.name} can't recruit ground units (needs a factory/front nearby)"
            )
        GroundUnitPurchaseAdapter(cp, coalition, game).buy(unit, quantity)
        return schemas.OpResult(
            ok=True,
            detail=f"ordered {quantity} {unit.display_name} at {cp.name}; "
            f"budget now {round(coalition.budget)}",
        )
    except (TransactionError, ValueError) as exc:
        return schemas.OpResult(ok=False, error=str(exc))


def _resolve_naval(game: Game, naval_id: str):
    """Resolve a turn_context.naval id to a movable object: a ShipGroundObject (a tgo
    id) or a carrier/LHA naval control point (a control-point id). Returns the object or
    None. Both expose ownership, position, max_move_distance, target_position the same.
    """
    from game.theater.theatergroundobject import ShipGroundObject

    try:
        uid = UUID(str(naval_id))
    except (ValueError, AttributeError, TypeError):
        return None
    try:
        tgo = game.db.tgos.get(uid)
    except KeyError:
        tgo = None
    if isinstance(tgo, ShipGroundObject) and tgo.moveable:
        return tgo
    try:
        cp = game.theater.find_control_point_by_id(uid)
    except Exception:
        cp = None
    if cp is not None and getattr(cp, "moveable", False):
        return cp
    return None


def move_ship(
    game: Game,
    side: str,
    ship_id: str,
    lat: float | None = None,
    lng: float | None = None,
) -> schemas.OpResult:
    """Reposition one of ``side``'s own movable naval groups — a combatant ship group or
    a carrier/LHA (the player's movable-naval feature, opened to the AI). Validates
    ownership, the per-turn range cap, and an all-water route — the same checks the map
    UI enforces. The move applies at turn processing. Omit lat+lng to cancel a pending
    reposition."""
    from dcs import Point
    from dcs.mapping import LatLng

    from game.utils import meters

    player = views.player_for_side(side)
    try:
        mover = _resolve_naval(game, ship_id)
        if mover is None:
            raise ValueError(
                f"no movable ship group or carrier with id {ship_id!r} "
                f"(use an id from turn_context.naval)"
            )
        # ship groups carry their owner on their control_point; carriers ARE the cp
        owner = getattr(getattr(mover, "control_point", mover), "captured", None)
        if owner != player:
            raise ValueError(f"{mover.name} is not yours to move")
        if lat is None or lng is None:
            mover.target_position = None
            return schemas.OpResult(
                ok=True, detail=f"{mover.name}: pending move cancelled (holds position)"
            )
        point = Point.from_latlng(LatLng(float(lat), float(lng)), game.theater.terrain)
        moved_nm = round(meters(mover.position.distance_to_point(point)).nautical_miles)
        if not mover.destination_in_range(point):
            raise ValueError(
                f"destination is {moved_nm}nm away — {mover.name} can move at most "
                f"{int(mover.max_move_distance.nautical_miles)}nm per turn"
            )
        landmap = game.theater.landmap
        if landmap is not None and landmap.land_inbetween(mover.position, point):
            raise ValueError(
                f"can't move {mover.name} over land — pick an all-water destination"
            )
        mover.target_position = point
        return schemas.OpResult(
            ok=True,
            detail=f"{mover.name} repositioning {moved_nm}nm (applies at turn end)",
        )
    except Exception as exc:
        return schemas.OpResult(ok=False, error=str(exc))


def set_stance(
    game: Game, side: str, friendly_cp_id: str, enemy_cp_id: str, stance: str
) -> schemas.OpResult:
    """Set ``side``'s ground posture at the front between two control points."""
    from game.ground_forces.combat_stance import CombatStance

    aliases = {
        "defend": CombatStance.DEFENSIVE,
        "defensive": CombatStance.DEFENSIVE,
        "hold": CombatStance.DEFENSIVE,
        "aggressive": CombatStance.AGGRESSIVE,
        "push": CombatStance.AGGRESSIVE,
        "breakthrough": CombatStance.BREAKTHROUGH,
        "eliminate": CombatStance.ELIMINATION,
        "elimination": CombatStance.ELIMINATION,
        "retreat": CombatStance.RETREAT,
        "ambush": CombatStance.AMBUSH,
    }
    try:
        friendly = _resolve_cp(game, friendly_cp_id)
        enemy = _resolve_cp(game, enemy_cp_id)
        key = stance.strip().lower()
        chosen = aliases.get(key)
        if chosen is None:
            try:
                chosen = CombatStance[stance.strip().upper()]
            except KeyError:
                raise ValueError(f"unknown stance {stance!r}")
        friendly.stances[enemy.id] = chosen
        return schemas.OpResult(
            ok=True, detail=f"{friendly.name} -> {enemy.name}: {chosen.name}"
        )
    except ValueError as exc:
        return schemas.OpResult(ok=False, error=str(exc))


def relocate_squadron(
    game: Game, side: str, squadron_id: str, dest_cp_id: str
) -> schemas.OpResult:
    """Order a squadron to relocate to another of your bases (arrives over time)."""
    try:
        squadron = _resolve_squadron(game, side, squadron_id)
        dest = _resolve_cp(game, dest_cp_id)
        if dest.captured != views.player_for_side(side):
            raise ValueError(f"{dest.name} is not yours — can't relocate there")
        if dest == squadron.location:
            raise ValueError(f"{squadron} is already at {dest.name}")
        origin = squadron.location.name
        squadron.plan_relocation(dest, game.conditions.start_time)
        return schemas.OpResult(
            ok=True, detail=f"{squadron} relocating {origin} -> {dest.name}"
        )
    except Exception as exc:
        return schemas.OpResult(ok=False, error=str(exc))


def transfer_ground(
    game: Game,
    side: str,
    origin_cp_id: str,
    dest_cp_id: str,
    unit_name: str,
    quantity: int = 1,
    by_air: bool = False,
) -> schemas.OpResult:
    """Transfer existing ground units between two of your bases (land or air)."""
    from game.transfers import TransferOrder

    coalition = views.coalition_for_side(game, side)
    player = views.player_for_side(side)
    try:
        origin = _resolve_cp(game, origin_cp_id)
        dest = _resolve_cp(game, dest_cp_id)
        if origin.captured != player or dest.captured != player:
            raise ValueError("both the origin and destination base must be yours")
        if origin == dest:
            raise ValueError("origin and destination are the same base")
        armor = origin.base.armor
        unit = next(
            (
                u
                for u in armor
                if unit_name in (u.display_name, getattr(u, "variant_id", None))
            ),
            None,
        )
        if unit is None or armor.get(unit, 0) <= 0:
            have = (
                ", ".join(f"{u.display_name} x{n}" for u, n in armor.items()) or "none"
            )
            raise ValueError(
                f"{origin.name} has no {unit_name!r} to move (it has: {have})"
            )
        qty = max(1, min(quantity, armor[unit]))
        order = TransferOrder(origin, dest, {unit: qty}, request_airflift=by_air)
        # Validate the route BEFORE new_transfer — new_transfer debits the origin base
        # up front, so an unreachable destination would otherwise lose the units.
        if not order.is_completable(coalition.transfers.network_for(origin)):
            raise ValueError(
                f"no route from {origin.name} to {dest.name} for a ground transfer "
                f"(the destination isn't reachable over the supply network)"
            )
        coalition.transfers.new_transfer(order, game.conditions.start_time)
        mode = "by air" if by_air else "by land"
        return schemas.OpResult(
            ok=True,
            detail=f"transferring {qty} {unit.display_name} {origin.name} -> "
            f"{dest.name} {mode} (arrives over the next turns)",
        )
    except Exception as exc:
        return schemas.OpResult(ok=False, error=str(exc))
