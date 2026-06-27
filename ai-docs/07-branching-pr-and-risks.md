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
   `GameContext`, `QtCallbacks`) are core/upstream — good. Fork-only features
   (movable ships, OPFOR money cheat, EW, TIC, kill-attribution detail for
   `prev_turns`) are master-only; if a tool leans on one, **gate it** so the core
   feature still builds against `dev`. Note: the "who killed it" detail in
   `prev_turns` depends on the fork's kill-attribution — degrade gracefully if absent.
4. **Isolate the `mcp` dependency** to `game/mcp/` + the mount, so the gameplay
   half can be PR'd even if the MCP transport is split out.

### Suggested PR path

- Develop & soak-test on `experiment-mcp` (from `master`) in the real binary.
- For the `dev` PR, cut a clean branch from `dev` and apply only the feature's
  commits (new modules + small guarded edits). Isolation makes this a clean
  cherry-pick.
- Consider **splitting** into two PRs: (1) service layer + REST + engine OPFOR hook
  (pure gameplay, the high-value contribution), (2) `game/mcp/` + `mcp[cli]`
  dependency (the MCP transport for web LLMs).

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
| **Plan quality** — incoherent/illegal red turns | Reuse fulfilment (can't emit invalid missions); scripted **fallback** fills gaps; start at L2 before L3 |
| **Exposure** — port forwarded for a web LLM is internet-reachable | Mandatory long **token** (URL + header); bind localhost by default; tunnel terminates TLS; document clearly |
| **Concurrency** — UI/sim/API touch one `Game` | Writes only at the planning boundary (sim paused); lock around `initialize_turn`+ATO; push `GameUpdateEvents` after |
| **Logic duplication** across REST/MCP | Single `game/agent/service.py`; transports are thin shims; parity test |
| **MCP mount/lifespan** quirks in the existing server | Verified pattern; sibling-port fallback; pin `mcp<2` |
| **Save-compat** — new persisted fields (`stored_context`, after-action) | Default + `Migrator`/`__setstate__` backfill; or sidecar JSON to avoid pickle change |
| **`dev` PR drags in master-only code** | Isolation rules above; gate fork-only features; split PRs |
| **Latency/cost** of LLM planning (L3) | Cache turn_context; cap actions; budget/token caps in settings; L2 is cheaper |

## Open decisions for juanjux

(The earlier "headless vs live" decision is **resolved: live-over-HTTP**.)

1. **Default autonomy level** behind the setting — **L2** (strategy hook; LLM sets
   priorities, HTN fulfils) is the recommended first "decent opponent"; **L3**
   (autonomous) is the vision. Ship L2 first?
2. **Which LLM drives autonomous OPFOR (L3)?** For L0–L2-manual the client is the
   LLM (no API key). L3 (engine-driven, no human) needs an Anthropic API path +
   model choice + token budget.
3. **`fog_of_war` default** — omniscient (easier, simpler) vs. limited-to-what-red-
   knows (fairer, harder to build). Recommend on, sourced from red's detection.
4. **Give OPFOR a leg up by default?** `enemy_income_multiplier` (`settings.py:125`)
   makes red threatening without perfect play. On/off?
5. **`stored_context` home** — in-`Game` field + migrator backfill (travels with the
   save; recommended) vs. sidecar JSON (no pickle change, but doesn't travel).
6. **Map-edit power** — how much of section F ([`04`](04-api-reference.md)) to
   expose, behind which cheat flags.
7. **One PR or two** to `dev` (gameplay+REST hook vs. MCP transport)?
8. **MCP mount** — into the existing FastAPI app (one port) vs. sibling port (same
   process). Recommend one app if the lifespan wires cleanly.
