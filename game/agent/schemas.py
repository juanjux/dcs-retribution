"""Input specs and write-result DTOs for the OPFOR-AI feature.

These are what the LLM POSTs (specs) and what it gets back (results). Kept terse
for the same token-economy reasons as the read DTOs in ``views.py``.
"""

from __future__ import annotations

from pydantic import BaseModel

from game.agent import views


class FlightSpec(BaseModel):
    task: str  # FlightType, e.g. STRIKE / DEAD / BARCAP / OCA_RUNWAY / CAS / ANTISHIP
    count: int = 2
    escort: str | None = None  # air / sead / ewar / refuel — pruned if not needed


class PackageSpec(BaseModel):
    target_id: str  # id of a control point or ground object (from turn_context/targets)
    flights: list[FlightSpec]
    rationale: str | None = None  # one line "why this exists" — shown to the player
    asap: bool = True


class CreateResult(BaseModel):
    ok: bool
    target: str
    error: str | None = None
    package: views.PackageView | None = None


class OpResult(BaseModel):
    ok: bool
    detail: str | None = None
    error: str | None = None


# --- REST request bodies ---


class CreatePackagesRequest(BaseModel):
    side: str = "red"
    packages: list[PackageSpec]


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
