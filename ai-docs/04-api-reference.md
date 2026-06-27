# 04 — API Reference (REST + MCP, one backing each)

Every operation lives **once** in `game/agent/service.py` and is exposed two ways:

- **REST** under `/retribution-ai/*` — desktop agents `GET`/`POST` it (curl).
- **MCP** at `/mcp` — same operation as a tool (writes) or resource (reads), so a
  web LLM can use it via a custom connector.

All take the auth **token** (header `X-API-Key` or `?token=`). All return pydantic
models (JSON). Reads never mutate; writes only succeed at a turn/planning boundary
(see concurrency in [`01`](01-architecture.md)).

> **Guiding principle — the AI is a player, not a god.**
> The API exposes **only the actions a human player can take through the game**:
> plan packages/flights, buy/sell units, set front-line stances, run procurement,
> read state, keep notes. **No cheats, no map editing, no god-mode** — no setting
> the budget, no capturing bases, no placing/teleporting units. Settings such as
> `enemy_income_multiplier` and `map_coalition_visibility` are normal campaign/
> player settings: the AI **reads** them via `/settings`, it does not change them.
> This keeps OPFOR a fair opponent playing by the same rules as the human.

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
| **turn_context** — campaign, map, all OPFOR items (bases, wings, pilots, aircraft, ground units, units outside bases, buildings, SAMs, EWRs: position + alive/dead + health); OWNFOR detail limited per **`map_coalition_visibility`** (the real "Fog of war" map mode — see [`05`](05-context-and-persistence.md)) | `GET /turn_context` | resource `retribution://turn_context/{side}` | `theater.controlpoints`/`ground_objects`, `AirWing.iter_squadrons`, `Squadron.*`, `game.threat_zone_for`, `ObjectiveFinder.*`, coords via `leaflet` ([`02`](02-codebase-map.md)) |
| **prev_turns** — per prior turn: units lost (how / who killed them), bases captured, key events; `?n=K` for K turns ago (1 = last) | `GET /prev_turns?n=1` | tool `get_prev_turns(n)` | debrief history + `game.informations` + stats ([`05`](05-context-and-persistence.md)) |
| **packages** (read) — current OPFOR packages/flights (to verify none / resume) | `GET /packages?side=red` | tool `get_packages(side)` | `coalition.ato.packages`, `Package.*`, `Flight.flight_plan` |

`turn_context` is the high-value call. Build it in `game/agent/views.py` as a
compact, faithful snapshot; limit OWNFOR detail per `map_coalition_visibility`
(see [`05`](05-context-and-persistence.md)).

## C. Write — plan OPFOR (missions, economy, transfers)

| Op | REST | MCP | Service → engine |
|----|------|-----|------------------|
| **create packages/flights** | `POST /packages` | tool `create_packages(specs)` | `PackageFulfiller.plan_mission(ProposedMission(...))` → `coalition.ato.add_package`; then `MissionScheduler.schedule_missions` ([`02`](02-codebase-map.md)) |
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

## F. Out of scope: map editing & cheats

There is **no map-editing surface and no cheat surface** (per the guiding
principle above). The AI does not reposition/place units, capture bases, or set
budgets — only the legitimate player actions in sections A–E. If a future need
arises for a normal player capability that happens to move something on the map
(e.g. the fork's *movable ships*, which the human can do), add it as a **normal
player action** in section C — never as a cheat-gated "map edit".

## Error handling

Engine planning raises `PlanningError` / `NavMeshError` /
`InvalidObjectiveLocation`; purchases raise `TransactionError`. Catch at the
service boundary and return a **structured error** (code + message + which item),
so the LLM can adjust and retry a *different* action — never a stack trace, never
abort the whole turn.

## Resources vs. tools (MCP side)

- Side-effect-free reads (`start`, `howtoplay`, `settings`, `human_notes`,
  `turn_context`, `stored_context` read) → **resources** (cacheable context).
- Everything that mutates — creates, writes, **and deletes** (packages/flights,
  clear-ATO, buys, stances, stored_context write/delete, show_planning_dialog,
  plan_opfor) → **tools**. MCP has no HTTP verbs, so a REST `DELETE` maps to a
  `delete_*` / `clear_*` tool. All deletes obey the same turn/planning-boundary
  rule as other writes.
- Consider an MCP **prompt** "Plan OPFOR's turn" that bundles the workflow, so the
  user can one-shot it from the client.
