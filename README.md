# DCS Retribution — juanjux fork

A personal fork of [DCS Retribution](https://github.com/dcs-retribution/dcs-retribution)
that bundles a number of features and fixes which are not (yet) in upstream
Retribution. Some features and fixes are also adapted from the
[414Ret fork](https://github.com/bradyccox/414Ret).

## How development works here

Development now happens **in this fork**. New work is opened as a
[Pull Request against this repository](https://github.com/juanjux/dcs-retribution/pulls)
(targeting `juanjux-dev`), **not** against upstream — this keeps the upstream
review queue light and makes it easy for other forks to cherry-pick whatever
they want. Each PR describes the feature or fix it adds. Individual fixes may
still be offered upstream case by case.

## Branches

| Branch | Purpose |
| --- | --- |
| **`dev`** | A clean mirror of upstream `dcs-retribution/dev`. Pristine, untouched — the base everything is cut from. |
| **`juanjux-dev`** | The curated line. A feature lands here **only after it has been tested and reviewed via a PR** (opened against `juanjux-dev`). Branched from `dev` and periodically re-synced with upstream `dev`. |
| **`master`** | The live "buffed" build where new things are tried out and soak-tested. It is **ahead of `juanjux-dev`** and carries work-in-progress not yet PR'd. **Build this branch** if you want to play with everything. |

In short: experiment on `master`, promote the proven pieces to `juanjux-dev`
through a PR, and keep `dev` a pristine upstream mirror. When upstream `dev`
gets new commits they are occasionally pulled into `master` and `juanjux-dev`.

## Features not in upstream Retribution

Each item links to the fork PR that implements it. The authoritative, up-to-date
list is the [pull requests](https://github.com/juanjux/dcs-retribution/pulls?q=is%3Apr).

### Map & UI
- **Mission dashboard** — an embedded in-progress panel (live clocks, weather,
  per-flight status and a kill feed, with accept / submit-manually / abort)
  that replaces the old modal "waiting for mission result" dialog.
  ([#27](https://github.com/juanjux/dcs-retribution/pull/27))
- **SAM ring tooltips + click-to-select** — hover a threat/detection ring to
  see the site name and its emitters; **left-click** a ring to open the site,
  **right-click** to start a package against it (so you can reach a site whose
  icon is buried under another marker). Package route lines show flight/package
  info on hover, and clicking one selects that package.
  ([#8](https://github.com/juanjux/dcs-retribution/pull/8))
- **IADS network link colouring** by kind and state (comms / power), with an
  easier tooltip hover margin.
  ([#10](https://github.com/juanjux/dcs-retribution/pull/10))
- **Finances dialog** showing income, automated HQ spending and net per turn.
  ([#7](https://github.com/juanjux/dcs-retribution/pull/7))
- **Hide destroyed ground objects** — map layer toggles to hide destroyed,
  non-repairable ground objects.
  ([#16](https://github.com/juanjux/dcs-retribution/pull/16))
- **Carrier/LHA ship groups on the map** like other naval groups.
  ([#23](https://github.com/juanjux/dcs-retribution/pull/23))
- **Air Wing dialog improvements** — clickable squadron names, living-pilot /
  aircraft / idle counts, parking info, buy/sell controls and transfer indicators.
  ([#25](https://github.com/juanjux/dcs-retribution/pull/25),
  [#26](https://github.com/juanjux/dcs-retribution/pull/26))
- **Plugin drop-down options** — plugin settings can offer choice (combo-box) options.
  ([#2](https://github.com/juanjux/dcs-retribution/pull/2))

### Kneeboards
- **Friendly-packages list** plus a **package-targets map** page.
  ([#11](https://github.com/juanjux/dcs-retribution/pull/11))
- **DEAD/SEAD target page** — one waypoint per target with an STPT column.
  ([#18](https://github.com/juanjux/dcs-retribution/pull/18))
- **COMM2 presets** mirrored from COMM1 on twin-radio aircraft (plus an
  F/A-18-family COMM1/COMM2 fix), clearer auto-assigned **TACAN** codes, and an
  in-air-start **waypoint numbering** fix.
  ([#12](https://github.com/juanjux/dcs-retribution/pull/12),
  [#20](https://github.com/juanjux/dcs-retribution/pull/20),
  [#14](https://github.com/juanjux/dcs-retribution/pull/14))

### Missions, AI & tasking
- **Campaign Doctrine: "non-combat (crash) air losses don't count"** — AI
  crashes/collisions DCS not credited to a weapon or SAM (which happen a lot because DCS AI is stupid) no longer deplete a
  squadron or kill the pilot; backed by per-loss kill attribution and shown in
  the debriefing.
  ([#1](https://github.com/juanjux/dcs-retribution/pull/1))
- **Best standoff/PGM loadouts for AI DEAD flights**, per airframe.
  ([#6](https://github.com/juanjux/dcs-retribution/pull/6))
- **Manual DEAD tasking** — non-DEAD-role aircraft can fly DEAD as a secondary task.
  ([#4](https://github.com/juanjux/dcs-retribution/pull/4))
- **Money cheat for both coalitions** (OWNFOR + OPFOR).
  ([#3](https://github.com/juanjux/dcs-retribution/pull/3))
- *(WIP on `master`, not yet PR'd)* **Electronic Warfare / "Jamming"** flight
  task for dedicated EW aircraft (EA-18G, EA-6B, Su-34, …).
- *(WIP on `master`, not yet PR'd)* **Automated ground-object / building repair**
  — the HQ can repair damaged SAM sites, vehicle groups and buildings each turn,
  with tunable budgets and priorities.
- *(WIP on `master`, not yet PR'd)* **Movable ships** — reposition non-carrier
  naval groups on the campaign map.

### Modding & data
- **Anubis C-130 Hercules** — `suppress_ballute` crash fix and an air-assault
  zig-zag ingress (C-130 and helos).
  ([#9](https://github.com/juanjux/dcs-retribution/pull/9))
- *(WIP on `master`, not yet PR'd)* **F-15EX, F-15C EG (Golden Eagle) and
  Eurofighter Typhoon** mod aircraft.

### Fixes
- App no longer lingers as a background process after the window is closed.
  ([#15](https://github.com/juanjux/dcs-retribution/pull/15))
- Qt non-native dialogs avoid a QtWebEngine file-dialog deadlock.
  ([#17](https://github.com/juanjux/dcs-retribution/pull/17))
- Robust payload handling — unparseable payload files are skipped; loadouts are
  written atomically.
  ([#21](https://github.com/juanjux/dcs-retribution/pull/21))
- Carrier SEAD mission-type fix (no duplicate SEAD Escort; the SEAD task is present).
  ([#22](https://github.com/juanjux/dcs-retribution/pull/22))
- Player ground-start flights no longer spawn in the air.
  ([#19](https://github.com/juanjux/dcs-retribution/pull/19))
- Take-off no longer hangs when the fast-forward stop condition is unreachable.
  ([#24](https://github.com/juanjux/dcs-retribution/pull/24))
- DCS no longer rejects missions with a locked-speed waypoint between TOT-locked
  waypoints.
  ([#13](https://github.com/juanjux/dcs-retribution/pull/13))
- The sell-aircraft exploit that corrupted squadron counts is fixed.
  ([#5](https://github.com/juanjux/dcs-retribution/pull/5))

## From the 414Ret fork

These are adapted from the [**414Ret** fork](https://github.com/bradyccox/414Ret)
(414th Joint Fighter Group), with thanks to its authors — 414Ret bundles many
more features; listed here are the ones incorporated into this fork. They are
currently on `master` (being integrated; not all PR'd yet). TIC vendors Grendel's
TIC script (MIT).

- **Troops In Contact (TIC)** — a dynamic frontline: ground forces actually fight
  along the FLOT (with ambient fire) instead of behaving as two static walls.
- **Mission Impact debrief summary** — bases captured/lost, runway damage and a
  both-sides loss overview above the casualty tables.
- **AI routes around the ground battle** — the active front line becomes a
  navmesh routing hazard, so transit flights detour around it.
- **Frontline units spread along the line** instead of stacking laterally.
- **Package context bar** — a one-line ATO summary (primary task, flight count,
  player slots, real TOT, departure bases).
- **Flight-creation context** — live explanatory text when picking task /
  aircraft / squadron, with informative squadron tooltips.
- **Bulk flight altitude** — an "apply to all" en-route altitude control; the
  per-waypoint altitude steps by 1000 ft instead of 1 ft.
- **Building-card cleanup** — drops the "Missing Recon Picture" placeholder for
  tidier ground-object cards.
- **Self-documenting plugin options** — per-plugin description text and cleaned
  labels on the LUA plugins options page.
- **CurrentHill Iran pack** — Shahed-136, IRGCN fast-attack craft and a
  `[CH] Iran 2020` faction (upstream ships the UK CurrentHill pack, not Iran).
- Selected crash fixes (flight-exit, AWACS/tanker orbit deconfliction, malformed
  mod payloads).

---

For installation and general usage, see the upstream
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution) documentation.
