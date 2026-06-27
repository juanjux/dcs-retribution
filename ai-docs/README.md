# `ai-docs/` — MCP feature design (branch `experiment-mcp`)

> **Status:** Design / planning only. **No production code has been written yet.**
> This directory is the complete hand-off package for implementing an **MCP
> (Model Context Protocol) server** for DCS Retribution.
>
> It was produced on branch `experiment-mcp` (cut from `master`) so that a second
> Claude Code session (running on juanjux's desktop) can pick up implementation
> with full context. Read the docs in order.

## What this feature is

An MCP server that lets an LLM agent (Claude, etc.) **read** the campaign state
(savegames, live game, logs, the map) and **plan turns** for either coalition —
but **especially OPFOR (red)**, so a human can play against a competent,
adaptive opponent instead of the current rule-based commander.

The scripted commander (`game/commander/`, an HTN planner) is rigid: it walks a
**fixed, hardcoded task-priority list every turn** with no awareness of the
strategic situation or the player's behaviour. The core idea of this feature is
to **replace (or augment) the commander's "brain" with an LLM**, while reusing
the engine's existing "hands" (package building, flight planning, procurement)
so we inherit all validation and mission generation for free.

## Read in this order

| # | Doc | What it covers |
|---|-----|----------------|
| 0 | [`00-vision-and-scope.md`](00-vision-and-scope.md) | The goal, the "decent OPFOR" thesis, scope, non-goals, autonomy levels |
| 1 | [`01-architecture.md`](01-architecture.md) | Architecture options + recommendation, the layered design, state/concurrency, transport, security |
| 2 | [`02-codebase-map.md`](02-codebase-map.md) | Annotated reference of every relevant subsystem, with `file:line` |
| 3 | [`03-opfor-planner.md`](03-opfor-planner.md) | **The centerpiece** — how the scripted commander works and exactly where/how to hook the LLM |
| 4 | [`04-mcp-tools.md`](04-mcp-tools.md) | Catalog of read + plan/write MCP tools & resources, with backing engine APIs |
| 5 | [`05-headless-bootstrap-and-saves.md`](05-headless-bootstrap-and-saves.md) | How to load a save headless, init sequence, the pickle save format, gotchas |
| 6 | [`06-implementation-plan.md`](06-implementation-plan.md) | Phased plan (MVP → full), file layout to add, deps, testing |
| 7 | [`07-branching-pr-and-risks.md`](07-branching-pr-and-risks.md) | Branch strategy (master → dev PR), what to isolate, risks, open decisions for juanjux |

## How this was researched

Every `file:line` reference in these docs was read first-hand or via a parallel
recon pass over the codebase at commit `7f063a0` (`master`, 2026-06-27). The
references are accurate as of that commit; if the desktop session is on a newer
`master`, re-grep the symbol names before relying on exact line numbers (the
**symbol names** are the stable contract, the line numbers are a convenience).

## TL;DR of the conclusions

- **The engine already supports the exact hook we need.** `Game.initialize_turn(
  events, for_red=True, for_blue=False)` (`game/game.py:398`) re-plans **only
  OPFOR** without touching the player's plan — its own docstring documents this
  case. The LLM plugs in at `TheaterCommander.plan_missions`
  (`game/commander/theatercommander.py:95`).
- **Reuse, don't rebuild.** Create packages/flights via
  `PackageFulfiller.plan_mission(...)` and procure via the `PurchaseAdapter`
  classes. These give us validation, flight-plan generation and budget handling
  for free.
- **Headless works.** A `Game` can be loaded from a save without Qt
  (`persistency.load_game` + `Migrator`), so an MCP can run standalone against
  save files. The live Qt game is reachable via the existing in-process FastAPI
  `GameContext`.
- **Recommended shape:** a thin **agent-core layer** (pure Python, operates on a
  `Game`) used by **both** a standalone stdio MCP server (for offline planning /
  development) **and** an in-process mount (for planning the live game). The
  scripted commander stays as a fallback/baseline so OPFOR turns are never empty.
