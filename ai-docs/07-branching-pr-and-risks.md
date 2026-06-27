# 07 — Branching, PR Strategy, Risks & Open Decisions

## Branch reality

- This work lives on **`experiment-mcp`**, cut from **`master`** (juanjux's fork —
  `origin` is `juanjux/dcs-retribution`; there is **no `upstream` remote** in this
  clone). Base commit: `7f063a0`.
- Repo branch roles (from the fork README):
  - **`dev`** — pristine mirror of upstream `dcs-retribution/dev`.
  - **`juanjux-dev`** — curated line; features land via PR after testing.
  - **`master`** — live "buffed" build, ahead of `juanjux-dev`, carries WIP; the
    desktop Claude Code builds the playable binary from here.
- **Eventual PR target for this feature: `dev`** (per juanjux) — a clean,
  upstream-shaped contribution.

## The tension to design around

`experiment-mcp` is cut from `master`, which contains fork-specific features and
WIP **not present in `dev`**. But the PR goes to `dev`. So the feature must be
**cleanly separable from everything master-only**.

### Rules to keep it separable

1. **New code in new modules:** `game/agent/`, `game/server/retributionai/`,
   `game/mcp/`. New files cherry-pick onto `dev` trivially.
2. **Minimise edits to existing files.** Unavoidable touch-points:
   - `game/server/app.py` — add lifespan + REST router + `/mcp` mount.
   - `game/server/security.py` — accept `?token=`.
   - `game/commander/theatercommander.py` — the OPFOR hook (small, guarded wrapper).
   - `game/settings/settings.py` — feature flags + `human_notes`.
   - `game/game.py` / `game/migrator.py` — `stored_context` (+ after-action) field
     with a backfill.
   - `requirements.txt` — `mcp[cli]<2`.
   Keep each edit small and dependent only on code that **also exists in `dev`**.
3. **Don't build on master-only APIs.** The engine seams used (`initialize_turn`,
   `TheaterCommander`, `PackageFulfiller`, `PurchaseAdapter`, the FastAPI server,
   `GameContext`, `QtCallbacks`, the `waypoints` set-position route) are
   core/upstream — good. Fork-only dependencies to **degrade gracefully** on `dev`
   rather than hard-depend:
   - **kill-attribution** detail used by `prev_turns` ("who killed it");
   - **movable ships** (the `tgos` `target_position`/`moveable` reposition) — juanjux
     is upstreaming it; if the target branch lacks it, hide/no-op the `move_ship`
     op rather than break the build;
   - the **air-wing cheat** (`enable_air_wing_adjustments`, fork PR #41): the
     *mid-campaign* squadron create/delete gate depends on it. Turn-0 air-wing
     config (create/delete via `AirWingConfigurationDialog`) is upstream and fine;
     guard the cheat-flag reference so it no-ops where the flag is absent.
4. **Isolate the `mcp` dependency** to `game/mcp/` + the mount, so it's a small,
   self-contained part of the single PR.

### Suggested PR path (one PR — decided)

- Develop & soak-test on `experiment-mcp` (from `master`) in the real binary.
- For the `dev` PR, cut a clean branch from `dev` and apply the feature's commits
  (new modules + small guarded edits). Isolation makes this a clean cherry-pick.
- **One PR** containing service layer + REST + MCP transport + the engine OPFOR
  hook. (The isolation rules keep it reviewable; no need to split.)

## Verification status of this design

- **First-hand verified** (`7f063a0`): game core/turn loop, the OPFOR commander/HTN
  seam, ATO/package creation, the FastAPI server + `GameContext` + `QtCallbacks`,
  economy/purchase adapters, theater/map model + coordinate conversion,
  coalition/air-wing read model, logging, settings/cheat flags, persistence.
- **Verified current (web, 2026-06):** FastMCP API, mounting into FastAPI
  (`streamable_http_app()` + `session_manager.run()` lifespan), `mcp[cli]`
  packaging, v2-alpha timing.
- **NOT deeply verified — confirm at implementation time:**
  - **Debrief shape** (`game/debriefing.py`, `MissionResultsProcessor`): exact
    stored structure for `prev_turns` (losses, kill attribution, captures).
  - **`MissionTarget.mission_types`** (per theater target class) — enumerate valid
    task/target pairs from there for `create_packages` validation.
  - **Red auto-plan gating** vs. the LLM (so the scripted red planner and the LLM
    don't clobber each other; blue is gated by `AutoAtoBehavior.Disabled`).
  - **Mounting MCP into the thread-started uvicorn** — confirm the lifespan runs;
    sibling-port fallback if not.

## Risks

| Risk | Mitigation |
|------|-----------|
| **Plan quality** — incoherent/illegal red turns | Reuse fulfilment (can't emit invalid missions); scripted **fallback** if red's turn is empty; rich context + memory so the LLM plans well |
| **Exposure** — port forwarded for a web LLM is internet-reachable | Mandatory long **token** (URL + header); bind localhost by default; tunnel terminates TLS; document clearly |
| **Concurrency** — UI/sim/API touch one `Game` | Writes only at the planning boundary (sim paused); lock around `initialize_turn`+ATO; push `GameUpdateEvents` after |
| **Logic duplication** across REST/MCP | Single `game/agent/service.py`; transports are thin shims; parity test |
| **MCP mount/lifespan** quirks in the existing server | Verified pattern; sibling-port fallback; pin `mcp<2` |
| **Save-compat** — new persisted fields (`stored_context`, after-action) | Default + `Migrator`/`__setstate__` backfill |
| **`dev` PR drags in master-only code** | Isolation rules above; degrade gracefully on the kill-attribution dependency |
| **Latency/cost** of LLM planning | Mode A: the client (the user's own agent) bears it. Mode B (engine-driven): cache turn_context, cap actions, token/budget caps in settings |

## Decisions already made (juanjux)

- **Mode:** live-over-HTTP (no headless / save-file mode).
- **API scope:** only player-legal actions, through the same endpoints — incl.
  buy/sell aircraft, buy/transfer ground units, **moving movable ships**, and
  **dragging flight/package waypoints**; plus a rendered **map image** for
  multimodal models. **No cheats** (budget/base-capture/unit-placement). The AI
  reads settings (`map_coalition_visibility`, `enemy_income_multiplier`, …) but
  never changes them; those are normal per-campaign, player-alterable settings.
- **AI intel:** driven by the existing `map_coalition_visibility` (the "Fog of war"
  map mode) — mirror the player's setting; don't invent a flag. See [`05`](05-context-and-persistence.md).
- **Air wings:** at **turn 0** the AI configures OPFOR's air wings like the player
  (create/delete squadrons, initial size). Mid-campaign it may create/delete
  squadrons **only when `enable_air_wing_adjustments`** (the air-wing cheat) is on,
  and fills them by **buying** — never the free aircraft +/-. It cannot change the
  faction's allowed airframes (asks the human). See [`04`](04-api-reference.md) §G.
- **`stored_context`:** stored **in the save** (new `Game` field + migrator backfill).
- **Autonomy:** **full autonomy only — no intermediate "strategy hook" level.** The
  AI plans the whole red turn like a human player. **Mode A (client-driven)** ships
  first: when OPFOR-AI is on, the engine doesn't auto-plan red — the chat LLM fills
  red via the API; the scripted commander is **fallback** if red's turn is empty.
  **Mode B (engine-driven, embedded LLM)** is a later optional add-on. See [`03`](03-opfor-planner.md).
- **Turn trigger (v1):** the **human says "your turn" in chat**; the `/howtoplay`
  briefing makes the LLM teach the player this on first contact (incl. the first
  turn). OPFOR plans **first**, then the human reviews. Long-poll / eventstream
  `new_turn` push remain documented as future upgrades. See [`04`](04-api-reference.md) §E.
- **PR:** **one** PR to `dev`.

## Open decisions for juanjux

1. **Which LLM drives engine-driven OPFOR (Mode B)?** Mode A (v1) needs no key —
   the chat client is the LLM. Mode B (engine calls an embedded LLM, hands-off)
   needs an Anthropic API path + model choice + token/budget caps. (Only relevant
   when you build Mode B.)
2. **MCP mount** — into the existing FastAPI app (one port) vs. sibling port (same
   process). Recommend one app if the lifespan wires cleanly.

*(The turn-trigger mechanism is resolved for v1 — human says "your turn"; see
Decisions above. Long-poll / eventstream push are future upgrades, not blockers.)*
