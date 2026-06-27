# 04 — MCP Tool & Resource Catalog

The MCP surface, grouped by purpose. Each tool is a thin wrapper over the
agent-core (`game/agent/`), which is a thin wrapper over the engine APIs in
[`02-codebase-map.md`](02-codebase-map.md). Keep tools **coarse and intent-shaped**
(few well-documented tools the model can reason about), not a 1:1 mirror of every
engine method.

Conventions:
- **Read** tools/resources never mutate. **Write/plan** tools mutate the `Game`
  and (live mode) push `GameUpdateEvents`.
- All return **pydantic models** (FastMCP structured output) so the client gets a
  machine-readable schema.
- Object references use **stable names/ids** issued by read tools; write tools
  resolve them back to engine objects and **raise a clear error** if unknown.
- Mutations are **gated**: economy/map cheats only when the matching `Settings`
  cheat flag is on; turn advancement only when the sim is paused / at a boundary.

---

## A. Session / save management

| Tool | Backing | Notes |
|------|---------|-------|
| `list_savegames()` | glob `persistency.save_dir()` | enumerate `.retribution` saves + autosave |
| `load_savegame(path)` | `load_game` + `Migrator` ([`05`](05-headless-bootstrap-and-saves.md)) | Option A only; one game per process |
| `save_game()` / `save_game_as(path)` | `persistency.save_game` / set `savepath` | requires `game.savepath` set |
| `autosave()` | `persistency.autosave` | |
| `attach_live_game()` | `GameContext.require()` | Option C only; binds tools to the running Qt game |

In live mode (Option C) the save tools are replaced by `attach_live_game` and an
explicit `save` that calls the same persistency path on the live `Game`.

---

## B. Read — situation & map (resources or read tools)

These back the LLM "operational picture" ([`03`](03-opfor-planner.md)).

| Tool | Backing |
|------|---------|
| `get_turn_state()` → turn, day, time-of-day, weather, win/loss | `game.turn`, `current_day`, `conditions`, `check_win_loss` |
| `get_coalitions()` → per side: faction, budget, income, air-wing size | `game.blue/red`, `Income`, `AirWing.size` |
| `get_control_points()` → owner, type, position(lat/lng), parking, based squadrons | `theater.controlpoints`, `leaflet` conversion |
| `get_ground_objects(side?)` → SAM/EWR/ship/building sites: kind, owner, position, alive units, dead? | `theater.ground_objects`, `TheaterGroundObject.*` |
| `get_front_lines()` → location, vulnerable?, current stance | `theater`, `FrontLine`, `CombatStance` |
| `get_threat_picture(for_side)` → enemy IADS rings, ships, threat zones | `game.threat_zone_for`, `ObjectiveFinder` |
| `get_targets(for_side)` → capturable points, strike/oca/IADS/convoy targets (ranked) | `ObjectiveFinder.*` |
| `get_air_wing(side)` → squadrons: airframe, owned/untasked, pending, ready pilots, base, primary task | `AirWing.iter_squadrons`, `Squadron.*` |
| `get_operational_picture(for_side)` → **the whole bundle above**, compact | `game/agent/GameView` |

`get_operational_picture` is the high-value one — it's the single call the OPFOR
brain consumes.

---

## C. Read — ATO & plans

| Tool | Backing |
|------|---------|
| `list_packages(side)` → target, primary task, TOT, flight count, has-players | `coalition.ato.packages`, `Package.*` |
| `get_package(id)` → flights, waypoints, takeoff/TOT times, escort windows | `Package`, `Flight.flight_plan` |
| `list_flights(package_id)` → type, count, squadron, airframe, start type, dep/arr | `Flight.*` |
| `get_flight_plan(flight_id)` → ordered waypoints (type, lat/lng, alt, tot) | `FlightPlan.waypoints` |

---

## D. Read — intel & logs (adaptivity)

| Tool | Backing |
|------|---------|
| `get_last_debrief()` → what blue flew/hit, losses, captures last turn | `game/debriefing.py`, `MissionResultsProcessor` outputs |
| `get_blue_ato_summary()` → what the player planned this turn (for red to react to) | `game.ato_for(BLUE)` |
| `get_messages(limit)` → in-game event log | `game.informations` |
| `read_logs(lines, level?)` → tail of `./logs/*.log` | files under `./logs/` ([`02`](02-codebase-map.md)) |

---

## E. Write / plan — missions (the executor)

| Tool | Backing | Validation |
|------|---------|-----------|
| `plan_package(side, target, task, size, escort?)` | `PackageFulfiller.plan_mission(ProposedMission(...))` → `ato.add_package` | raises on bad task/target, no squadron, no route |
| `create_empty_package(side, target)` → id | `Package(target, game.db.flights)` | |
| `add_flight(package_id, task, count, squadron?, start_type?)` | `Flight(...)` + `recreate_flight_plan` | claims inventory; raises if insufficient |
| `set_package_tot(package_id, when\|asap)` | `package.set_tot_asap` / assign | |
| `remove_flight(flight_id)` / `remove_package(package_id)` | `Package.remove_flight` / `ato.remove_package` | returns pilots+aircraft |
| `schedule_all(side)` | `MissionScheduler.schedule_missions(now)` | space TOTs across the turn |

> After any flight edit, the tool must `recreate_flight_plan()`. For formation
> packages, add all primary flights before recreating plans (see ATO gotchas in
> [`02`](02-codebase-map.md)).

---

## F. Write / plan — economy

| Tool | Backing | Gate |
|------|---------|------|
| `buy_aircraft(base, squadron, count)` | `AircraftPurchaseAdapter(cp).buy` | budget/parking/capacity |
| `sell_aircraft(base, squadron, count)` | `…buy/sell` | |
| `buy_ground_units(base, unit_type, count)` | `GroundUnitPurchaseAdapter(cp, coalition, game).buy` | budget + supply source |
| `set_front_line_stance(front, stance)` | `CombatStance` on `FrontLine` | |
| `adjust_budget(side, amount)` | `Game.adjust_budget` | **cheat** — only if money cheat on |
| `run_auto_procurement(side)` | `Coalition.plan_procurement` | let the scripted buyer spend the rest |

---

## G. Write — map edits ("place or change things")

All gated behind the relevant cheat `Settings` flag; accept **lat/lng** and
convert to internal `Point`.

| Tool | Backing | Gate |
|------|---------|------|
| `move_ship_group(tgo_id, lat, lng)` | reposition non-carrier naval `TheaterGroundObject` | movable-ships feature exists in this fork |
| `set_control_point_owner(cp, side)` | base-capture path | `enable_base_capture_cheat` |
| `repair_ground_object(tgo_id)` / `edit_ground_object(...)` | TGO unit edits | follow buy/sell-TGO replan rules |

⚠️ Map edits that change ownership or units **must** trigger a re-init:
`Game.initialize_turn(events, for_red=…, for_blue=…)` (mirroring the cheat-capture
flow documented at `game/game.py:398`), and a `compute_threat_zones` if units
changed.

---

## H. Turn control & the OPFOR brain

| Tool | Backing | Notes |
|------|---------|-------|
| `plan_opfor_turn()` | `Game.initialize_turn(events, for_red=True, for_blue=False)` | **re-plans only red**, leaves blue intact |
| `replan(for_red, for_blue)` | `Game.initialize_turn(events, …)` | general re-init |
| `advance_turn(no_action=False)` | `Game.pass_turn` | end + replan + autosave; **live mode: only when sim paused** |
| `opfor_brain_plan()` | `OpforBrain.plan_missions` ([`03`](03-opfor-planner.md)) | LLM plans red; scripted fallback fills gaps |
| `get_plan_diff()` | compare ATO before/after | so the human can review what the agent did |

---

## Resources vs. tools

- Expose the **read snapshots** (operational picture, map, ATO) as **resources**
  (`@mcp.resource("retribution://state/operational/{side}")`) so the client can
  pull context cheaply and cache it, *and* as tools for ad-hoc calls.
- Expose **everything that mutates** as **tools** only (resources are meant to be
  side-effect-free reads).
- Consider a **prompt** (`@mcp.prompt`) that packages "you are the OPFOR commander;
  here is the operational picture; produce a plan in this schema" so juanjux can
  invoke a one-shot "plan red's turn" from the client.

## Error handling

- Engine planning raises `PlanningError` / `NavMeshError` /
  `InvalidObjectiveLocation`; purchases raise `TransactionError`. Catch these at
  the tool boundary and return a **structured error** (not a stack trace) so the
  LLM can adjust and retry a *different* intent.
- Never let one bad intent abort the whole turn — skip it and continue (see
  `OpforBrain` sketch in [`03`](03-opfor-planner.md)).
