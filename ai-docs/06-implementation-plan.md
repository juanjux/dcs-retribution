# 06 — Implementation Plan

A phased plan the desktop Claude Code can execute. Each phase is independently
useful and testable. The model is **live, in-process, dual-transport** (REST +
MCP over one service layer) — see [`01`](01-architecture.md).

## File layout (recap)

```
game/
  agent/                 # NEW — single source of truth (pure Python)
    service.py           # all operations (turn_context, packages, prev_turns,
                         #   stored_context, settings, human_notes, squadrons,
                         #   planning_dialog/status, turn-handshake, howtoplay,
                         #   map-visibility/intel filter)
    views.py             # pydantic read DTOs (operational picture, intel filter)
    planner.py           # write ops → PackageFulfiller / PurchaseAdapter / stances
    schemas.py           # pydantic specs/intents/DTOs
  server/
    retributionai/routes.py + models.py   # NEW REST shims → service
    app.py               # EDIT: add lifespan(mcp.session_manager.run()),
                         #   include REST router, mount MCP at /mcp
    security.py          # EDIT: accept token via ?token= as well as X-API-Key
  mcp/server.py          # NEW — FastMCP tools/resources (shims → service)
```

Only `game/mcp/` and the mount in `game/server/app.py` import `mcp`. Keep it
isolated for the `dev` PR ([`07`](07-branching-pr-and-risks.md)).

## Dependencies

Add to `requirements.txt` (v2 is in alpha as of 2026-06; beta 2026-06-30, stable
2026-07-27):

```
mcp[cli]<2
```

The LLM is always **the client** (Claude Code / claude.ai) — the server **never**
calls an LLM API. (An embedded/in-engine LLM is out of scope; see [`03`](03-opfor-planner.md).)
So there is no `anthropic` dependency and no model/key to manage server-side.

## Phases

### Phase 0 — Service layer + read context  *(foundation)*
- `game/agent/service.py` + `views.py`: `turn_context` (OWNFOR limited per
  `map_coalition_visibility`, see [`05`](05-context-and-persistence.md)),
  `prev_turns`, `get_packages`, `settings`, `human_notes`, `howtoplay`, the `start`
  doc.
- Pure functions over `GameContext.require()`.
- **Deliverable:** can produce a faithful turn-context JSON for the live game.

### Phase 1 — REST transport + auth  *(desktop agents, no config files)*
- `game/server/retributionai/routes.py`: thin GET shims for the Phase-0 reads.
- `security.py`: accept `?token=`; settings shows the URL with the token.
- Setting **"Allow OPFOR AI control"** + the help text/URL ([`00`](00-vision-and-scope.md)).
- **Deliverable:** paste `…/start?token=…` into Claude Code → it reads context.

### Phase 2 — Write path / executor  *(the AI authors a full turn)*
- `game/agent/planner.py`: `create_packages` (PackageFulfiller; **assign pilots**,
  reject pilotless seats), buy/sell + transfers (PurchaseAdapter / `PendingTransfers`),
  stances, `schedule_all`, **move ships / waypoints** (reuse tgos/waypoints routes),
  delete ops. Structured per-item results/errors; reads return stable ids + pilots.
- REST `POST/PUT/DELETE` routes for them. Gate writes to the planning boundary.
- **Planning dialog** via the `QtCallbacks` bridge: `planning_dialog(show/hide)` +
  `set_planning_status(text)` (robot-general image + spinner + live status line).
- **Turn handshake** (§E of [`04`](04-api-reference.md)): `turn_status`,
  `wait_for_opfor_turn` (long-poll), `opfor_planning_done`; reuse eventstream
  `new_turn`. Pause turn-init at the OPFOR window with a timeout→scripted fallback.
- **Deliverable:** from Claude Code, plan a full red turn over REST; the human
  reviews red's plan, then advances the turn in Qt and it plays.

### Phase 3 — MCP transport  *(web LLMs can POST)*
- `game/mcp/server.py`: FastMCP instance; register tools/resources that **call the
  same `game/agent/service` functions** (no logic duplication).
- Mount into `app.py` (`mcp.streamable_http_app()` at `/mcp` + lifespan running
  `mcp.session_manager.run()`).
- **Deliverable:** add the `/mcp` URL as a claude.ai custom connector and plan red
  from the web LLM (reads + writes).

### Phase 4 — Memory + adaptivity
- `stored_context` (new `Game` field + migrator backfill) and `human_notes`
  (Settings); `prev_turns` after-action history if not already retained
  ([`05`](05-context-and-persistence.md)).
- Feed last debrief + blue ATO (fog-filtered) into the context so red reacts to the
  player.
- **Deliverable:** red references prior turns and its own strategy notes.

### Phase 5 — Autonomous wiring + fallback (the "decent opponent" — completes the feature)
- When `settings.opfor_ai_enabled`, **suppress the engine's auto-planning of red**
  (leave the ATO for the AI to author via the API), and add the **fallback**: if
  red's turn is still empty when the human advances (AI didn't play / errored), run
  the scripted `TheaterCommander` so the turn is never empty ([`03`](03-opfor-planner.md)).
- **Deliverable:** with the setting on, red is planned entirely by the LLM via the
  API like a human player; with it off (or on failure) the scripted commander runs.

### Phase 6 — Polish
- Settings group (enable OPFOR-AI, AI-intel = mirror `map_coalition_visibility`).
- Status surface (what red planned / why) — reuse turn/finances panels.
- Tunnel/exposure docs for the web-LLM connector flow. (No map-edit/cheat tools —
  the API stays to player-legal actions; see the guiding principle in [`04`](04-api-reference.md).)

## Minimal server wiring (current FastMCP API, verified 2026-06)

```python
# game/server/app.py (additions)
import contextlib
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from game.mcp.server import mcp          # FastMCP instance, tools delegate to game/agent/service
from game.server.retributionai.routes import router as ai_router

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())   # REQUIRED for /mcp
        yield

app = FastAPI(lifespan=lifespan)
# ... existing include_router(...) calls ...
app.include_router(ai_router)                       # REST: /retribution-ai/*
app.mount("/mcp", mcp.streamable_http_app())        # MCP endpoint at /mcp
```

```python
# game/mcp/server.py
from mcp.server.fastmcp import FastMCP
from game.agent import service

mcp = FastMCP("DCS Retribution OPFOR AI", stateless_http=True, json_response=True)

@mcp.resource("retribution://turn_context/{side}")
def turn_context(side: str):
    return service.turn_context(side)               # SAME function the REST route calls

@mcp.tool()
def create_packages(side: str, packages: list[dict]) -> dict:
    return service.create_packages(side, packages)  # SAME function the REST POST calls
# ...rest of tools/resources, all delegating to service...
```

```python
# game/server/retributionai/routes.py  (the REST half — same backing)
from fastapi import APIRouter, Depends
from game.server.security import ApiKeyManager
from game.agent import service

router = APIRouter(prefix="/retribution-ai", dependencies=[Depends(ApiKeyManager.verify)])

@router.get("/turn_context")
def turn_context(side: str = "red"):
    return service.turn_context(side)

@router.post("/packages")
def create_packages(body: dict):
    return service.create_packages(body["side"], body["packages"])
```

> Pin the FastMCP API to the installed `mcp` version (lifespan/`Context`/
> `streamable_http_app` signatures shifted across minors). The above matches `mcp`
> 1.x. If mounting into the thread-started uvicorn fights you, run the MCP app on a
> sibling port in the same process — non-duplication still holds (shared service).

## Client setup (what the Settings panel tells the user)

- **Desktop agent (Claude Code):** "Paste this URL to your agent:
  `http://127.0.0.1:8322/retribution-ai/start?token=<KEY>`." The agent GETs it and
  follows the workflow. **No config files.** (Optionally also document
  `claude mcp add --transport http http://127.0.0.1:8322/mcp` for MCP-native use.)
- **Web LLM (claude.ai):** "Expose the port (tunnel) and add this as a custom
  connector: `https://<your-tunnel>/mcp`." The connector gives it read+write tools.

## Testing strategy

- **Live-game fixture:** build a `Game` in a test via `create_game` +
  `begin_turn_0` (as `qt_ui/main.py:283` does), point the service at it, assert
  `turn_context` shape and that `create_packages` yields a non-empty, valid red ATO.
- **Round-trip:** `create_packages` → assert packages reference valid
  targets/squadrons and flight plans build.
- **Fallback:** force the LLM hook to raise; assert the scripted commander still
  fills red ([`00`](00-vision-and-scope.md) guarantee).
- **Transport parity:** the same operation via REST and via MCP returns equal
  results (guards against logic drifting out of the service layer).
- **No-Qt purity:** `game/agent/*` importable without PySide6 (keeps the `dev` PR
  clean; the Qt-callback bits stay behind a thin interface).
- Keep `mypy` / `black` / `pre-commit` green.
