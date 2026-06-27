# 02 — Codebase Map (subsystem reference)

Annotated reference of every subsystem the MCP feature touches. Line numbers are
as of `master` @ `7f063a0`; treat **symbol names as the contract**.

---

## Game core & turn loop — `game/game.py`, `game/coalition.py`, `game/sim/`

`Game` (`game/game.py:95`) is the central in-memory campaign state: theater, both
coalitions (+ neutral), turn counter, weather/time, settings, stats, `GameDb`.

- **Read:** `game.turn`, `game.current_day` (`:483`), `game.current_turn_time_of_day`
  (`:478`), `game.conditions` (weather), `game.blue` / `game.red` / `game.neutral`,
  `game.coalitions` (`:179`), `game.coalition_for(player)` (`:238`),
  `game.ato_for(player)` (`:187`), `game.threat_zone_for(player)` (`:510`),
  `game.theater`, `game.db` (`game/db/gamedb.py:10` — `flights`/`front_lines`/`tgos`
  registries), `game.check_win_loss()` (`:384`).
- **Advance a full turn (end + replan + autosave):** `Game.pass_turn(no_action=False)`
  (`:359`). `no_action=True` skips without front-line movement.
- **★ Re-plan WITHOUT advancing the turn — the OPFOR hook:**
  `Game.initialize_turn(events, for_red=True, for_blue=True, squadrons_start_full=False)`
  (`:398`). **`for_red=True, for_blue=False` re-plans only OPFOR** and leaves the
  player's plan intact — the docstring documents exactly this case. Requires a
  `GameUpdateEvents()` instance. **`check_win_loss()` runs first** and short-circuits.
- **First turn:** `Game.begin_turn_0(squadrons_start_full)` (`:325`).
- **Budget:** `Game.adjust_budget(amount, player)` (`:246`).
- **Threat recompute after unit edits:** `Game.compute_threat_zones(events)` (`:504`).

`Coalition` (`game/coalition.py:34`) holds per-side state: `budget`, `ato`
(`AirTaskingOrder`), `air_wing` (`AirWing`), `armed_forces`, `procurement_requests`,
`transfers`, `bullseye`, `threat_zone`, `nav_mesh`, `last_turn_expenses`, `opponent`.

- `Coalition.initialize_turn(is_turn_0)` (`:187`) — **clears the ATO, resets the
  air wing, refunds outstanding orders, clears procurement requests**, then
  `plan_missions(now)` (`:223`) + `plan_procurement()` (`:234`). ⚠️ Any
  hand-authored flights for that side are wiped on replan; plan OPFOR only with
  `for_blue=False` so blue survives.
- `Coalition.plan_missions(now)` (`:223`) → `TheaterCommander(game, player).plan_missions(now, tracer)` + `MissionScheduler(...).schedule_missions(now)`. **This is the OPFOR-planner seam.**
- `Coalition.plan_procurement()` (`:234`) → `ProcurementAi.spend_budget`. For **RED**, management flags are forced `True` regardless of automation settings.
- `Coalition.end_turn()` (`:160`) — income + transfers.

`game/sim/` runs combat between turns; it does **not** advance the campaign turn.
`GameLoop` (`gameloop.py:20`) drives `MissionSimulation` (`missionsimulation.py:30`);
`MissionResultsProcessor` commits debrief/combat results. `GameLoopTimer`
(`gamelooptimer.py`) uses a real `threading.Timer` (background thread).

---

## ★ AI commander / OPFOR planner — `game/commander/`, `game/htn.py`

See [`03-opfor-planner.md`](03-opfor-planner.md) for the full hook design.

- `TheaterCommander.plan_missions(now, tracer)` (`game/commander/theatercommander.py:95`)
  — builds `TheaterState.from_game(...)`, loops `self.plan(state)` (HTN), executes
  `task.execute(coalition)` for each primitive task in the result. **The seam.**
- `PlanNextAction.each_valid_method` (`game/commander/tasks/compound/nextaction.py:27`)
  — the **fixed priority list** of compound tasks. This rigidity is why OPFOR is weak.
- `game/htn.py:71` — `Planner.plan()`: DFS over compound/primitive tasks; returns
  `PlanningResult(tasks, end_state)`.
- `TheaterState` (`game/commander/theaterstate.py:55`) — the world-state the planner
  reads: front lines, threat zones, enemy air defenses/ships/convoys, strike/oca
  targets, capturable points, barcaps needed, etc. `from_game()` at `:200` builds it
  via `ObjectiveFinder`.
- `ObjectiveFinder` (`game/commander/objectivefinder.py`) — finds & prioritises
  targets (`prioritized_points()`, `enemy_air_defenses()`, `strike_targets()`, …).
- Compound tasks: `game/commander/tasks/compound/*` (e.g. `capturebases.py`,
  `defendbases.py`, `degradeiads.py`). Primitive tasks: `…/primitive/*` (e.g.
  `cas.py`, `dead.py`, `strike.py`, `barcap.py`) — each `execute()` builds packages
  via `PackagePlanningTask` / `PackageFulfiller`.
- `MissionScheduler.schedule_missions(now)` (`game/commander/missionscheduler.py:23`)
  — spaces package TOTs across the turn.

---

## ATO / flights / packages — `game/ato/`

How missions are modeled and **created programmatically** (the "hands").

- `AirTaskingOrder` (`game/ato/airtaaskingorder.py:9`): `packages: list[Package]`;
  `add_package` (`:25`), `remove_package`, `clear` (`:36`).
- `Package` (`game/ato/package.py:24`): `target`, `flights[]`, `time_over_target`
  (absolute `datetime`), `waypoints`; `add_flight` (`:132`), `set_tot_asap(now)`
  (`:129`), `primary_task` (`:158`).
- `Flight` (`game/ato/flight.py:53`): ctor takes `(package, squadron, count,
  flight_type, start_type, divert)`. ⚠️ **Constructor has side effects** — it
  `squadron.claim_inventory(count)` (raises if insufficient) and claims pilots.
  `flight.flight_plan` (`:158`) lazily builds; **`recreate_flight_plan()` (`:366`)**
  after any change; `set_flight_type` (`:271`).
- `FlightType` enum (`game/ato/flighttype.py:8`); `StartType` enum (COLD/WARM/
  RUNWAY/IN_FLIGHT, `game/ato/starttype.py`).
- Flight-plan builders: `IBuilder.get_or_build` (`game/ato/flightplans/ibuilder.py:30`),
  `FlightPlanBuilderTypes.for_flight` (`flightplanbuildertypes.py:38`) maps
  `FlightType → Builder`. Can raise `PlanningError` / `NavMeshError` /
  `InvalidObjectiveLocation`.

**High-level creation recipe (preferred — use this):**

```python
from game.commander.missionproposals import ProposedMission, ProposedFlight
from game.commander.packagefulfiller import PackageFulfiller

mission = ProposedMission(location, [ProposedFlight(task, num_aircraft, escort_type)])
pkg = PackageFulfiller(
    coalition, theater, game.db.flights, settings
).plan_mission(mission, purchase_multiplier=1, now=now, tracer=tracer)   # packagefulfiller.py:166
if pkg is not None:
    coalition.ato.add_package(pkg)                                       # airtaaskingorder.py:25
# then space TOTs:
MissionScheduler(coalition, settings.desired_player_mission_duration).schedule_missions(now)
```

`plan_mission` allocates squadrons (`AirWing.best_squadron_for`,
`game/squadrons/airwing.py:113`), builds flights, calls `recreate_flight_plan`,
prunes/adds escorts. If no capable squadron in range, it files an
`AircraftProcurementRequest` instead of planning (`packagefulfiller.py:97`).

⚠️ Gotchas (full list in the ATO recon): pass the **shared** `game.db.flights` to
`Package`; build all primary flights *before* recreating plans (formation packages
share `PackageWaypoints`); a flight not added to a package leaks claimed inventory;
`package.time_over_target` is absolute and `datetime.min` until scheduled.

---

## Economy / procurement / orders — `game/procurement.py`, `game/purchaseadapter.py`, `game/groundunitorders.py`, `game/income.py`, `game/transfers.py`

**The clean, validated buy/sell path is the `PurchaseAdapter` family**
(`game/purchaseadapter.py`) — it handles budget adjustment, parking/capacity
checks, and pending-order/sale cancellation. Use it instead of poking internals.

```python
from game.purchaseadapter import AircraftPurchaseAdapter, GroundUnitPurchaseAdapter

# Buy 4 airframes into a squadron (checks budget, parking, capacity):
AircraftPurchaseAdapter(control_point).buy(squadron, 4)        # adapter.py:24/90
# Order 6 of a ground unit type at a base (checks budget + supply source):
GroundUnitPurchaseAdapter(control_point, coalition, game).buy(unit_type, 6)  # adapter.py:141
```

- `PurchaseAdapter.buy/sell` (`:24/:34`) deduct/refund via `coalition.adjust_budget`.
- **Aircraft can be sold**: `AircraftPurchaseAdapter.sell` / `can_sell =
  untasked_aircraft > 0` (`purchaseadapter.py:110/119`). Aircraft adapter buy
  increments `squadron.pending_deliveries`.
- **Ground units cannot be sold**: `GroundUnitPurchaseAdapter.can_sell` returns
  `False` and `do_sale` raises (`purchaseadapter.py:160/169`). Buy calls
  `control_point.ground_unit_orders.order({unit_type: 1})` (`groundunitorders.py:31`);
  `do_cancel_purchase` cancels a pending order (`ground_unit_orders.sell`).
- Auto-procurement: `ProcurementAi.spend_budget(budget)` (`game/procurement.py:115`);
  `AircraftProcurementRequest` (`:31`). `Income(game, player).total` (`game/income.py`).
- **Transfers** (move own ground units between own bases): `TransferOrder(origin,
  destination, units: dict[GroundUnitType, int])` (`game/transfers.py:94`) +
  `coalition.transfers.new_transfer(order, now)` (`:651`); list by iterating
  `coalition.transfers` (`PendingTransfers`, `:590`); `cancel_transfer(order)`
  (`:718`). `GroundUnitOrders` (`groundunitorders.py:21`) holds per-CP buy orders.
- `Settings.enemy_income_multiplier` (`game/settings/settings.py:125`) scales
  red's income. It's a **normal campaign/player setting** (per-campaign default,
  player-alterable) — the AI **reads** it (via `/settings`), it does not set it.

---

## Theater / map / control points / ground objects — `game/theater/`

The map data model — read for `turn_context`, plus the **player-legal spatial
moves** the feature does support: **moving movable ships** and **dragging
flight/package waypoints** (both via existing server routes; see the server
section below and [`04`](04-api-reference.md)). What's **not** supported is
cheat-level editing (capturing bases, placing/teleporting units, editing TGO unit
composition).

- `ControlPoint` (`game/theater/controlpoint.py:369`, a `MissionTarget`): subtypes
  `Airfield` (`:1334`), `NavalControlPoint` (`:1496`), `Carrier` (`:1618`),
  `Lha` (`:1658`), `OffMapSpawn` (`:1688`), `Fob` (`:1762`).
  - `.coalition` (`:433`), `.captured` (`:510`, returns `Player`),
    `.ground_unit_orders` (`:416`), `.is_carrier`/`.is_fleet`/`.is_fob`,
    `.can_operate(aircraft)` (`:1007`), `.allocated_aircraft(parking_type)` (`:1192`),
    `.squadrons`, `.position` (inherited `Point`).
- `TheaterGroundObject` (`game/theater/theatergroundobject.py:62`, a `MissionTarget`):
  SAM/EWR/ship/building/vehicle sites. `.is_dead` (`:128`), `.units` (`:132`),
  `.obj_name` (`:170`), `.mission_types(for_player)` (`:182`), `.alive_unit_count`
  (`:202`), `.coalition` (`:313`), `.control_point`, `.position`. Subtypes incl.
  `SamGroundObject` (`:607`), `EwrGroundObject` (`:710`), `ShipGroundObject` (`:738`),
  `BuildingGroundObject` (`:321`), `VehicleGroupGroundObject` (`:666`).
- `ConflictTheater` (`game/theater/conflicttheater.py`): `.controlpoints`,
  `.ground_objects`, `.iads_network`, `control_points_for(player)`. Landmap reloads
  from `resources/<terrain>/` on unpickle (`:50`).
- `FrontLine` (`game/theater/frontline.py`).
- **Coordinate system:** internal positions are `dcs.Point(x, y, theater.terrain)`
  in the terrain's projected (meter) CRS. Convert to map lat/lng with
  `Point(x, y, terrain).latlng()` → `LatLng(lat, lng)` (see `game/server/leaflet.py:66`).
  Going the other way (lat/lng → internal) uses `dcs` mapping helpers. Read tools
  emit lat/lng (matching the web map).
- **Player-legal spatial moves (existing server routes the AI reuses):**
  - **Move a ship/naval group:** `PUT /tgos/{id}/destination` (`set_tgo_destination`,
    `game/server/tgos/routes.py`) sets `tgo.target_position` — an **end-of-turn**
    reposition, checked against `ShipGroundObject.destination_in_range` /
    `max_move_distance` and not-over-land. `GET /tgos/{id}/destination-in-range`
    validates; clear route sets `target_position = None`. `TgoJs.moveable` /
    `target_position` (`game/server/tgos/models.py:35`) expose which groups move.
    (Naval *control points* have an analogous `cp.target_position` route,
    `game/server/controlpoints/routes.py`.)
  - **Adjust a flight/package waypoint:** `POST /waypoints/{flight_id}/{idx}/position`
    (`set_waypoint_position`, `game/server/waypoints/routes.py:49`) sets the waypoint
    to a lat/lng; for the **primary flight** it cascades join/ingress/split/refuel to
    the package and sibling flights (`update_package_waypoints_if_primary_flight`,
    `:87`). Read waypoints via `GET /waypoints/{flight_id}` (`:38`).
- **Map image source:** every map layer is already produced as lat/lng geometry by
  the server (`controlpoints`/`frontlines`/`threatzones`/`tgos`/`supplyroutes`
  routes + `game/server/leaflet.py`); render those to a PNG (or grab the live Qt
  `QWebEngineView`) for the multimodal map-image endpoint ([`04`](04-api-reference.md)).

---

## Coalition / air wing / squadrons / factions — `game/coalition.py`, `game/squadrons/`, `game/armedforces/`, `game/factions/`

"What does OPFOR have to work with."

- `AirWing` (`game/squadrons/airwing.py:22`): `squadrons: dict[AircraftType,
  list[Squadron]]`; `iter_squadrons()` (`:161`), `size` (`:179`),
  `squadrons_for(aircraft)` (`:51`), `best_squadron_for(...)` (`:113`),
  `best_available_aircrafts_for(task)` (`:129`), `auto_assignable_for_task(task)`
  (`:146`).
- `Squadron` (`game/squadrons/squadron.py`): `.aircraft` (`AircraftType`),
  `.owned_aircraft`, `.untasked_aircraft`, `.pending_deliveries`, `.active_pilots`
  (`:305`), `.location` (`ControlPoint`), `.primary_task`, `claim_inventory(count)`
  (`:416`), `can_auto_assign(task)` (`:351`), `expected_size_next_turn` (`:473`).
  Squadron sizing limits gated by `Settings.enable_squadron_aircraft_limits` (`:477`).
- `ArmedForces` (`game/armedforces/`) — the coalition's ground order-of-battle
  source. `Faction` (`game/factions/faction.py`) — what airframes/units/doctrine a
  side may field; `game/factions/FACTIONS` registry.
- **Faction allowed airframes:** `Faction.aircraft` / `awacs` / `tankers`
  (`game/factions/faction.py:64-71`); union via `Faction.all_aircrafts` (`:189`).
- **Squadron create/delete (air-wing config):** create =
  `air_wing.squadron_def_generator.generate_for_aircraft(aircraft)`
  (`squadrondefgenerator.py:44`; aircraft must be in `faction.all_aircrafts`, base
  must `can_operate`) → `Squadron.create_from(def, primary_task, max_size, base,
  coalition, game)` (`squadron.py:572`) → `air_wing.add_squadron` (`airwing.py:48`);
  new squadron starts at 0 aircraft. Delete = `air_wing.unclaim_squadron_def`
  (`airwing.py:42`) + drop from `air_wing.squadrons[aircraft]`. Reference UI flow
  (turn-0 config + cheat +/-): `qt_ui/windows/AirWingConfigurationDialog.py`.
- **Air-wing cheat flag:** `Settings.enable_air_wing_adjustments` (`settings.py:1707`)
  gates the free aircraft +/- (`cheat_add_aircraft`/`cheat_remove_aircraft`). The AI
  may create/delete squadrons (turn-0, or mid-campaign when this is on) but **never**
  the free +/- — it fills squadrons by buying.

---

## Existing FastAPI server & web client — `game/server/`, `client/`

The in-process API that powers the embedded Leaflet map. Relevant because Option
C reuses it.

- `app` (`game/server/app.py:21`): FastAPI with routers `controlpoints`, `flights`,
  `frontlines`, `waypoints`, `tgos`, `iadsnetwork`, `navmesh`, `mapzones`,
  `supplyroutes`, `debuggeometries`, `eventstream`, `game`, `qt`. CORS limited to
  `file://` (+ `localhost:3000` in debug).
- `Server(uvicorn.Server)` (`game/server/server.py:25`) runs the app on a **thread**
  via `run_in_thread()` (`:40`); started in `qt_ui/main.py:522`.
- `GameContext` (`game/server/dependencies.py:13`): classmethod singleton; `get()` /
  `require()` return the live `Game`. Wired by `GameContext.set_model(game_model)`
  (`qt_ui/windows/QLiberationWindow.py:71`). **Duck-typed** — it just needs an
  object with a `.game` attribute (the Qt import is `TYPE_CHECKING` only), so a
  headless stub model works.
- `QtContext` / `QtCallbacks` (`dependencies.py:35/49`): UI action bridge
  (`create_new_package`, `show_tgo_info`, …) — Qt-only, not reusable headless.
- Auth: `ApiKeyManager.KEY` random per process, `X-API-Key` header
  (`game/server/security.py`).
- `eventstream/` — websocket push of `GameUpdateEvents` to the map; the qt webview
  is the consumer.
- The existing endpoints are overwhelmingly **read/render**; the only mutations go
  through the `qt` router into Qt callbacks. Writing the planning surface means
  adding new routes/tools, not reusing existing ones.
- OpenAPI is generated and consumed by the TS client (`client/openapi-config.ts`,
  `client/src/api/_liberationApi.ts`). An MCP can mirror this approach but does not
  need the TS client.

---

## Persistence, logging, debrief, settings

- **Saves:** pickle (`.retribution`/`.liberation`), `persistency.load_game(path)`
  (`game/persistency.py:417`) + `Migrator(game, is_liberation)` (`game/migrator.py:28`);
  `save_game(game)` (`:428`), `autosave(game)` (`:454`). The feature runs against
  the **live** game (no headless load needed); saves matter only as the natural
  home for the `stored_context` scratchpad + `human_notes` — see
  [`05-context-and-persistence.md`](05-context-and-persistence.md).
- **Logging:** `logging_config.init_logging(version)` (`game/logging_config.py:11`)
  writes to **`./logs/`** (created relative to cwd), config from
  `resources/default_logging.yaml` (or `resources/logging.yaml` if present). An MCP
  log-reading tool reads files under `./logs/`. In-game message log is
  `game.informations` (`game.message(...)`).
- **Debrief:** `game/debriefing.py` + `game/polldebriefingfilethread.py` parse DCS
  mission results; `MissionResultsProcessor` (`game/sim/`) commits them into the
  `Game`. Relevant for "what did the player do last turn" context fed to the LLM.
- **Settings:** `Settings` (`game/settings/settings.py:93`). Relevant to the
  feature (all **read-only** to the AI, surfaced via `/settings`):
  `map_coalition_visibility` (`:170`, the "Fog of war" map mode — drives AI intel,
  see [`05`](05-context-and-persistence.md)), `player_income_multiplier` (`:116`),
  `enemy_income_multiplier` (`:125`), `automate_*` toggles (`:666`–`:768`), and
  **`enable_air_wing_adjustments`** (`:1707`, the air-wing cheat — gates the AI's
  *mid-campaign* squadron create/delete; see [`04`](04-api-reference.md) §G). The
  pure cheat flags (`enable_*_cheat`, `:1703`–`:1706`) exist but the feature **does
  not use them** — the AI only takes player-legal actions, and even with the
  air-wing cheat on it buys aircraft rather than using the free +/-.
