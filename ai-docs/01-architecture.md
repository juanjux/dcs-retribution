# 01 — Architecture

## One service layer, two transports, one live game

The whole feature is built on **infrastructure that already exists**. The Qt app
already runs a FastAPI server in-process on a background thread
(`qt_ui/main.py:522` → `Server(...).run_in_thread()`), bound to the **live `Game`**
via `GameContext` (`game/server/dependencies.py:13`). We add to it.

```
Qt process (exactly ONE live Game)
└─ FastAPI app  (game/server/app.py — already started in a thread)
     ├─ existing map/render routers + /eventstream            (unchanged)
     ├─ NEW REST routers     /retribution-ai/*   ─┐
     │      (desktop agents curl GET/POST)         │  both delegate to the
     └─ NEW MCP sub-app      mounted at /mcp      ─┤  SAME service layer
            (web LLMs via connector; enables POST)─┘
                                                   │
                                                   ▼
                              game/agent/service.py   ← single source of truth
                              (pure Python; operates on GameContext.require())
                                                   │
                                                   ▼
                 engine: PackageFulfiller, PurchaseAdapter, initialize_turn,
                         ObjectiveFinder, theater, debrief, QtCallbacks…
```

**The non-duplication rule:** all logic lives in `game/agent/service.py`. A REST
route handler and the matching MCP tool are each a 3-line shim that calls the same
service function. Add an operation once; both transports get it.

### Why two transports

| | REST (`/retribution-ai/*`) | MCP over HTTP (`/mcp`) |
|---|---|---|
| Audience | Desktop agents (Claude Code) | Web LLMs (claude.ai connector); any MCP client |
| Setup | Paste URL; agent curls it. **No config files.** | Add URL as a custom connector once. |
| Reads | GET | tools/resources |
| **Writes** | POST (agent can curl arbitrary POST) | **tools** (this is the reason MCP exists here — a web LLM can't POST via plain browsing, but it *can* call an MCP tool) |

Same data, same operations, served from the same service layer.

## How the two transports compose (verified 2026-06)

FastMCP can be mounted into the existing FastAPI/Starlette app, sharing the
process and the live `Game`:

```python
# game/server/app.py (sketch of the additions)
from contextlib import asynccontextmanager, AsyncExitStack
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DCS Retribution OPFOR AI", stateless_http=True, json_response=True)
# ... register MCP tools/resources in game/mcp/, all delegating to game/agent/service ...

@asynccontextmanager
async def lifespan(app):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())   # REQUIRED
        yield

app = FastAPI(lifespan=lifespan)
app.include_router(...)                     # existing routers
app.include_router(retribution_ai_router)   # NEW REST
app.mount("/mcp", mcp.streamable_http_app())  # NEW MCP (endpoint ends up at /mcp)
```

- `mcp.session_manager.run()` **must** be in the host app's lifespan or the MCP
  endpoint won't work. The existing `app` has no lifespan today, so this is new.
- `stateless_http=True, json_response=True` keep it simple (no long-lived SSE
  session needed; one request/response per tool call).
- **Decided: mount into the existing FastAPI app (one port)** — simplest, one
  process, one URL. Only if wiring the lifespan into the thread-started uvicorn
  proves impossible would you fall back to a sibling port in the same process
  (non-duplication still holds, since both call `game/agent/service`); but mount is
  the plan.

> The service layer is the contract; the two transports share one ASGI app on one
> port.

## New code layout

```
game/
  agent/                 # NEW — pure Python, no mcp/http/Qt deps where avoidable
    __init__.py
    service.py           # the single source of truth: turn_context, packages,
                         #   prev_turns, stored_context, settings, human_notes,
                         #   planning_dialog/status, turn-handshake, howtoplay, map-visibility (intel) filter
    views.py             # pydantic read-models (DTOs returned to the LLM)
    planner.py           # write ops over PackageFulfiller / PurchaseAdapter / stances
    schemas.py           # pydantic: package/flight specs, plan intents, DTOs
  server/
    retributionai/       # NEW REST routers (thin shims → game/agent/service)
      routes.py
      models.py
  mcp/                   # NEW — FastMCP tools/resources (thin shims → service)
    __init__.py
    server.py            # FastMCP instance + tool/resource registration
```

Only `game/mcp/` (and the mount in `game/server/app.py`) import `mcp`. Keeping the
dependency isolated matters for the eventual `dev` PR ([`07`](07-branching-pr-and-risks.md)).

## The bootstrap URL & "start" document

`GET /retribution-ai/start` (and the MCP equivalent resource/prompt) returns the
**bootstrap document** the LLM reads first: what DCS World and Retribution are, the
LLM's role as OPFOR planner, the list of operations, and the recommended workflow
(read `howtoplay` once → read `turn_context` + `prev_turns` + `stored_context` →
plan → POST packages/buys → optionally update `stored_context`). It's served from
`game/agent/service.py` so REST and MCP return identical content.

The **Settings panel** shows this URL (with the token) and one line each for the
desktop-paste and web-connector flows.

## Auth & exposure (bake in from day 1)

- **Token, always.** Reuse the per-process `X-API-Key` pattern
  (`game/server/security.py`) but also accept it as a **URL query token** so the
  user can hand a single clickable URL to an agent: `…/start?token=<KEY>`. The
  moment the port is exposed, the URL is the only thing standing between the
  internet and the player's game — make the token mandatory and long.
- **Localhost vs. exposed.** `127.0.0.1` works for a desktop agent on the same
  machine over plain HTTP (no TLS needed locally). For a **web** LLM the user must
  expose the port (port-forward or a tunnel like cloudflared/ngrok); the tunnel
  terminates TLS, so we don't need self-signed certs in-app. Document this; don't
  bind to `0.0.0.0` by default.
- **CORS:** the existing app locks CORS to `file://`. The new MCP/REST surface for
  external agents needs its own allowance; scope it as tightly as the chosen
  client requires.

## Concurrency (simpler than it sounds here)

The Qt UI, the server thread, and the sim (`GameLoopTimer`, a real
`threading.Timer`) all touch the one `Game`. But the feature's **writes happen at
one safe moment: the OPFOR-planning step**, between missions, when the sim isn't
advancing flights. So:

- Allow **mutating** calls (POST packages, buys, `plan_opfor_turn`) only when the
  game is at a turn/planning boundary (sim paused); reject mid-sim with a clear
  error. Reads are always fine.
- Put a lock around the planning mutations (`initialize_turn` + ATO edits) so a UI
  action and an API call can't interleave.
- Push a `GameUpdateEvents` onto `EventStream` after mutations so the web map UI
  refreshes (mirror `Game.pass_turn`, `game/game.py:367`).

## Security note on inputs

External LLM input only ever flows through the service layer, which routes it into
**validated engine calls** (task/target compatibility, range, inventory, budget).
A malformed request fails that one operation; it cannot corrupt the turn. Never
`eval`/`pickle` anything from the API. (Pickle only appears in normal save/load,
not in this API.)
