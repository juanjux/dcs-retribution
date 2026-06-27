# 03 — OPFOR Planner Hook (the centerpiece)

This is the heart of the feature: making OPFOR play well by putting an LLM where
the scripted commander's brain is.

## How the scripted commander works today

Per coalition, per turn, `Coalition.plan_missions(now)`
(`game/coalition.py:223`) runs:

```python
TheaterCommander(self.game, self.player).plan_missions(now, tracer)   # commander/theatercommander.py:95
MissionScheduler(self, ...).schedule_missions(now)                    # commander/missionscheduler.py:23
```

`TheaterCommander.plan_missions` (`theatercommander.py:95`):

```python
def plan_missions(self, now, tracer):
    state = TheaterState.from_game(self.game, self.player, now, tracer)  # theaterstate.py:200
    while True:
        result = self.plan(state)          # HTN search → PlanningResult | None  (htn.py:71)
        if result is None:
            return                          # planned all viable tasks this turn
        for task in result.tasks:           # primitive tasks
            task.execute(self.game.coalition_for(self.player))   # mutates the coalition: builds packages, sets stances…
        state = result.end_state
```

The HTN (`game/htn.py`) is a depth-first search. The top task `PlanNextAction`
offers its methods (compound tasks) in a **fixed order**
(`tasks/compound/nextaction.py:27`):

```
TheaterSupport, ProtectAirSpace, DefendBases, InterdictReinforcements,
AttackBattlePositions, CaptureBases, AttackAirInfrastructure, AttackBuildings,
AttackShips, DegradeIads, RecoverySupport
```

Each compound task decomposes into more tasks; each **primitive** task checks
`preconditions_met(state)` and, if met, `apply_effects(state)` (planning-time) and
later `execute(coalition)` (real mutation — builds a package via
`PackageFulfiller`, sets a front-line stance, etc.). `TheaterState`
(`theaterstate.py:55`) is the world model the planner reasons over (front lines,
threat zones, enemy air defenses, strike/oca targets, capturable points, …),
built from `ObjectiveFinder`.

**Why it's weak:** the order and the preconditions are static. The same priorities
fire every turn; there's no concentration of force, no read of the player, no
operational intent, no memory. It is locally greedy and globally incoherent.

## The hook: full autonomy (like a human player) + scripted fallback

**Decision (juanjux): go straight to full autonomy — no intermediate "strategy
hook" level.** The LLM plans the **whole** red turn, exactly as the human plans
theirs: it authors the entire plan (packages, flights, buys, stances, transfers,
ship/waypoint moves) through the same API ([`04`](04-api-reference.md)). The
scripted `TheaterCommander` is kept **only as a fallback**, so an OPFOR turn is
never empty. It reuses the engine's fulfilment machinery (packages, flight plans,
procurement) — we never ask the LLM for waypoints or raw units.

There are two ways the LLM can deliver that plan; both produce the same result (a
filled red ATO + purchases) and both fall back to the scripted commander.

### Mode A — client-driven (v1, recommended first)

The chat LLM (Claude Code / claude.ai) fills red's plan **through the API** during
the OPFOR window, just like the human fills theirs through the UI. The engine does
**not** auto-run the scripted planner for red; it leaves the red ATO for the AI to
author, and only falls back if the AI never plays.

The only engine change needed: when OPFOR-AI is enabled, **suppress the automatic
scripted planning of red** and **fall back** if red's turn is still empty when the
human advances.

```python
# Coalition.initialize_turn / plan_missions for red, augmented
def plan_missions(self, now):
    if self.game.settings.opfor_ai_enabled and self.player.is_red:
        return  # leave the ATO for the AI to author via the API (human says "your turn")
    # scripted path (blue, or AI disabled)
    TheaterCommander(self.game, self.player).plan_missions(now, tracer)
    MissionScheduler(self, ...).schedule_missions(now)

# Fallback at turn-advance: if red is AI-controlled but its ATO is empty
# (AI didn't play / errored / timed out), run the scripted commander so the
# turn is never empty.
```

> The API write path already runs `MissionScheduler.schedule_missions` after the AI
> adds packages (see [`04`](04-api-reference.md) §C), so TOTs are spaced correctly.

### Mode B — engine-driven (later; needs an embedded LLM)

For fully hands-off play (no human in the loop), the engine itself calls an LLM at
red's planning step. This wraps `TheaterCommander.plan_missions`:

```python
# game/agent/opforbrain.py  (engine-driven variant)
class OpforBrain:
    def plan_missions(self, game, player, now, tracer) -> bool:
        """Return True if the LLM produced a usable plan, else False to fall back."""
        view = GameView(game, player).operational_picture()
        try:
            plan = self.llm.plan_turn(view)                    # -> list[Intent] (Anthropic API)
        except Exception:
            return False
        applied = 0
        for intent in plan.intents:
            try:
                self.apply(intent, game, player, now, tracer)  # same executor as the API write path
                applied += 1
            except (PlanningError, TransactionError, ...):
                continue                                        # skip bad intent, keep going
        return applied > 0
# If it returns False (or leaves gaps), run the scripted commander as fallback.
```

Mode B needs an Anthropic API path + model/budget (open decision in
[`07`](07-branching-pr-and-risks.md)); Mode A needs none (the client is the LLM).
**Both share the same executor** (`apply(intent, …)` = the API write path) and the
same fallback, so Mode B is a later add-on, not a different design.

### What "execute an intent" maps to

| LLM intent | Engine call |
|------------|-------------|
| Fly a package (target + flights; each flight = task/squadron/count/payload; escort/SEAD are flights too) | `Package` + `Flight(...)` + `recreate_flight_plan` + `coalition.ato.add_package`, or `PackageFulfiller.plan_mission` for auto-select (see [`02`](02-codebase-map.md), [`04`](04-api-reference.md)) |
| Set a front-line stance | the corresponding primitive task / `CombatStance` on the `FrontLine` |
| Buy/sell aircraft, buy/transfer ground units | `AircraftPurchaseAdapter.buy/sell` / `GroundUnitPurchaseAdapter.buy` / `coalition.transfers.new_transfer` |
| Move a ship / adjust a waypoint | existing `tgos` `set_tgo_destination` / `waypoints` `set_waypoint_position` routes (player-legal map moves) |

(Only player-legal actions — same as the human; **no cheats** (budget/base-capture/
unit-placement). Moving movable ships and dragging waypoints **are** allowed. See
[`04`](04-api-reference.md).)

Because every intent routes through code that validates target/task
compatibility and builds the flight plan, a malformed intent fails *that intent*
only — it can't corrupt the turn.

## The data contract: what the LLM sees and returns

### Input — the "operational picture" (read from `Game`)

Assemble a compact, structured snapshot (pydantic models in `game/agent/`):

- **Situation:** turn #, date/time-of-day, weather; win/loss proximity.
- **Map:** control points (owner, type, position lat/lng, runway/parking, squadrons
  based there), front lines (where, vulnerable?), bullseye.
- **Force ratio:** what **red** has (`AirWing.iter_squadrons` → airframe, counts,
  ready pilots, base) vs. what **blue** has that red can see.
- **Threats:** enemy (blue) IADS/SAM rings, ships, threat zones
  (`game.threat_zone_for`), navmesh hazards.
- **Targets:** capturable points (`ObjectiveFinder.prioritized_points`), strike/oca
  targets, enemy air defenses, convoys/shipping.
- **Economy:** red budget, income, `enemy_income_multiplier`, last-turn expenses.
- **★ Player intel (the adaptivity):** what **blue** did last turn — from the
  current blue ATO (`game.ato_for(BLUE)`), recent captures, and the **debrief**
  (`game/debriefing.py`) of the last mission (what blue flew, what it hit, losses).
  This is what lets OPFOR plan *against the human*.

### Output — an ordered plan of intents (validated, then executed)

A small, typed schema (so we can use MCP/LLM structured output):

```jsonc
{
  "intent": "Concentrate DEAD+strike on the northern airbase to enable a capture next turn",
  "actions": [
    // A package is a target + flights; escort/SEAD are flights, not a field.
    {"type": "package", "target": "SAM Armadillo", "flights": [
        {"task": "DEAD", "squadron": "16th OVAP", "count": 2},
        {"task": "SEAD", "squadron": "3rd Fighter Sqn", "count": 2}
    ]},
    {"type": "package", "target": "Krymsk runway", "flights": [
        {"task": "STRIKE", "squadron": "559th Bomber", "count": 4},
        {"task": "ESCORT", "squadron": "3rd Fighter Sqn", "count": 2}
    ]},
    {"type": "stance",  "front": "Krymsk-Novorossiysk", "value": "BREAKTHROUGH"},
    {"type": "buy_air", "base": "Krymsk", "squadron": "Su-34", "count": 2},
    {"type": "buy_ground", "base": "Krymsk", "unit": "T-90", "count": 6},
    {"type": "transfer", "origin": "Maykop", "dest": "Krymsk", "units": {"T-90": 6}}
  ]
}
```

(Flight fields mirror the `POST /packages` schema in [`04`](04-api-reference.md):
`task`, origin `squadron` (fixes airframe + base), `count`, optional `start_type`/
`payload`/`waypoints`. Omit waypoints to let the engine auto-build a valid plan.)

Target identifiers should be **names/ids the read tools handed out**, so the
executor can resolve them back to engine objects unambiguously (don't trust the
LLM to invent coordinates).

## Why not let the LLM emit raw missions?

Because the engine already encodes a lot of hard-won correctness: task↔target
compatibility (`MissionTarget.mission_types`), reachability gating (DEAD that
can't actually reach a shielded SAM — `TheaterState.dead_can_reach`,
`theaterstate.py:113`), navmesh routing around threats, squadron range/inventory,
parking limits, escort needs, TOT spacing. Re-deriving that in prompt-space is
fragile and slow. Let the LLM do what it's good at — **operational judgment** —
and let the engine do what it's good at — **valid execution**.

## Suggested build order for the hook

1. **Read path first.** Implement the turn-context read in `game/agent/service.py`
   and expose it via the API (REST `GET` + MCP resource — see
   [`04`](04-api-reference.md)). Eyeball it; make sure it's a faithful, compact
   snapshot. (For development you can stop here and review the LLM's proposed plan
   without applying it — a dry-run, purely a test aid.)
2. **Executor.** Implement `apply(intent, …)` over `PackageFulfiller` +
   `PurchaseAdapter` + stances + transfers + ship/waypoint moves in the service
   layer, exposed as REST + MCP write tools. Drive a **full** red turn by hand from
   Claude Code against the live game.
3. **Suppress + fallback (Mode A).** When `opfor_ai_enabled`, stop the engine from
   auto-planning red (leave the ATO for the AI); add the fallback that runs the
   scripted commander if red's turn is still empty at advance time. This is the
   v1 "decent opponent" — the AI plays the whole turn like a player.
4. **Engine-driven (Mode B, later).** Wire `OpforBrain.plan_missions` (embedded
   LLM) into `TheaterCommander.plan_missions`, reusing the same executor and
   fallback, for hands-off play.
