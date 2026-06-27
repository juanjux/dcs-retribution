# 01 — Architecture

## The three integration options

The codebase gives us three distinct ways to wire an MCP server to the game.
They are not mutually exclusive — the recommendation is a layered design that
supports all of them behind one core.

### Option A — Standalone headless MCP (operates on save files)

A separate Python process runs an MCP server. On request it loads a `.retribution`
save into an in-memory `Game` (`persistency.load_game` + `Migrator`), exposes
read/plan tools, mutates the `Game`, and writes the save back.

- **Pros:** Simplest to build and test. No Qt, no live coupling. Perfectly
  scriptable. Ideal for development, CI, and batch "plan N saves" experiments.
- **Cons:** Operates on *files*, not the game the user is actively playing. The
  user would: save in Qt → run the agent → reload in Qt. Loading multiple saves
  in one long-lived process is unsafe (process-global state; see
  [`05-headless-bootstrap-and-saves.md`](05-headless-bootstrap-and-saves.md)).

### Option B — MCP talks to the running game over the existing FastAPI server

The Qt app already runs a FastAPI server **in-process on a background thread**
(`qt_ui/main.py:522` → `Server(...).run_in_thread()`), bound to the live `Game`
via `GameContext` (`game/server/dependencies.py:13`). An external MCP process
could be an HTTP client of that API.

- **Pros:** Drives the **live** game the user is playing.
- **Cons:** The existing API is a **read/render API for the web map** plus a
  thin Qt-callback bridge — it has very few write endpoints and is not designed
  for planning. We'd have to add a large write surface to it. Auth is a
  per-process random `X-API-Key` (`game/server/security.py`), and CORS is locked
  to `file://` (the Qt webview). Doable but indirect.

### Option C — MCP mounted in-process, sharing `GameContext`

Mount the MCP server inside the Qt process (as its own thread / ASGI sub-app),
reading the live `Game` directly through `GameContext.require()` — no HTTP
indirection, no second process holding a separate `Game`.

- **Pros:** Plans the **live** game with **direct object access** (full power of
  the Python API, not a REST subset). Reuses the existing server bootstrap.
- **Cons:** Must run inside the Qt process; requires care around threading
  (mutations vs. the sim thread and the Qt main thread — see *Concurrency*).

## Recommended design: one core, two front-ends

Build a thin **agent-core layer** that is pure Python and operates on a `Game`
object. Everything else is an adapter around it.

```
                ┌───────────────────────────────────────────────┐
                │  game/agent/   (NEW — pure Python, no Qt, no    │
                │  MCP/HTTP deps)                                 │
                │                                                 │
                │  • GameView      read-models (state → pydantic) │
                │  • GamePlanner   write/plan ops (wraps          │
                │                  PackageFulfiller, PurchaseAdapter, │
                │                  initialize_turn, theater edits) │
                │  • OpforBrain    LLM hook for TheaterCommander  │
                └───────────────▲───────────────▲────────────────┘
                                │               │
            ┌───────────────────┘               └─────────────────────┐
            │                                                          │
 ┌──────────┴───────────┐                              ┌──────────────┴───────────┐
 │ game/mcp/ (NEW)        │                              │ in-process mount (later)  │
 │ FastMCP server         │                              │ same FastMCP app started   │
 │ • stdio transport      │                              │ from qt_ui alongside the   │
 │ • loads saves (Opt A)  │                              │ existing Server, sharing   │
 │   OR connects to live  │                              │ GameContext (Opt C)        │
 └────────────────────────┘                             └────────────────────────────┘
```

**Why this layering wins:**

- The **agent-core** has no MCP/HTTP/Qt dependencies, so it is unit-testable and
  reusable. The OPFOR LLM hook lives here and is used by the engine's planning
  path *directly* — it does not require the MCP server to be running at all.
- The **MCP server** is a thin adapter: each tool is a few lines calling
  agent-core. Start with **Option A (stdio, save files)** as the MVP, then add
  **Option C (in-process, live game)** by pointing the same tools at
  `GameContext.require()` instead of a loaded save.
- This keeps the dependency on the `mcp` package **isolated to `game/mcp/`** —
  important for the eventual `dev` PR (see [`07`](07-branching-pr-and-risks.md)).

### Where the `Game` comes from (the one abstraction the core needs)

Give agent-core a single `GameSource` seam:

```python
# game/agent/source.py  (sketch)
class GameSource(Protocol):
    def get(self) -> Game: ...        # the live Game to read/plan
    def save(self) -> None: ...       # persist (autosave or to savepath)

class SaveFileSource:                 # Option A
    def __init__(self, path: str): ...  # load_game + Migrator on first get()
class GameContextSource:              # Option C
    def get(self) -> Game: return GameContext.require()
```

The MCP tools and `OpforBrain` only ever touch `GameSource`, so the same code
serves offline and live use.

## Transport & client registration

Use the official Python SDK's **FastMCP** (`from mcp.server.fastmcp import
FastMCP`). For a local desktop tool driven by Claude Code / Claude Desktop,
**stdio is the right default transport**: the client launches the server as a
subprocess, no ports, no auth to manage.

- **Claude Code:** a project `.mcp.json` (or `claude mcp add`) with a `command`
  that runs the server module in the repo's venv.
- **Claude Desktop:** an `mcpServers` entry in `claude_desktop_config.json`.

(Exact snippets in [`06-implementation-plan.md`](06-implementation-plan.md).)

For the **live in-process (Option C)** case, `streamable-http` mounted on a local
port is the alternative, because the server's lifetime is the Qt app's, not the
client's — the client connects to an already-running server rather than spawning
one. Keep the per-process `X-API-Key` pattern there.

> **SDK version caveat (as of 2026-06):** `mcp` **v2 is in alpha** (beta target
> 2026-06-30, stable 2026-07-27). Pin **`mcp[cli]<2`** for now unless the desktop
> session deliberately wants v2. Confirm the current version at implementation
> time.

## State & concurrency

- **Long-lived `Game` across tool calls.** In FastMCP, hold the `GameSource` (and
  for Option A the loaded `Game`) in the **lifespan context**, retrieved via
  `ctx.request_context.lifespan_context`. Do **not** reload the save per call.
- **One game per process (Option A).** Loading a save runs `Game.on_load()`,
  which mutates **process-global** state (`game.naming.namegen`,
  `ObjectiveDistanceCache`, theater globals — see
  [`05`](05-headless-bootstrap-and-saves.md)). Loading a second save in the same
  process clobbers the first. Policy: one `Game` per server process; to switch
  saves, restart or isolate in a subprocess.
- **Live game threading (Option C).** The Qt UI, the FastAPI server thread, and
  the sim (`GameLoopTimer` uses a real `threading.Timer`) can all touch the
  `Game`. Mutating tools must run when the sim is **paused/at a turn boundary**.
  Serialise planning mutations (a lock around `initialize_turn` / ATO edits) and
  prefer applying plans **at the turn-planning step**, not mid-sim. The ATO's
  transient `FlightState` is not pickled and is reset on load, so plan at turn
  boundaries to stay safe.
- **Events.** Every mutating turn/sim method takes a `GameUpdateEvents` instance
  (`game/sim/gameupdateevents.py`). Headless, create a throwaway one and ignore
  it. Live (Option C), push it onto `EventStream` so the web map UI refreshes
  (mirror what `pass_turn` does at `game/game.py:367`).

## Security

- **stdio (Option A):** no network surface; the client owns the subprocess. The
  main risk is that **loading a pickle save executes arbitrary class resolution**
  (`MigrationUnpickler.find_class`) — only load trusted saves. Document this.
- **http (Option C):** keep `X-API-Key` and bind to localhost only. Never widen
  CORS beyond what the map UI needs.
- Map/economy **cheats** (base capture, money) are gated behind `Settings` flags;
  expose them through the MCP only when the corresponding cheat setting is on, so
  the agent can't silently rewrite the game state the user didn't opt into.
