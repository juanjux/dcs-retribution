"""Service layer for the OPFOR-AI feature — the single source of truth.

Both transports (REST routers in ``game/server/retributionai/`` and the MCP tools in
``game/mcp/``) call these functions, so all behaviour lives here and never drifts
between transports. Functions resolve the live game lazily via ``GameContext`` so the
module stays importable without a running server (and without Qt).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.agent import views

if TYPE_CHECKING:
    from game import Game


def _require_game() -> Game:
    # Lazy import keeps game/agent importable without the server/Qt stack.
    from game.server import GameContext

    return GameContext.require()


def turn_context(side: str = "red") -> views.TurnContextView:
    """Operational picture for ``side`` (red/blue) from the live game."""
    return views.build_turn_context(_require_game(), side)


def settings() -> views.SettingsView:
    """Campaign settings the planner reads (aggressiveness, fog, mission window)."""
    return views.build_settings(_require_game())


def get_packages(side: str = "red") -> list[views.PackageView]:
    """Current ATO for ``side`` — packages and their flights (with stable ids)."""
    return views.build_packages(_require_game(), side)
