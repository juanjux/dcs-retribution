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

## The hook points (three levels, increasing power & risk)

All three reuse the engine's fulfilment machinery (packages, flight plans,
procurement) — we never ask the LLM for waypoints or raw units.

### Level 2 — Strategy hook (recommended first "decent opponent")

Let the LLM set **high-level strategy**, then let the existing HTN fulfil it.
Two concrete sub-options:

- **2a — Reorder/select methods.** Replace the fixed list in
  `PlanNextAction.each_valid_method` with an **LLM-chosen ordering / subset** for
  this turn, plus emphasis weights. Minimal surface, maximal reuse: the HTN still
  does target selection, precondition checking and fulfilment, but pursues the
  objectives the LLM prioritised, in the LLM's order. This alone makes OPFOR far
  less predictable and lets it *concentrate* (e.g. "this turn: DefendBases +
  DegradeIads only, ignore CaptureBases").
- **2b — Bias `ObjectiveFinder` / `TheaterState`.** Have the LLM rank/weight the
  candidate objectives (`prioritized_points()`, strike/oca/IADS target lists) and
  per-front stances, then feed those rankings into `TheaterState.from_game`. The
  HTN consumes a player-shaped world model.

Level 2 keeps **all** validation and flight planning in tried-and-tested code and
cannot produce an invalid plan. Best risk/reward for the first competent OPFOR.

### Level 3 — Autonomous plan (the end-state)

Replace the `while True` loop in `plan_missions` with an LLM that emits an
**ordered list of intents**, each mapping to an existing primitive-task /
fulfilment call. The wrapper validates and executes them, then **runs the
scripted commander to fill any gaps** (the fallback guarantee).

```python
# game/agent/opforbrain.py  (sketch — wraps the real planner)
class OpforBrain:
    def plan_missions(self, game, player, now, tracer) -> bool:
        """Return True if the LLM produced a usable plan, else False to fall back."""
        view = GameView(game, player).operational_picture()   # structured context (see below)
        try:
            plan = self.llm.plan_turn(view)                    # -> list[Intent]
        except Exception:
            return False
        applied = 0
        for intent in plan.intents:
            try:
                self.apply(intent, game, player, now, tracer)  # -> PackageFulfiller / PurchaseAdapter / stance
                applied += 1
            except (PlanningError, TransactionError, ...):
                continue                                        # skip bad intent, keep going
        return applied > 0
```

And the integration seam in the commander:

```python
# TheaterCommander.plan_missions, augmented
def plan_missions(self, now, tracer):
    if self.game.settings.opfor_llm_enabled and self.player.is_red:
        if OpforBrain(...).plan_missions(self.game, self.player, now, tracer):
            self._fill_gaps_with_scripted_planner(now, tracer)   # optional top-up
            return
    # original scripted path (fallback / blue / disabled)
    state = TheaterState.from_game(self.game, self.player, now, tracer)
    ...
```

> Wrapping `TheaterCommander.plan_missions` (not `Coalition.plan_missions`) keeps
> `MissionScheduler.schedule_missions` running afterward, so TOTs are spaced
> correctly regardless of who planned.

### What "execute an intent" maps to

| LLM intent | Engine call |
|------------|-------------|
| Fly a package (task, target, size, escorts) | `PackageFulfiller.plan_mission(ProposedMission(...))` → `coalition.ato.add_package` (see [`02`](02-codebase-map.md)) |
| Set a front-line stance | the corresponding primitive task / `CombatStance` on the `FrontLine` |
| Buy aircraft / ground units | `AircraftPurchaseAdapter.buy` / `GroundUnitPurchaseAdapter.buy` |
| Reposition a ship / edit the map | theater mutation (see [`04`](04-mcp-tools.md)) |

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
    {"type": "package", "task": "DEAD",  "target": "SAM Armadillo", "size": 4, "escort": "ESCORT"},
    {"type": "package", "task": "STRIKE","target": "Krymsk runway",  "size": 4, "escort": "SEAD"},
    {"type": "stance",  "front": "Krymsk-Novorossiysk", "value": "BREAKTHROUGH"},
    {"type": "buy_air", "base": "Krymsk", "squadron": "Su-34", "count": 2},
    {"type": "buy_ground", "base": "Krymsk", "unit": "T-90", "count": 6}
  ]
}
```

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

1. **Read path first.** Implement `GameView.operational_picture()` and expose it
   as an MCP resource/tool. Eyeball it; make sure it's a faithful, compact
   snapshot. (Enables L0 advisor.)
2. **Executor next.** Implement `apply(intent, …)` over `PackageFulfiller` +
   `PurchaseAdapter` + stances, exposed as MCP write tools. Drive it by hand from
   Claude Code against a save. (L1.)
3. **Strategy hook.** Wire L2a (LLM-chosen method ordering) into
   `PlanNextAction`/`TheaterCommander`. (First "decent opponent".)
4. **Autonomous + fallback.** Wire `OpforBrain.plan_missions` into
   `TheaterCommander.plan_missions` behind `settings.opfor_llm_enabled`, with the
   scripted planner as gap-filler/fallback. (L3.)
