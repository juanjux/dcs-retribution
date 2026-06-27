# 05 — Context, Memory & Persistence

This feature runs against the **live** game (`GameContext.require()`), so there is
**no headless bootstrap and no save-file loading** in the request path. Saves
matter only as the durable home for the AI's memory. This doc covers where the
non-obvious state lives and how the "intel" reads are sourced.

## `stored_context` — the AI scratchpad

A freeform store the AI owns (multi-turn strategy, lessons learned this campaign,
notes about the player). Requirement: it must survive **across turns**, **across
sessions**, and **across different AIs** — i.e. it belongs to *this campaign*.

- **Store it in the `Game`** (a new field, e.g. `game.ai_stored_context: dict |
  str`). Because the whole `Game` is pickled on save (`game/persistency.py:428`),
  it travels with the campaign automatically and is there on reload.
- Read/write via the service layer (`GET/PUT/POST /stored_context`,
  [`04`](04-api-reference.md)).
- Keep it small and structured (a dict of named notes, or a capped markdown blob)
  so it doesn't bloat saves or the LLM context window.
- **Save-compat caveat:** adding a *persisted* field to `Game` interacts with the
  fork's save-compat machinery. Prefer a single new attribute with a safe default,
  and backfill it in `Migrator` (`game/migrator.py:28`) / `Game.__setstate__`
  (`game/game.py:170`) so old saves load. (Alternative: a **sidecar JSON** keyed
  by campaign/save path, avoiding any pickle change — simpler for save-compat, but
  it doesn't travel if the user copies the save elsewhere. Recommend the in-`Game`
  field with a migrator backfill.)

## `human_notes` — player-authored rules

Freeform text the human types in a box in the Settings window ("play aggressively",
"don't attack the carrier", house rules). Surfaced to the LLM via `GET
/human_notes`.

- Store on `Settings` (`game/settings/settings.py:93`) as a string option, or
  alongside `stored_context` in the `Game`. `Settings` is part of the pickled
  `Game`, so it persists with the campaign.
- Read-only to the AI; only the human edits it (in the UI).

## `fog_of_war` — what OWNFOR detail the AI sees

`turn_context` always returns full **OPFOR (red)** detail. For **OWNFOR (blue)**
items it must honour a `fog_of_war` setting:

- **off:** return blue's full picture too (easier AI, omniscient).
- **on:** return only what red could plausibly know — detections via red's sensors
  (its radars/EWR/threat picture), last-seen positions, and what the **debrief**
  revealed (what blue actually flew/showed last mission). Filter blue control
  points / squadrons / movements accordingly.

Implement the filter in `game/agent/views.py`. The engine already models detection
(threat/detection zones, IADS network); use those as the "what red knows" source
rather than handing over blue's raw state.

## `prev_turns` — the after-action history

`GET /prev_turns?n=K` returns, per prior turn: units lost (and **how / who killed
them**), bases captured/lost, and notable events. Sources:

- **Debrief / combat results.** `game/debriefing.py` parses DCS mission results;
  `MissionResultsProcessor` (`game/sim/`) commits them into the `Game`, including
  **per-loss kill attribution** (this fork credits losses to a weapon/SAM/aircraft
  — the basis for "who killed it"; see the fork's "kill attribution" feature).
  Confirm the exact stored shape during implementation.
- **In-game message log.** `game.informations` (`game.message(...)`) carries
  human-readable turn events (captures, reinforcements, repairs).
- **Stats.** `game.game_stats` for aggregate per-turn numbers.

If a structured per-turn after-action record isn't already retained across turns,
add a small **append-only history** (a list of compact turn summaries on the
`Game`, written at `finish_turn`) so `prev_turns` has a stable source instead of
re-deriving from the latest debrief. This is the one piece most likely to need new
persisted state beyond `stored_context`.

## What gets persisted (summary)

| State | Lives in | Persists because |
|-------|----------|------------------|
| AI scratchpad (`stored_context`) | new `Game` field (or sidecar) | pickled with the save |
| `human_notes` | `Settings` (in `Game`) | pickled with the save |
| `fog_of_war` & feature toggles | `Settings` | pickled with the save |
| per-turn after-action (for `prev_turns`) | new append-only list on `Game` (if added) | pickled with the save |
| the plan itself (packages) | `Coalition.ato` | already pickled |

## Save format (only what's relevant here)

Saves are plain `pickle` (`.retribution`), the whole `Game` graph
(`game/persistency.py:428`). There's no JSON schema and no in-file version stamp.
The only implication for this feature: **any new persisted field must load on old
saves** — give it a default and backfill in `Migrator`/`__setstate__`. No other
part of the feature touches persistence (no loading, no headless setup).
