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

The authoritative, up-to-date list is the
[open PRs](https://github.com/juanjux/dcs-retribution/pulls). A grouped summary:

### Map & UI
- **Mission dashboard** — an embedded in-progress panel (live clocks, weather,
  per-flight status and a kill feed, with accept / submit-manually / abort)
  that replaces the old modal "waiting for mission result" dialog.
- **SAM ring tooltips + click-to-select** — hover a threat/detection ring to
  see the site name and its emitters; **left-click** a ring to open the site,
  **right-click** to start a package against it (so you can reach a site whose
  icon is buried under another marker). Package route lines show flight/package
  info on hover, and clicking one selects that package.
- **IADS network link colouring** by kind and state (comms / power), with an
  easier tooltip hover margin.
- **Finances dialog** showing income, automated HQ spending and net per turn.
- **Hide destroyed ground objects** — map layer toggles to hide destroyed,
  non-repairable ground objects.
- **Carrier/LHA ship groups on the map** like other naval groups.
- **Air Wing dialog improvements** — clickable squadron names, living-pilot /
  aircraft / idle counts, parking info, buy/sell controls and transfer indicators.
- **Plugin drop-down options** — plugin settings can offer choice (combo-box) options.

### Kneeboards
- **Friendly-packages list** plus a **package-targets map** page.
- **DEAD/SEAD target page** — one waypoint per target with an STPT column.
- **COMM2 presets** mirrored from COMM1 on twin-radio aircraft (plus an
  F/A-18-family COMM1/COMM2 fix), clearer auto-assigned **TACAN** codes, and an
  in-air-start **waypoint numbering** fix.

### Missions, AI & tasking
- **Campaign Doctrine: "non-combat (crash) air losses don't count"** — AI
  crashes/collisions DCS not credited to a weapon or SAM (which happen a lot because DCS AI is stupid) no longer deplete a
  squadron or kill the pilot; backed by per-loss kill attribution and shown in
  the debriefing.
- **Best standoff/PGM loadouts for AI DEAD flights**, per airframe.
- **Manual DEAD tasking** — non-DEAD-role aircraft can fly DEAD as a secondary task.
- **Money cheat for both coalitions** (OWNFOR + OPFOR).
- *(WIP on `master`)* **Electronic Warfare / "Jamming"** flight task for
  dedicated EW aircraft (EA-18G, EA-6B, Su-34, …).

### Modding & data
- **Anubis C-130 Hercules** — `suppress_ballute` crash fix and an air-assault
  zig-zag ingress (C-130 and helos).
- *(WIP on `master`)* **F-15EX, F-15C EG (Golden Eagle) and Eurofighter Typhoon**
  mod aircraft.

### Fixes
- App no longer lingers as a background process after the window is closed.
- Qt non-native dialogs avoid a QtWebEngine file-dialog deadlock.
- Robust payload handling — unparseable payload files are skipped; loadouts are
  written atomically.
- Carrier SEAD mission-type fix (no duplicate SEAD Escort; the SEAD task is present).
- Player ground-start flights no longer spawn in the air.
- Take-off no longer hangs when the fast-forward stop condition is unreachable.
- DCS no longer rejects missions with a locked-speed waypoint between TOT-locked
  waypoints.
- The sell-aircraft exploit that corrupted squadron counts is fixed.

---

For installation and general usage, see the upstream
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution) documentation.
