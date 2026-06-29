"""Service layer for the OPFOR-AI feature — the single source of truth.

Both transports (REST routers in ``game/server/retributionai/`` and the MCP tools in
``game/mcp/``) call these functions, so all behaviour lives here and never drifts
between transports. Functions resolve the live game lazily via ``GameContext`` so the
module stays importable without a running server (and without Qt).
"""

from __future__ import annotations

import re
from pathlib import Path
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


def create_packages(side, specs):
    """Plan packages from the LLM's specs (reusing the engine). Lazy-imports the
    write path so the read service stays light."""
    from game.agent import planner

    return planner.create_packages(_require_game(), side, specs)


_DOCS_DIR = Path(__file__).parent / "docs"
_LEADING_COMMENT = re.compile(r"\A\s*<!--.*?-->\s*", re.DOTALL)


def _render_doc(name: str, subs: dict[str, str]) -> str:
    text = (_DOCS_DIR / name).read_text(encoding="utf-8")
    text = _LEADING_COMMENT.sub("", text, count=1)  # drop the editorial header
    for key, value in subs.items():
        text = text.replace("{" + key + "}", value)
    return text


def start_doc(base_url: str) -> str:
    """The /start welcome doc, with {BASE_URL} filled in (read once per session)."""
    return _render_doc("start.md", {"BASE_URL": base_url.rstrip("/")})


def howtoplay_doc() -> str:
    """The OPFOR briefing; fills in the red faction when a game is loaded."""
    subs: dict[str, str] = {}
    try:
        from game.server import GameContext

        game = GameContext.get()
    except Exception:
        game = None
    if game is not None:
        faction = game.red.faction
        subs["RED_FACTION"] = faction.name or "the RED faction"
        subs["RED_COUNTRY"] = faction.country.name
    return _render_doc("howtoplay.md", subs)
