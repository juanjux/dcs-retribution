# 04 — API Reference (REST + MCP, one backing each)

Every operation lives **once** in `game/agent/service.py` and is exposed two ways:

- **REST** under `/retribution-ai/*` — desktop agents `GET`/`POST` it (curl).
- **MCP** at `/mcp` — same operation as a tool (writes) or resource (reads), so a
  web LLM can use it via a custom connector.

All take the auth **token** (header `X-API-Key` or `?token=`). All return pydantic
models (JSON). Reads never mutate; writes only succeed at a turn/planning boundary
(see concurrency in [`01`](01-architecture.md)).

> The endpoint names below follow juanjux's sketch. They're a starting catalog,
> not gospel — refine shapes during implementation. The **engine backing** column
> is the important, verified part.

## Recommended LLM workflow (returned by `/start`)

1. `GET /start` → this workflow + role/context (or `/howtoplay` for depth).
2. `GET /howtoplay` once per session → game concepts (wings, packages, roles,
   ground combat, buying/selling).
3. `GET /settings`, `GET /human_notes`, `GET /stored_context` → rules & memory.
4. `GET /turn_context` (+ `GET /prev_turns?n=1`) → the situation.
5. `GET /packages` → check what's already planned (resume an interrupted turn).
6. Plan, then `POST /packages` (and economy/stance writes) to apply.
7. `PUT /stored_context` → persist notes/strategy for next turn.
8. `POST /show_planning_dialog` (start) / done.

## A. Bootstrap & meta

| Op | REST | MCP | Service → engine |
|----|------|-----|------------------|
| **start** — role, context, API list, workflow | `GET /start` | resource `retribution://start` (and/or a `prompt`) | static + `service.bootstrap_doc()` |
| **howtoplay** — game concepts (once/session) | `GET /howtoplay` | resource `retribution://howtoplay` | static doc (markdown) |
| **settings** — current settings + each explained | `GET /settings` | resource `retribution://settings` | `Settings` (`game/settings/settings.py:93`) + descriptions |
| **human_notes** — player's freeform rules/notes | `GET /human_notes` | resource `retribution://human_notes` | stored in `Settings`/save ([`05`](05-context-and-persistence.md)) |

## B. Read — situation (the "operational picture")

| Op | REST | MCP | Service → engine |
|----|------|-----|------------------|
| **turn_context** — campaign, map, all OPFOR items (bases, wings, pilots, aircraft, ground units, units outside bases, buildings, SAMs, EWRs: position + alive/dead + health); OWNFOR items subject to **fog_of_war** | `GET /turn_context` | resource `retribution://turn_context/{side}` | `theater.controlpoints`/`ground_objects`, `AirWing.iter_squadrons`, `Squadron.*`, `game.threat_zone_for`, `ObjectiveFinder.*`, coords via `leaflet` ([`02`](02-codebase-map.md)) |
| **prev_turns** — per prior turn: units lost (how / who killed them), bases captured, key events; `?n=K` for K turns ago (1 = last) | `GET /prev_turns?n=1` | tool `get_prev_turns(n)` | debrief history + `game.informations` + stats ([`05`](05-context-and-persistence.md)) |
| **packages** (read) — current OPFOR packages/flights (to verify none / resume) | `GET /packages?side=red` | tool `get_packages(side)` | `coalition.ato.packages`, `Package.*`, `Flight.flight_plan` |

`turn_context` is the high-value call. Build it in `game/agent/views.py` as a
compact, faithful snapshot; respect `fog_of_war` by filtering OWNFOR detail.

## C. Write — plan OPFOR

| Op | REST | MCP | Service → engine |
|----|------|-----|------------------|
| **create packages/flights** | `POST /packages` | tool `create_packages(specs)` | `PackageFulfiller.plan_mission(ProposedMission(...))` → `coalition.ato.add_package`; then `MissionScheduler.schedule_missions` ([`02`](02-codebase-map.md)) |
| **remove package/flight** | `DELETE /packages/{id}` | tool `remove_package(id)` | `ato.remove_package` / `Package.remove_flight` |
| **set front-line stance** | `POST /stances` | tool `set_stance(front, value)` | `CombatStance` on `FrontLine` |
| **buy aircraft** | `POST /buy/aircraft` | tool `buy_aircraft(base, squadron, n)` | `AircraftPurchaseAdapter(cp).buy` |
| **buy ground units** | `POST /buy/ground` | tool `buy_ground(base, unit, n)` | `GroundUnitPurchaseAdapter(cp, coalition, game).buy` |
| **run auto-procurement** (spend the rest) | `POST /buy/auto` | tool `auto_procure()` | `Coalition.plan_procurement` |

`POST /packages` body — intent-shaped, target by **name/id from turn_context**
(never raw coords):

```jsonc
{
  "side": "red",
  "packages": [
    {"task": "DEAD",   "target": "SAM Armadillo", "size": 4, "escort": "ESCORT"},
    {"task": "STRIKE", "target": "Krymsk runway", "size": 4, "escort": "SEAD"}
  ]
}
```

The service resolves names→engine objects, calls `plan_mission`, and returns a
**per-item result** (created / why it failed). A bad item fails *itself* only.

## D. Memory — the scratchpad

| Op | REST | MCP | Service → engine |
|----|------|-----|------------------|
| **stored_context** read | `GET /stored_context` | resource `retribution://stored_context` | persisted with the campaign ([`05`](05-context-and-persistence.md)) |
| **stored_context** write/append | `PUT /stored_context` (replace) / `POST /stored_context` (append) | tool `set_stored_context` / `append_stored_context` | same store |

A freeform key/value or markdown blob the AI owns: multi-turn strategy, lessons
learned this campaign, observations about the player. Persists across turns and
across different AIs/sessions because it lives in the save.

## E. UI / session

| Op | REST | MCP | Service → engine |
|----|------|-----|------------------|
| **show_planning_dialog** — modal "AI is planning OPFOR…" | `POST /show_planning_dialog` `{state: start\|done}` | tool `show_planning_dialog(state)` | `QtContext`/`QtCallbacks` bridge (`game/server/dependencies.py:35`) — add a callback like the existing ones |
| **trigger OPFOR replan** (optional; usually the human advances the turn in Qt) | `POST /plan_opfor` | tool `plan_opfor()` | `Game.initialize_turn(events, for_red=True, for_blue=False)` (`game/game.py:398`) |

> Advancing the campaign turn stays a **human** action in the Qt UI. The API lets
> the LLM *fill red's plan*; the player clicks "next turn". `plan_opfor` is only
> for "(re)generate red from scratch", e.g. to clear a half-done turn.

## F. Map edits ("place/change things") — optional, cheat-gated

Accept **lat/lng**, convert to internal `Point` (`leaflet.py:66`); gate on the
matching `Settings` cheat flag; trigger `initialize_turn` + `compute_threat_zones`
after ownership/unit changes (mirrors the cheat-capture flow at `game.py:398`).

| Op | REST | MCP | Gate |
|----|------|-----|------|
| move ship group | `POST /map/move_ship` | `move_ship(tgo_id, lat, lng)` | movable-ships (fork feature) |
| set base owner | `POST /map/capture` | `set_owner(cp, side)` | `enable_base_capture_cheat` |
| repair/edit ground object | `POST /map/ground_object` | `edit_ground_object(...)` | follow buy/sell-TGO replan rules |

## Error handling

Engine planning raises `PlanningError` / `NavMeshError` /
`InvalidObjectiveLocation`; purchases raise `TransactionError`. Catch at the
service boundary and return a **structured error** (code + message + which item),
so the LLM can adjust and retry a *different* action — never a stack trace, never
abort the whole turn.

## Resources vs. tools (MCP side)

- Side-effect-free reads (`start`, `howtoplay`, `settings`, `human_notes`,
  `turn_context`, `stored_context` read) → **resources** (cacheable context).
- Everything that mutates (packages, buys, stances, stored_context write,
  show_planning_dialog, plan_opfor, map edits) → **tools**.
- Consider an MCP **prompt** "Plan OPFOR's turn" that bundles the workflow, so the
  user can one-shot it from the client.
