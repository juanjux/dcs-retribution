"""REST transport for the OPFOR-AI feature.

Thin shims over ``game.agent.service`` (the single source of truth). The MCP
transport (Phase 3) registers the same service calls, so behaviour never drifts.
Every route requires the per-process token (``?token=`` or ``X-API-Key``).
Per-turn reads serialise with ``exclude_none`` to stay token-frugal.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from game.agent import schemas, service, views
from game.server.security import ApiKeyManager

router: APIRouter = APIRouter(
    prefix="/retribution-ai",
    dependencies=[Depends(ApiKeyManager.verify)],
)


@router.get(
    "/turn_context",
    operation_id="ai_turn_context",
    response_model=views.TurnContextView,
    response_model_exclude_none=True,
)
def turn_context(side: str = "red") -> views.TurnContextView:
    return service.turn_context(side)


@router.get(
    "/settings",
    operation_id="ai_settings",
    response_model=views.SettingsView,
)
def settings() -> views.SettingsView:
    return service.settings()


@router.get(
    "/packages",
    operation_id="ai_packages",
    response_model=list[views.PackageView],
    response_model_exclude_none=True,
)
def packages(side: str = "red") -> list[views.PackageView]:
    return service.get_packages(side)


@router.get(
    "/validate",
    operation_id="ai_validate",
    response_model=schemas.ValidateResult,
    response_model_exclude_none=True,
)
def validate_plan(side: str = "red") -> schemas.ValidateResult:
    return service.validate_plan(side)


@router.get("/capabilities", operation_id="ai_capabilities")
def capabilities() -> dict:
    return service.capabilities()


@router.get("/start", operation_id="ai_start", response_class=PlainTextResponse)
def start(request: Request) -> PlainTextResponse:
    base_url = str(request.base_url).rstrip("/") + "/retribution-ai"
    return PlainTextResponse(service.start_doc(base_url), media_type="text/markdown")


@router.get("/howtoplay", operation_id="ai_howtoplay", response_class=PlainTextResponse)
def howtoplay() -> PlainTextResponse:
    return PlainTextResponse(service.howtoplay_doc(), media_type="text/markdown")


# --- write path ---


@router.post(
    "/packages",
    operation_id="ai_create_packages",
    response_model=list[schemas.CreateResult],
    response_model_exclude_none=True,
)
def create_packages(body: schemas.CreatePackagesRequest) -> list[schemas.CreateResult]:
    return service.create_packages(body.side, body.packages)


@router.post(
    "/packages/evaluate",
    operation_id="ai_evaluate_package",
    response_model=schemas.EvaluateResult,
    response_model_exclude_none=True,
)
def evaluate_package(body: schemas.EvaluatePackageRequest) -> schemas.EvaluateResult:
    return service.evaluate_package(body.side, body.package)


@router.delete(
    "/packages",
    operation_id="ai_clear_packages",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def clear_packages(side: str = "red") -> schemas.OpResult:
    return service.clear_packages(side)


@router.delete(
    "/packages/{index}",
    operation_id="ai_delete_package",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def delete_package(index: int, side: str = "red") -> schemas.OpResult:
    return service.delete_package(side, index)


@router.post(
    "/buy/aircraft",
    operation_id="ai_buy_aircraft",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def buy_aircraft(body: schemas.BuyAircraftRequest) -> schemas.OpResult:
    return service.buy_aircraft(body.side, body.squadron_id, body.quantity)


@router.post(
    "/sell/aircraft",
    operation_id="ai_sell_aircraft",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def sell_aircraft(body: schemas.BuyAircraftRequest) -> schemas.OpResult:
    return service.sell_aircraft(body.side, body.squadron_id, body.quantity)


@router.post(
    "/buy/ground",
    operation_id="ai_buy_ground",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def buy_ground(body: schemas.BuyGroundRequest) -> schemas.OpResult:
    return service.buy_ground(body.side, body.cp_id, body.unit_name, body.quantity)


@router.post(
    "/stances",
    operation_id="ai_set_stance",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def set_stance(body: schemas.StanceRequest) -> schemas.OpResult:
    return service.set_stance(
        body.side, body.friendly_cp_id, body.enemy_cp_id, body.stance
    )


@router.post(
    "/squadron/relocate",
    operation_id="ai_relocate_squadron",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def relocate_squadron(body: schemas.RelocateSquadronRequest) -> schemas.OpResult:
    return service.relocate_squadron(body.side, body.squadron_id, body.dest_cp_id)


@router.post(
    "/ground/transfer",
    operation_id="ai_transfer_ground",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def transfer_ground(body: schemas.TransferGroundRequest) -> schemas.OpResult:
    return service.transfer_ground(
        body.side,
        body.origin_cp_id,
        body.dest_cp_id,
        body.unit_name,
        body.quantity,
        body.by_air,
    )


@router.post(
    "/naval/move",
    operation_id="ai_move_ship",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def move_ship(body: schemas.MoveShipRequest) -> schemas.OpResult:
    return service.move_ship(body.side, body.ship_id, body.lat, body.lng)


@router.post(
    "/repair",
    operation_id="ai_repair",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def repair(body: schemas.RepairRequest) -> schemas.OpResult:
    return service.repair(body.side, body.id)


# --- session / Take-Off gate ---


@router.post("/ai/active", operation_id="ai_set_active")
def set_ai_active(active: bool = True) -> dict:
    return service.set_ai_active(active)


@router.post("/ai/status", operation_id="ai_set_status")
def set_ai_status(text: str) -> dict:
    return service.set_ai_status(text)


@router.get("/turn_status", operation_id="ai_turn_status")
def turn_status() -> dict:
    return service.turn_status()


# --- memory ---


@router.get("/stored_context", operation_id="ai_get_stored_context")
def get_stored_context() -> dict:
    return service.get_stored_context()


@router.put("/stored_context", operation_id="ai_put_stored_context")
def put_stored_context(body: dict) -> dict:
    return service.put_stored_context(body)


@router.post("/stored_context", operation_id="ai_post_stored_context")
def post_stored_context(body: dict) -> dict:
    return service.post_stored_context(body)


@router.delete("/stored_context/{key}", operation_id="ai_delete_stored_context_key")
def delete_stored_context(key: str) -> dict:
    return service.delete_stored_context(key)


@router.delete("/stored_context", operation_id="ai_clear_stored_context")
def clear_stored_context() -> dict:
    return service.clear_stored_context()


@router.get("/human_notes", operation_id="ai_human_notes")
def human_notes() -> dict:
    return service.human_notes()


@router.get(
    "/prev_turns",
    operation_id="ai_prev_turns",
    response_model=list[views.TurnForcesView],
)
def prev_turns(n: int = 3) -> list[views.TurnForcesView]:
    return service.prev_turns(n)
