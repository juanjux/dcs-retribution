# 04 — API Reference (REST + MCP, one backing each)

Every operation lives **once** in `game/agent/service.py` and is exposed two ways:

- **REST** under `/retribution-ai/*` — desktop agents `GET`/`POST` it (curl).
- **MCP** at `/mcp` — same operation as a tool (writes) or resource (reads), so a
  web LLM can use it via a custom connector.

All take the auth **token** (header `X-API-Key` or `?token=`). All return pydantic
models (JSON). Reads never mutate; writes only succeed at a turn/planning boundary
(see concurrency in [`01`](01-architecture.md)).

> **Guiding principle — the AI is a player, not a god.**
> The API exposes **exactly the actions a human player can take through the game**,
> through the **same endpoints**: plan packages/flights, buy/sell aircraft,
> buy/transfer ground units, set front-line stances, **move movable ships**,
> **adjust flight/package waypoint positions on the map**, run procurement, read
> state (incl. a rendered **map image**), keep notes. What's excluded is
> **cheats / god-mode**: no setting the budget, no capturing bases, no creating or
> teleporting units beyond the game's legal move limits, no editing a TGO's unit
> composition. Settings such as `enemy_income_multiplier` and
> `map_coalition_visibility` are normal campaign/player settings — the AI **reads**
> them via `/settings`, it doesn't change them. OPFOR plays by the same rules, and
> through the same endpoints, as the human.

> The endpoint names below follow juanjux's sketch. They're a starting catalog,
> not gospel — refine shapes during implementation. The **engine backing** column
> is the important, verified part.

## Recommended LLM workflow (returned by `/start`)

1. `GET /start` → this workflow + role/context (or `/howtoplay` for depth).
2. `GET /howtoplay` once per session → game concepts (wings, packages, roles,
   ground combat, buying/selling).
3. `GET /settings`, `GET /human_notes`, `GET /stored_context` → rules & memory.
4. `GET /turn_context` (+ `GET /prev_turns?n=1`) → the situation. Image-capable
   models can also pull `GET /map/image` for the visual picture.
5. `GET /packages` → check what's already planned (resume an interrupted turn).
6. Plan, then apply: `POST /packages`, economy/stance writes, and any map moves
   (`move_ship`, `set_waypoint_position`).
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
| **turn_context** — campaign, map, all OPFOR items (bases, wings, pilots, aircraft, ground units, units outside bases, buildings, SAMs, EWRs: position + alive/dead + health); OWNFOR detail limited per **`map_coalition_visibility`** (the real "Fog of war" map mode — see [`05`](05-context-and-persistence.md)) | `GET /turn_context` | resource `retribution://turn_context/{side}` | `theater.controlpoints`/`ground_objects`, `AirWing.iter_squadrons`, `Squadron.*`, `game.threat_zone_for`, `ObjectiveFinder.*`, coords via `leaflet` ([`02`](02-codebase-map.md)) |
| **prev_turns** — per prior turn: units lost (how / who killed them), bases captured, key events; `?n=K` for K turns ago (1 = last) | `GET /prev_turns?n=1` | tool `get_prev_turns(n)` | debrief history + `game.informations` + stats ([`05`](05-context-and-persistence.md)) |
| **packages** (read) — current packages/flights **incl. waypoints & TOTs** (to verify none / resume / inspect routes) | `GET /packages?side=red` | tool `get_packages(side)` | `coalition.ato.packages`, `Package.*`, `Flight.flight_plan.waypoints` (reuses existing `flights`/`waypoints` route shapes) |
| **flight waypoints** — ordered waypoints of one flight (lat/lng, type, alt, tot) | `GET /waypoints/{flight_id}` | tool `get_flight_waypoints(flight_id)` | existing `game/server/waypoints/routes.py:38` (`list_all_waypoints_for_flight`) |
| **map image** — rendered PNG of the campaign map (ownership, control points, front lines, threat/detection rings, ground objects, **package route lines**) — "what the player sees", for multimodal LLMs; optional `bbox`, `layers`, `side` | `GET /map/image?side=red&bbox=…` | tool `get_map_image(side, bbox?)` → **image** | see "Map image" below |

`turn_context` is the high-value text call; **map image** is its visual companion
for image-capable models. Build `turn_context` in `game/agent/views.py` as a
compact, faithful snapshot; limit OWNFOR detail per `map_coalition_visibility`
(see [`05`](05-context-and-persistence.md)).

### Map image (multimodal)

Returns a raster image of the strategic map — the same picture the player reads on
the web map (control-point ownership, front lines, threat/detection rings, ground
objects, and **package/flight route lines**) — for LLMs that reason better over
images. Respects fog of war: rendered **from the requested side's perspective**
(`map_coalition_visibility`), so the red AI sees red's picture + detected blue.

- **MCP:** return an image (`mcp.server.fastmcp.Image` / image content). **REST:**
  respond `image/png`.
- **Recommended backing — server-side render (headless, flexible).** The server
  already produces every map layer as lat/lng geometry for the web map
  (control points, `frontlines`, `threatzones`, `tgos`, supply routes, and package
  route lines from flight waypoints — see `game/server/*/routes.py` and
  `game/server/leaflet.py`). Draw those layers to a PNG with Pillow/shapely using
  the terrain's planar x/y (positions are already meters; scale to pixels). This
  supports `bbox` subsets and `layers` selection and needs no Qt.
- **Alternative — grab the live map** for pixel-exact fidelity: capture the Qt
  `QWebEngineView` via the `QtCallbacks` bridge (`QtContext`,
  `game/server/dependencies.py:35`). Exactly what the player sees, but Qt-main-
  thread, whole-view only (no easy `bbox`), and needs the UI running.

Recommend the server-side renderer as primary; offer the Qt grab as an optional
"exact screenshot" mode.

## C. Write — plan OPFOR (missions, economy, transfers)

| Op | REST | MCP | Service → engine |
|----|------|-----|------------------|
| **create packages/flights** | `POST /packages` | tool `create_packages(specs)` | explicit flights → `Package` + `Flight(squadron, count, task, start_type)` + payload + `recreate_flight_plan` + `ato.add_package`; auto-select/auto-escort path → `PackageFulfiller.plan_mission(ProposedMission)`; then `MissionScheduler.schedule_missions` ([`02`](02-codebase-map.md)). Body schema below. |
| **delete a package** | `DELETE /packages/{id}` | tool `delete_package(id)` | `ato.remove_package` (returns its pilots + aircraft to inventory) |
| **delete a flight** | `DELETE /packages/{pkg_id}/flights/{flight_id}` | tool `delete_flight(pkg_id, flight_id)` | `Package.remove_flight` (`package.py:137`, returns pilots + aircraft) |
| **clear all OPFOR packages** (start the turn fresh / drop a half-done plan) | `DELETE /packages?side=red` | tool `clear_packages(side)` | `coalition.ato.clear()` (`airtaaskingorder.py:36`) |
| **set front-line stance** | `POST /stances` | tool `set_stance(front, value)` | `CombatStance` on `FrontLine` |
| **buy aircraft** | `POST /buy/aircraft` | tool `buy_aircraft(base, squadron, n)` | `AircraftPurchaseAdapter(cp).buy` |
| **sell aircraft** | `POST /sell/aircraft` | tool `sell_aircraft(base, squadron, n)` | `AircraftPurchaseAdapter(cp).sell` (sells *untasked* airframes; refunds budget) |
| **buy ground units** | `POST /buy/ground` | tool `buy_ground(base, unit, n)` | `GroundUnitPurchaseAdapter(cp, coalition, game).buy` |
| **cancel a pending ground order** | `POST /buy/ground/cancel` | tool `cancel_ground_order(base, unit, n)` | `GroundUnitPurchaseAdapter(...).sell` — cancels a not-yet-delivered order (ground units can't be *sold* once delivered) |
| **run auto-procurement** (spend the rest) | `POST /buy/auto` | tool `auto_procure()` | `Coalition.plan_procurement` |
| **transfer ground units between bases** | `POST /transfers` | tool `create_transfer(origin, dest, units)` | `coalition.transfers.new_transfer(TransferOrder(origin, dest, {unit: n}), now)` (`game/transfers.py:94`, `:651`) |
| **list pending transfers** | `GET /transfers?side=red` | tool `get_transfers(side)` | iterate `coalition.transfers` (`PendingTransfers`, `game/transfers.py:590`) |
| **cancel a transfer** | `DELETE /transfers/{id}` | tool `cancel_transfer(id)` | `coalition.transfers.cancel_transfer(t)` (`game/transfers.py:718`) |

### `POST /packages` body

A **package = a target + a list of flights** (+ optional package TOT). Escort/SEAD
are **just flights** in the package with that task — there is no package-level
"escort" field. Targets/squadrons are referenced by **name/id from
`turn_context`** (never raw coords).

```jsonc
{
  "side": "red",
  "packages": [
    {
      "target": "SAM Armadillo",        // resolved from turn_context
      "tot": "asap",                     // "asap" | ISO datetime | omit → MissionScheduler spaces it
      "flights": [
        {
          "task": "DEAD",                // FlightType
          "squadron": "16th OVAP",       // origin squadron — fixes BOTH airframe and base/wing
          "count": 2,
          "start_type": "COLD",          // COLD | WARM | RUNWAY | IN_FLIGHT (default: settings.default_start_type)
          "payload": "DEAD standoff",    // optional named loadout; omit → Loadout.default_for(flight)
          "waypoints": null              // optional; null/omit → engine auto-builds a valid flight plan (recommended)
        },
        {
          "task": "SEAD",                // the escort is its own flight in the same package
          "squadron": "3rd Fighter Sqn",
          "count": 2,
          "start_type": "COLD"
        }
      ]
    }
  ]
}
```

**Per-flight fields → engine:**

| Field | Meaning / engine mapping |
|-------|--------------------------|
| `task` | `FlightType` (`game/ato/flighttype.py`). Must be valid for the target (`MissionTarget.mission_types`). |
| `squadron` | The origin **squadron** — this is what fixes the **aircraft type** *and* the **origin base/wing** (`Squadron.aircraft`, `Squadron.location`). Resolve from `get_air_wing` / `turn_context`. |
| `aircraft` + `base` *(alt.)* | If you'd rather not name a squadron: give airframe + base and the service resolves the matching squadron; or omit both and it auto-picks via `AirWing.best_squadron_for`. **One of `squadron` or `aircraft`+`base` is required** (or omit all for auto). |
| `count` | aircraft in the flight (claims `untasked_aircraft` from the squadron; fails if insufficient). |
| `start_type` | `StartType` enum. |
| `payload` | a **named loadout** for the airframe/task, applied to the flight's members (uniform by default — `use_same_loadout_for_all_members`). Omit → `Loadout.default_for(flight)`. Valid names: `Loadout.default_loadout_names_for(task)` (`game/ato/loadouts.py:273`). |
| `waypoints` | **Optional. Recommended: omit.** The engine builds a doctrine/navmesh/threat-aware flight plan automatically (`recreate_flight_plan`). Provide a waypoint list only to *override*, which switches the flight to a custom plan (`flight.degrade_to_custom_flight_plan`, `game/ato/flight.py:161`). Hand-authored routes bypass the auto threat-avoidance — use sparingly. |

**How the service builds it (per package):** create `Package(target, game.db.flights)`
→ for each flight resolve the squadron, `Flight(package, squadron, count, task,
start_type)`, set payload if given, `pkg.add_flight(flight)` → build **all** flights
first, then `recreate_flight_plan()` each (formation packages share waypoints) →
`pkg.set_tot_asap(now)` or honour `tot` → `coalition.ato.add_package(pkg)` →
`MissionScheduler.schedule_missions(now)`. (See the recipe + gotchas in
[`02`](02-codebase-map.md).)

Returns a **per-package / per-flight result** (created, or why it failed —
unknown squadron, insufficient aircraft, task/target mismatch, no route). A bad
flight fails *itself* only; the rest still apply.

> To author flights the LLM needs the inventory: `get_air_wing(side)` /
> `turn_context` list squadrons (airframe, base, untasked count, ready pilots), and
> an optional `GET /payloads?aircraft=…&task=…` (→ `default_loadout_names_for`)
> lists valid payload names.

**Selling & transfers — semantics (all player-legal):**
- **Aircraft** can be bought *and sold* (only *untasked* airframes can be sold;
  selling refunds the price). `AircraftPurchaseAdapter` handles budget + parking.
- **Ground units cannot be sold** once delivered (`GroundUnitPurchaseAdapter.do_sale`
  raises). The only ways to undo ground spending are **cancel a pending order**
  before delivery, or **transfer** delivered units to another base.
- **Transfers** move *your own* ground units between *your own* bases along the
  supply network (`TransferOrder(origin, destination, {unit: n})`). This is the
  normal player transfer action — **not** the transfer *cheat* (`enable_transfer_cheat`),
  which the AI does not use.

## D. Memory — the scratchpad

| Op | REST | MCP | Service → engine |
|----|------|-----|------------------|
| **stored_context** read | `GET /stored_context` | resource `retribution://stored_context` | persisted with the campaign ([`05`](05-context-and-persistence.md)) |
| **stored_context** write/append | `PUT /stored_context` (replace) / `POST /stored_context` (append) | tool `set_stored_context` / `append_stored_context` | same store |
| **stored_context** delete one key | `DELETE /stored_context/{key}` | tool `delete_stored_context(key)` | pop the key from the store |
| **stored_context** clear all | `DELETE /stored_context` | tool `clear_stored_context()` | reset the store |

A freeform key/value or markdown blob the AI owns: multi-turn strategy, lessons
learned this campaign, observations about the player. Persists across turns and
across different AIs/sessions because it lives in the save. The AI fully owns it,
so it can prune/replace its own notes via the deletes above.

## E. UI / session

| Op | REST | MCP | Service → engine |
|----|------|-----|------------------|
| **show_planning_dialog** — modal "AI is planning OPFOR…" | `POST /show_planning_dialog` `{state: start\|done}` | tool `show_planning_dialog(state)` | `QtContext`/`QtCallbacks` bridge (`game/server/dependencies.py:35`) — add a callback like the existing ones |
| **trigger OPFOR replan** (optional; usually the human advances the turn in Qt) | `POST /plan_opfor` | tool `plan_opfor()` | `Game.initialize_turn(events, for_red=True, for_blue=False)` (`game/game.py:398`) |

> Advancing the campaign turn stays a **human** action in the Qt UI. The API lets
> the LLM *fill red's plan*; the player clicks "next turn". `plan_opfor` is only
> for "(re)generate red from scratch", e.g. to clear a half-done turn.

## F. Spatial actions — move ships & adjust waypoints (player-legal)

These are normal player map actions in the fork, and **already exist as server
endpoints the human's web map uses** — the AI reuses the same ones.

| Op | REST | MCP | Service → engine |
|----|------|-----|------------------|
| **move a ship / naval group** | `PUT /tgos/{tgo_id}/destination` | tool `move_ship(tgo_id, lat, lng)` | existing `set_tgo_destination` (`game/server/tgos/routes.py`) → sets `tgo.target_position` — an **end-of-turn** reposition; checks `destination_in_range`/`max_move_distance` and not-over-land |
| **check a ship move is legal** | `GET /tgos/{tgo_id}/destination-in-range?lat=&lng=` | tool `ship_move_in_range(tgo_id, lat, lng)` | `ShipGroundObject.destination_in_range` (tgos route) |
| **clear a ship's pending move** | `DELETE /tgos/{tgo_id}/destination` | tool `clear_ship_move(tgo_id)` | existing clear route (`tgo.target_position = None`) |
| **adjust a flight/package waypoint** | `POST /waypoints/{flight_id}/{idx}/position` | tool `set_waypoint_position(flight_id, idx, lat, lng)` | existing `set_waypoint_position` (`game/server/waypoints/routes.py:49`) — moves the waypoint; if it's the **primary flight's** join/ingress/split/refuel, **propagates to the whole package** (`update_package_waypoints_if_primary_flight`) |

Notes:
- **Which ships are movable:** `TgoJs.moveable` (`game/server/tgos/models.py`); only
  non-carrier naval groups, within `max_move_distance`. Ship moves take effect at
  **end of turn** (it's a `target_position`, not a teleport).
- **Waypoint edits are immediate** and re-time the flight (`update_tot`). Editing the
  package's shared waypoints = editing the **primary flight's** join/ingress/split/
  refuel waypoint, which the endpoint cascades to the package and sibling flights.
- *Movable ships* is currently a **fork feature** (the human can do it; juanjux is
  upstreaming it). For the `dev` PR, gate this op gracefully if the target branch
  lacks it ([`07`](07-branching-pr-and-risks.md)).

## G. Out of scope: cheats

No **cheat / god-mode** surface (per the guiding principle): the AI cannot set the
budget, capture bases, create/teleport units beyond the legal move limits, or edit
a TGO's unit composition. Moving movable ships and dragging waypoints are **not**
cheats — they're player actions and live in sections C/F above.

## Error handling

Engine planning raises `PlanningError` / `NavMeshError` /
`InvalidObjectiveLocation`; purchases raise `TransactionError`. Catch at the
service boundary and return a **structured error** (code + message + which item),
so the LLM can adjust and retry a *different* action — never a stack trace, never
abort the whole turn.

## Resources vs. tools (MCP side)

- Side-effect-free reads (`start`, `howtoplay`, `settings`, `human_notes`,
  `turn_context`, `stored_context` read, flight waypoints) → **resources**
  (cacheable context). The **map image** is best a **tool** returning an image
  (`mcp.server.fastmcp.Image`), since it's parameterised (`side`/`bbox`/`layers`).
- Everything that mutates — creates, writes, **and deletes** (packages/flights,
  clear-ATO, buys, stances, transfers, **ship moves**, **waypoint moves**,
  stored_context write/delete, show_planning_dialog, plan_opfor) → **tools**. MCP
  has no HTTP verbs, so a REST `DELETE`/`PUT` maps to a `delete_*`/`clear_*`/`set_*`
  tool. All mutations obey the same turn/planning-boundary rule.
- Consider an MCP **prompt** "Plan OPFOR's turn" that bundles the workflow, so the
  user can one-shot it from the client.
