# 06 — Implementation Plan

A phased plan the desktop Claude Code can execute. Each phase is independently
useful and testable. Ship them in order.

## New code layout

Keep the MCP dependency isolated and the core reusable:

```
game/
  agent/                  # NEW — pure Python, no mcp/http/Qt deps
    __init__.py
    bootstrap.py          # headless setup()+load_game()+Migrator() (see 05)
    source.py             # GameSource: SaveFileSource | GameContextSource (see 01)
    views.py              # GameView → pydantic read-models (operational picture)
    planner.py            # GamePlanner → write/plan ops over PackageFulfiller/PurchaseAdapter
    opforbrain.py         # OpforBrain: LLM hook used by TheaterCommander (see 03)
    schemas.py            # pydantic: Intent/Action/Plan + read DTOs
  mcp/                    # NEW — the MCP adapter (isolated mcp[cli] dependency)
    __init__.py
    server.py             # FastMCP app: tools/resources wrapping game/agent
    __main__.py           # `python -m game.mcp` entrypoint (stdio)
tests/
  agent/                  # unit tests for views/planner/bootstrap against a fixture save
ai-docs/                  # this folder
```

Rationale: only `game/mcp/` imports `mcp`. `game/agent/` is plain Python and is
what the engine's OPFOR hook and the tests use — so the *gameplay* feature works
even if the MCP server isn't running, and the `dev` PR can be split cleanly
([`07`](07-branching-pr-and-risks.md)).

## Dependencies

Add to `requirements.txt` (pin for now — **v2 is in alpha as of 2026-06**, beta
2026-06-30, stable 2026-07-27):

```
mcp[cli]<2
```

The LLM client itself is **the MCP client** (Claude Code / Claude Desktop) — the
server does **not** call an LLM API for L0/L1/L2-manual. For the *autonomous*
OPFOR brain (L3) that runs inside the engine without a human in the loop, you'll
additionally need an Anthropic API path (`anthropic` SDK) invoked from
`opforbrain.py`; keep that behind a setting and out of the MCP package.

## Phases

### Phase 0 — Headless bootstrap + read-only core  *(foundation)*
- `game/agent/bootstrap.py` (the [`05`](05-headless-bootstrap-and-saves.md) sequence) + `source.py`.
- `game/agent/views.py`: `GameView.operational_picture()` and the per-area read DTOs.
- Test: load a fixture `.retribution` save headless, assert the picture matches.
- **Deliverable:** can load a real save outside Qt and dump a faithful state JSON.

### Phase 1 — Standalone MCP server (Option A), read tools only  *(L0 advisor)*
- `game/mcp/server.py` with FastMCP: session tools (B), read tools/resources (B–D),
  lifespan holding the `GameSource`.
- stdio transport; register in Claude Code / Desktop (snippets below).
- **Deliverable:** from Claude Code, "load save X and describe red's situation".

### Phase 2 — Write/plan tools (the executor)  *(L1 assisted apply)*
- `game/agent/planner.py`: `plan_package` (PackageFulfiller), buy/sell
  (PurchaseAdapter), stances, `schedule_all`, turn control (`initialize_turn`/
  `pass_turn`), `get_plan_diff`.
- Wire as MCP write tools (E–H). Structured errors at the boundary.
- **Deliverable:** from Claude Code, drive a full red turn against a save by hand,
  save it, load in Qt, verify it plays.

### Phase 3 — Strategy hook in the engine  *(L2 — first "decent opponent")*
- `game/agent/opforbrain.py` L2a: LLM-chosen method ordering/subset for
  `PlanNextAction`; integrate at `TheaterCommander.plan_missions` behind
  `settings.opfor_llm_*`.
- **Deliverable:** toggling the setting makes red concentrate/adapt; scripted
  fallback intact.

### Phase 4 — Autonomous OPFOR + live mount  *(L3 + Option C)*
- `OpforBrain.plan_missions` full intent loop + scripted gap-fill/fallback.
- Add `GameContextSource` + in-process mount of the FastMCP app from `qt_ui`
  alongside the existing `Server` (streamable-http, localhost, `X-API-Key`), so the
  agent plans the **live** game.
- Add player-intel context (last debrief + blue ATO) for adaptivity.
- **Deliverable:** play a campaign in Qt where red turns are planned by the LLM.

### Phase 5 — Polish
- A `Settings` group for the feature (enable, autonomy level, model, budget caps).
- A thin status surface (what red planned, why) — reuse the turn/finances panels.
- Map-edit tools (G) behind cheat flags.

## Client registration snippets

**Claude Code** — project `.mcp.json` (or `claude mcp add retribution -- <cmd>`):

```jsonc
{
  "mcpServers": {
    "retribution": {
      "command": "python",
      "args": ["-m", "game.mcp"],
      "cwd": "/path/to/dcs-retribution",      // run from repo root (see 05)
      "env": { "RETRIBUTION_SAVE": "/path/to/save.retribution" }  // optional default
    }
  }
}
```

Use the project venv's interpreter for `command` (e.g. the absolute path to
`.venv/Scripts/python.exe` on Windows). The server should read the save path from
an env var or a `load_savegame` tool call.

**Claude Desktop** — `claude_desktop_config.json` (`mcpServers` block, same shape):

```jsonc
{
  "mcpServers": {
    "retribution": {
      "command": "C:/path/to/dcs-retribution/.venv/Scripts/python.exe",
      "args": ["-m", "game.mcp"],
      "cwd": "C:/path/to/dcs-retribution"
    }
  }
}
```

## Minimal server skeleton (current FastMCP API, verified 2026-06)

```python
# game/mcp/server.py
from contextlib import asynccontextmanager
from dataclasses import dataclass
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

from game.agent.bootstrap import bootstrap_headless
from game.agent.source import SaveFileSource
from game.agent.views import GameView
from game.agent.schemas import OperationalPicture

@dataclass
class AppCtx:
    source: SaveFileSource

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppCtx]:
    bootstrap_headless()                       # logging, mods, persistency.setup, payloads
    yield AppCtx(source=SaveFileSource())      # holds the loaded Game across calls

mcp = FastMCP("DCS Retribution", lifespan=lifespan)

@mcp.tool()
def load_savegame(path: str, ctx: Context) -> str:
    ctx.request_context.lifespan_context.source.load(path)
    return f"loaded {path}"

@mcp.resource("retribution://state/operational/{side}")
def operational_picture(side: str) -> OperationalPicture:        # pydantic → structured output
    game = mcp.get_context().request_context.lifespan_context.source.get()
    return GameView(game, side).operational_picture()

# ...read tools (B–D), write tools (E–H)...

if __name__ == "__main__":
    mcp.run()        # stdio by default
```

```python
# game/mcp/__main__.py
from game.mcp.server import mcp
mcp.run()
```

> Note: pin the FastMCP API to the installed `mcp` version at implementation time
> (the lifespan/`Context` signatures shifted between minor releases). The shapes
> above match `mcp` 1.x.

## Testing strategy

- **Fixture save:** commit a small `.retribution` save under `tests/` (or generate
  one in a fixture via `create_game` + `begin_turn_0`) and assert read-model shape.
- **Round-trip:** load → `plan_opfor_turn` → `save_game` → reload → assert the red
  ATO is non-empty and references valid targets/squadrons.
- **Fallback:** force the LLM path to raise and assert the scripted commander still
  produces a red plan (the [`00`](00-vision-and-scope.md) guarantee).
- **No-Qt import test:** importing `game.agent.*` and `game.mcp.*` must not import
  PySide6 (guards headless purity and keeps the `dev` PR clean).
- Keep `mypy`/`black`/`pre-commit` green (the repo enforces them).
