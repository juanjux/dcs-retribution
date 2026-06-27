# 07 — Branching, PR Strategy, Risks & Open Decisions

## Branch reality

- This work lives on **`experiment-mcp`**, cut from **`master`** (juanjux's fork —
  `origin` is `juanjux/dcs-retribution`; there is **no `upstream` remote** in this
  clone). Base commit: `7f063a0`.
- Repo branch roles (from the fork README):
  - **`dev`** — pristine mirror of upstream `dcs-retribution/dev`.
  - **`juanjux-dev`** — curated line; features land via PR after testing.
  - **`master`** — live "buffed" build, ahead of `juanjux-dev`, carries WIP. The
    desktop Claude Code builds the playable binary from here.
- **Eventual PR target for this feature: `dev`** (per juanjux). That makes it a
  *clean, upstream-shaped* contribution.

## The tension to design around

`experiment-mcp` is cut from `master`, which contains many fork-specific features
and WIP **not present in `dev`**. But the PR goes to `dev`. So the feature must be
**cleanly separable from everything master-only**, or the eventual `dev` PR will
drag in unrelated fork changes (or fail to apply).

### Rules to keep it separable

1. **New code in new modules.** Put ~all the feature in `game/agent/` and
   `game/mcp/` (new files). New files cherry-pick onto `dev` trivially.
2. **Minimise edits to existing files.** The unavoidable touch-points are:
   - `game/commander/theatercommander.py` — the OPFOR hook (keep it a small, well
     -guarded wrapper; see [`03`](03-opfor-planner.md)).
   - `game/settings/settings.py` — a few new feature flags.
   - `requirements.txt` — add `mcp[cli]<2`.
   Keep each edit small, self-contained, and **dependent only on code that also
   exists in `dev`**.
3. **Don't build on master-only APIs.** Before relying on a symbol, check it
   exists in `dev` (or vendor/guard it). The engine seams this feature uses
   (`Game.initialize_turn`, `TheaterCommander`, `PackageFulfiller`,
   `PurchaseAdapter`, `persistency`) are core and present upstream — good. But the
   fork's extra features (movable ships, OPFOR money cheat, air-wing cheat, EW,
   TIC, etc.) are master-only; if a map-edit/economy tool leans on one of those,
   **gate it** so the core feature still builds against `dev`.
4. **Keep the `mcp` dependency isolated** to `game/mcp/` so the gameplay half
   (`game/agent/` + the OPFOR hook) can be PR'd even if the MCP-server half is held
   back or split into a second PR.

### Suggested PR path

- Develop & soak-test on `experiment-mcp` (cut from `master`) so it runs in the
  real buffed binary the desktop builds.
- When proven, prepare the `dev` PR by cutting a clean branch from `dev` and
  applying **only** the feature's commits (the new modules + the small guarded
  edits). Because the feature is isolated, this should be a clean cherry-pick.
- Consider **splitting** into two PRs: (1) `game/agent/` + OPFOR engine hook
  (pure gameplay, no new deps), (2) `game/mcp/` + `mcp[cli]` dependency (the MCP
  server). PR (1) is the higher-value, lower-risk upstream contribution.

## Verification status of this design

- **First-hand verified** (read at `7f063a0`): game core/turn loop, persistence,
  the OPFOR commander/HTN seam, ATO/package creation, the FastAPI server seam,
  app bootstrap, economy/purchase adapters, theater/map model + coordinate
  conversion, coalition/air-wing read model, logging config, settings/cheat flags.
- **Verified current (web, 2026-06):** FastMCP API, transports, `mcp[cli]`
  packaging, v2-alpha timing.
- **NOT deeply verified — confirm at implementation time:**
  - **Debrief flow** (`game/debriefing.py`, `MissionResultsProcessor`): the exact
    shape of "what blue did last turn" intel. Known at a high level only.
  - **Exact log filenames** under `./logs/` — read `resources/default_logging.yaml`.
  - **`MissionTarget.mission_types`** lives in the theater classes (per target
    type); enumerate valid task/target pairs from there before building
    `plan_package` validation.
  - **Red auto-plan gating** vs. the LLM: confirm how `PackagePlanningTask`
    preconditions treat red (blue is gated by `AutoAtoBehavior.Disabled`) so the
    LLM and the scripted red planner don't clobber each other.

## Risks

| Risk | Mitigation |
|------|-----------|
| **Plan quality** — LLM produces incoherent/illegal red turns | Reuse fulfilment (can't produce invalid missions); scripted **fallback** always fills gaps; start at L2 (strategy-only) before L3 |
| **Threading** in live mode (Option C) — sim/Qt/server all touch `Game` | Plan only at turn boundaries / paused sim; lock around `initialize_turn`+ATO edits; start with headless Option A |
| **Process-global state** — multiple saves in one process corrupt namegen/caches | One `Game` per server process; subprocess to switch saves ([`05`](05-headless-bootstrap-and-saves.md)) |
| **Pickle trust** — loading a save executes class resolution | Only load trusted saves; document; stdio (no network) |
| **Latency/cost** of LLM planning each red turn (L3) | Cache the operational picture; cap intents; budget/token caps in settings; allow L2 (cheaper) |
| **`dev` PR drags in master-only code** | Isolation rules above; split PRs |
| **`mcp` v2 churn** | Pin `<2`; revisit after 2026-07-27 stable |
| **Save-compat** — feature adds fields to pickled objects | Prefer keeping new state in new modules / volatile + recomputed; if you must add persisted fields, follow the fork's save-compat conventions (`game/savecompat.py`, `Migrator`) |

## Open decisions for juanjux

These shape the build; the desktop session should ask if unclear:

1. **Priority: headless-on-saves (Option A) vs. live-game (Option C) first?**
   Recommendation: **A first** (simplest, testable), C in Phase 4.
2. **Default autonomy level** to ship behind the setting — L2 (strategy hook) is
   the recommended first "decent opponent"; L3 is the vision.
3. **Which LLM drives autonomous OPFOR (L3)?** For L0–L2-manual the *client*
   (Claude Code/Desktop) is the LLM — no API key needed. L3 (engine-driven, no
   human) needs an Anthropic API path + model choice + token budget.
4. **Give OPFOR a leg up by default?** `enemy_income_multiplier` lets red
   out-resource blue cheaply — useful to make the LLM opponent threatening without
   perfect play. On/off by default?
5. **Map-edit tools** — how much "place/change things on the map" power to expose,
   and behind which cheat flags.
6. **One PR or two** to `dev` (gameplay hook vs. MCP server)?
