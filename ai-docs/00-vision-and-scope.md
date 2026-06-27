# 00 — Vision & Scope

## The problem

DCS Retribution generates a turn-based strategic campaign on top of DCS World.
Between missions, each coalition's turn is planned by an **automated commander**
(`game/commander/`) built on a Hierarchical Task Network (HTN). For the human
player this is optional (they plan their own ATO in the UI), but for **OPFOR
(red) it is the only planner** — it decides every enemy package, target, stance
and purchase.

That commander is **weak and predictable**, by design and by structure:

- `PlanNextAction.each_valid_method` (`game/commander/tasks/compound/nextaction.py:27`)
  yields the same **fixed priority order of task types every single turn**:
  `TheaterSupport → ProtectAirSpace → DefendBases → InterdictReinforcements →
  AttackBattlePositions → CaptureBases → AttackAirInfrastructure →
  AttackBuildings → AttackShips → DegradeIads → RecoverySupport`.
- Selection is driven purely by **preconditions and local heuristics**, with **no
  model of the player**, no memory of what worked last turn, no concentration of
  force, no deception, no operational shape.

The result plays like an idiot: it reacts locally, spreads effort thinly, and is
trivial to read once you've played a few turns.

## The idea

Put an **LLM in the commander's seat for OPFOR**. The LLM consumes a rich,
structured picture of the theater (front lines, threats, IADS, what red has to
work with, what the player did last turn) and produces an **operational plan**:
which objectives to prioritise, where to concentrate, what packages/tasks to fly,
what to buy, what posture to take on each front. The engine's existing machinery
turns that intent into concrete, validated missions.

> **Design principle: replace the brain, reuse the hands.**
> The LLM decides *what to do*. The engine's `PackageFulfiller`, flight-plan
> builders, `MissionScheduler` and `PurchaseAdapter` decide *how to do it* and
> guarantee the output is valid. We do **not** ask the LLM to emit waypoints or
> raw unit data.

## Goals

1. **A competent, adaptive OPFOR** that plans red turns via an LLM and is
   meaningfully harder/more interesting to play against than the scripted AI.
2. **An MCP surface** that exposes the game to any MCP client (Claude Code,
   Claude Desktop) for:
   - reading state (turn, coalitions, ATO, map, threats, finances, logs);
   - planning/mutating (create packages, buy units, set stances, advance turns);
   - editing the map ("place or change things") — reposition ships, edit/seed
     ground objects, capture bases (cheat-gated).
3. **Headless operation** so plans can be generated against save files outside
   the Qt app (great for development, testing, and batch experiments).

## Non-goals (initial)

- Replacing the **player's** planning UX. The human still plans blue in the Qt
  UI; the MCP can *assist* blue but that's secondary.
- Driving the in-DCS mission in real time. The MCP plans the **strategic turn**;
  DCS still runs the generated `.miz`.
- Rewriting the HTN. It stays as a **fallback/baseline** (see below) and as a
  source of reusable primitive tasks.
- A polished GUI for configuring the agent. Settings + a thin status surface are
  enough initially.

## Autonomy levels (ship them incrementally)

The feature should support a dial, from least to most autonomous:

| Level | Behaviour | Use |
|-------|-----------|-----|
| **L0 — Advisor** | LLM reads state and returns a written plan / suggestions; nothing is applied automatically. | Safest first milestone; lets juanjux eyeball plan quality. |
| **L1 — Assisted apply** | LLM proposes discrete actions (packages, buys, stances) that are applied via MCP write tools, but the human/engine triggers each. | Validates the write path end-to-end. |
| **L2 — Strategy hook** | LLM sets high-level strategy (objective priorities, per-front stance, budget split, task emphasis); the existing HTN fulfils the details. | Lowest-risk "decent opponent" — reuses all fulfilment logic. |
| **L3 — Autonomous OPFOR** | At red's planning step, the LLM plans the entire red turn; the scripted commander only fills gaps. | The end-state vision. |

L2 and L3 are the heart of the feature; see [`03-opfor-planner.md`](03-opfor-planner.md).

## The fallback guarantee

**An OPFOR turn must never come out empty.** If the LLM is unavailable, times
out, errors, or leaves a front unplanned, the scripted `TheaterCommander` must
run (for the whole turn, or just to fill gaps the LLM left). This keeps the game
playable regardless of the agent's state and makes the feature safe to ship
behind a setting. Concretely: the LLM hook wraps `TheaterCommander.plan_missions`
and falls back to the original code path on any failure.

## Success criteria

- Red turns planned by the LLM are **valid** (no engine exceptions; missions
  generate and fly) — guaranteed by reusing the fulfilment path.
- Red behaviour is **visibly more coherent**: concentration of force, sensible
  DEAD-before-strike sequencing, responses to the player's last turn.
- The whole thing is **toggleable** and **falls back cleanly**.
- Works both **headless** (against a save) and **live** (against the running Qt
  game).
