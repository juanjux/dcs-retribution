"""REST transport for the OPFOR-AI feature.

Thin shims over ``game.agent.service`` (the single source of truth). The MCP
transport (Phase 3) registers the same service calls, so behaviour never drifts.
Every route requires the per-process token (``?token=`` or ``X-API-Key``).
Per-turn reads serialise with ``exclude_none`` to stay token-frugal.
"""

from fastapi import APIRouter, Depends

from game.agent import service, views
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
