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
    "ewar": EscortType.Ewar,
    "ew": EscortType.Ewar,
    "jamming": EscortType.Ewar,
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
