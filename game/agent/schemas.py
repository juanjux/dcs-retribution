"""Input specs and write-result DTOs for the OPFOR-AI feature.

These are what the LLM POSTs (specs) and what it gets back (results). Kept terse
for the same token-economy reasons as the read DTOs in ``views.py``.
"""

from __future__ import annotations

from pydantic import BaseModel

from game.agent import views


class FlightSpec(BaseModel):
    task: str  # FlightType, e.g. STRIKE / DEAD / BARCAP / OCA_RUNWAY / CAS / ANTISHIP
    count: int = 2  # aircraft in this flight; CAPPED at the airframe's max_group_size
    # (usually 4), same as the player's flight creator — for a bigger raid add more flights
    escort: str | None = None  # air / sead / ewar / refuel — pruned if not needed
    squadron_id: str | None = (
        None  # force this squadron/airframe (from turn_context.air_wing) instead of
        # letting the engine auto-pick; works even if the engine wouldn't auto-assign it
        # (mirrors the player picking it by hand)
    )
    loadout: str | dict[int, str] | None = (
        None  # payload: a named loadout ("Retribution Anti-ship", from /aircraft/loadouts)
        # OR a custom {pylon_number: weapon_clsid} map (build it from /aircraft/pylons).
        # Omit to use the engine default for the task.
    )


class PackageSpec(BaseModel):
    target_id: str  # id of a control point or ground object (from turn_context/targets)
    flights: list[FlightSpec]
    rationale: str | None = None  # one line "why this exists" — shown to the player
    asap: bool = True
    ignore_range: bool = (
        False  # plan even if the target is past the auto-planner's range limit — a
        # capable but far airframe the human could send manually (accept the fuel risk)
    )
    tot_minutes: int | None = (
        None  # desired Time-On-Target as MINUTES after mission start (0 = start), the same
        # unit evaluate returns as tot_minutes_into_mission. Omit for ASAP. Use it to stagger
        # or synchronise packages (deconflict a multi-axis strike, avoid self-collisions).
    )


class DroppedFlight(BaseModel):
    """A flight that was requested but could NOT be included in the package."""

    flight: str  # which flight (task + squadron), e.g. "DEAD from Won Pat"
    reason: str  # why it was dropped (no free aircraft / out of range / escort w/o parent …)


class CreateResult(BaseModel):
    ok: bool
    target: str
    error: str | None = None
    package: views.PackageView | None = None
    dropped: list[DroppedFlight] | None = (
        None  # flights that COULDN'T be filled and were left out (the package is planned
        # with the rest — partial by default). Present only when something was dropped —
        # ALWAYS check it: the strike may be missing its SEAD/escort, or be under-strength.
    )
    idle_flyable_remaining: int | None = (
        None  # aircraft you can still LAUNCH after this package (untasked + crewed) — keep
        # tasking until it's 0, so you don't leave force on the ramp. Set on a successful create.
    )


class EvaluateResult(BaseModel):
    """Dry-run of a package: what it WOULD look like if created, without committing it."""

    ok: bool
    target: str
    error: str | None = None
    package: views.PackageView | None = None  # planned but NOT added to the ATO
    tot_minutes_into_mission: int | None = None  # 0 = turn start
    mission_window_min: int | None = None  # the player's setting
    within_window: bool | None = None  # False = arrives late (wasted / needs a tanker)


class PackageCheck(BaseModel):
    index: int
    target: str
    tot: str | None = None  # HH:MM
    tot_minutes_into_mission: int | None = None
    within_window: bool | None = None
    uncrewed: int | None = None  # missing pilot slots in this package (omitted when 0)


class ValidateResult(BaseModel):
    """A health check of the whole committed plan (no changes made)."""

    ok: bool  # True = every package is crewed and within the mission window
    mission_window_min: int
    packages: list[PackageCheck]
    issues: list[str] | None = None  # human-readable problems (omitted when none)


class OpResult(BaseModel):
    ok: bool
    detail: str | None = None
    error: str | None = None


# --- REST request bodies ---


class CreatePackagesRequest(BaseModel):
    side: str = "red"
    packages: list[PackageSpec]


class EvaluatePackageRequest(BaseModel):
    side: str = "red"
    package: PackageSpec


class PackageTotRequest(BaseModel):
    side: str = "red"
    tot_minutes: int | None = None  # minutes into the mission; null resets to ASAP


class ValidatePayloadRequest(BaseModel):
    side: str = "red"
    squadron_id: str
    payload: dict[int, str]  # {pylon_number: weapon_clsid} to check


class WaypointEditRequest(BaseModel):
    side: str = "red"
    flight_id: str
    waypoint_idx: int  # 1-based; 0 (takeoff) is immovable. Waypoints can't be deleted.
    lat: float | None = None
    lng: float | None = None
    alt_m: float | None = None  # new altitude in metres (optional)


class BuyAircraftRequest(BaseModel):
    side: str = "red"
    squadron_id: str
    quantity: int = 1


class BuyGroundRequest(BaseModel):
    side: str = "red"
    cp_id: str
    unit_name: str
    quantity: int = 1


class StanceRequest(BaseModel):
    side: str = "red"
    friendly_cp_id: str
    enemy_cp_id: str
    stance: str


class RelocateSquadronRequest(BaseModel):
    side: str = "red"
    squadron_id: str
    dest_cp_id: str


class TransferGroundRequest(BaseModel):
    side: str = "red"
    origin_cp_id: str
    dest_cp_id: str
    unit_name: str
    quantity: int = 1
    by_air: bool = False


class MoveShipRequest(BaseModel):
    side: str = "red"
    ship_id: str  # a ship-group OR carrier id from turn_context.naval
    lat: float | None = None  # destination; omit lat AND lng to cancel a pending move
    lng: float | None = None


class RepairRequest(BaseModel):
    side: str = "red"
    id: str  # a repair-target id from turn_context.repairs (ground object/building/runway)
