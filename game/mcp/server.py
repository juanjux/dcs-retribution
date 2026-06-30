"""FastMCP tools for the OPFOR-AI feature.

Every tool delegates to ``game.agent.service`` — the SAME functions the REST routes
call — so the two transports never diverge. Mounted at ``/mcp`` by
``game/server/app.py``. Reads return frugal dicts (``exclude_none``) for token economy.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from game.agent import service

mcp = FastMCP(
    "DCS Retribution OPFOR AI",
    instructions=(
        "Plan the enemy (red/OPFOR) turn of a DCS Retribution campaign. Call "
        "`start` then `howtoplay` once, then on each 'your turn': set_ai_active, "
        "read turn_context/get_packages, create_packages / buy / stances, "
        "set_ai_active(false)."
    ),
    stateless_http=True,
    json_response=True,
    # The sub-app's own route lives at "/"; app.py mounts it at "/mcp", so the
    # connector URL is http://host:port/mcp (not /mcp/mcp).
    streamable_http_path="/",
    # Single-user tool with user-controlled exposure: don't reject by Host header
    # so a tunnel (claude.ai connector) reaches it. The localhost bind and the
    # user's own tunnel are the boundary — add token auth + a host allowlist before
    # exposing more widely.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def _dump(obj: Any) -> Any:
    if isinstance(obj, list):
        return [_dump(x) for x in obj]
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=True)
    return obj


# --- reads ---


@mcp.tool()
def turn_context(side: str = "red") -> dict:
    """Operational picture: situation, economy, control points, air wing."""
    return _dump(service.turn_context(side))


@mcp.tool()
def settings() -> dict:
    """Campaign settings the planner reads (aggressiveness, fog, mission window)."""
    return _dump(service.settings())


@mcp.tool()
def get_packages(side: str = "red") -> list:
    """Current ATO for a side — packages and flights with stable ids."""
    return _dump(service.get_packages(side))


@mcp.tool()
def start() -> str:
    """Start-here briefing: role, per-turn workflow, the tool catalog."""
    return service.start_doc("")


@mcp.tool()
def howtoplay() -> str:
    """The OPFOR commander's full briefing (packages, fair play, doctrine)."""
    return service.howtoplay_doc()


@mcp.tool()
def turn_status() -> dict:
    """AI-session snapshot (active/status/cancelled) plus the current turn number."""
    return service.turn_status()


# --- writes ---


@mcp.tool()
def create_packages(side: str, packages: list[dict]) -> list:
    """Plan packages: each spec is target_id + flights[{task,count,escort?}] + rationale."""
    return _dump(service.create_packages(side, packages))


@mcp.tool()
def evaluate_package(side: str, package: dict) -> dict:
    """Dry-run ONE package spec (target_id + flights[{task,count,escort?}]) to see its
    time-over-target and whether it fits the mission window — WITHOUT committing it.
    Use this to check a strike's feasibility/timing before create_packages."""
    return _dump(service.evaluate_package(side, package))


@mcp.tool()
def delete_package(side: str, index: int) -> dict:
    """Remove a package by its index (frees its aircraft/pilots)."""
    return _dump(service.delete_package(side, index))


@mcp.tool()
def clear_packages(side: str) -> dict:
    """Remove all of a side's packages (start the turn over)."""
    return _dump(service.clear_packages(side))


@mcp.tool()
def buy_aircraft(side: str, squadron_id: str, quantity: int = 1) -> dict:
    """Order aircraft into a squadron (arrive next turn; spends budget)."""
    return _dump(service.buy_aircraft(side, squadron_id, quantity))


@mcp.tool()
def sell_aircraft(side: str, squadron_id: str, quantity: int = 1) -> dict:
    """Sell untasked aircraft from a squadron (refunds budget)."""
    return _dump(service.sell_aircraft(side, squadron_id, quantity))


@mcp.tool()
def buy_ground(side: str, cp_id: str, unit_name: str, quantity: int = 1) -> dict:
    """Order ground units of a type (from turn_context.buyable_ground) at your base."""
    return _dump(service.buy_ground(side, cp_id, unit_name, quantity))


@mcp.tool()
def set_stance(side: str, friendly_cp_id: str, enemy_cp_id: str, stance: str) -> dict:
    """Set the ground stance at the front between two control points."""
    return _dump(service.set_stance(side, friendly_cp_id, enemy_cp_id, stance))


@mcp.tool()
def relocate_squadron(side: str, squadron_id: str, dest_cp_id: str) -> dict:
    """Relocate a squadron to another of your bases (arrives over time, not instant)."""
    return _dump(service.relocate_squadron(side, squadron_id, dest_cp_id))


@mcp.tool()
def transfer_ground(
    side: str,
    origin_cp_id: str,
    dest_cp_id: str,
    unit_name: str,
    quantity: int = 1,
    by_air: bool = False,
) -> dict:
    """Transfer existing ground units between two of your bases (land, or by_air to airlift)."""
    return _dump(
        service.transfer_ground(
            side, origin_cp_id, dest_cp_id, unit_name, quantity, by_air
        )
    )


@mcp.tool()
def set_ai_active(active: bool = True) -> dict:
    """Mark the AI busy/idle. Take Off is blocked while active (toolbar robot lit)."""
    return service.set_ai_active(active)


@mcp.tool()
def set_ai_status(text: str) -> dict:
    """Set the one-line status shown in the robot info window."""
    return service.set_ai_status(text)


# --- memory ---


@mcp.tool()
def get_stored_context() -> dict:
    """Your saved per-campaign strategy notes (key -> value), persisted in the save."""
    return service.get_stored_context()


@mcp.tool()
def put_stored_context(data: dict) -> dict:
    """Replace ALL your stored notes with `data` (a key->value object)."""
    return service.put_stored_context(data)


@mcp.tool()
def post_stored_context(data: dict) -> dict:
    """Merge `data` into your stored notes (add/update keys; keeps the rest)."""
    return service.post_stored_context(data)


@mcp.tool()
def delete_stored_context(key: str) -> dict:
    """Remove one note key from stored_context."""
    return service.delete_stored_context(key)


@mcp.tool()
def human_notes() -> dict:
    """The player's campaign notes — guidance for you to read (read-only)."""
    return service.human_notes()


@mcp.tool()
def prev_turns(n: int = 3) -> list:
    """Force totals over the last n turns — the attrition trend to react to."""
    return _dump(service.prev_turns(n))
