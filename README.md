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
- **Air Wing squadron list, redesigned** — the aircraft type leads the row so the list
  can be scanned, the primary task shows as a role chip, and the list gained a filter, a
  sort order and grouping by type or base, both remembered between openings.
  ([#118](https://github.com/juanjux/dcs-retribution/pull/118))

  <img src="https://raw.githubusercontent.com/juanjux/dcs-retribution/juanjux/screenshots/airwing-redesign.png" width="760">

- **"All >>" and "None <<" in the unit transfer dialog** — a base can hold two dozen
  unit types, and queueing a whole garrison meant clicking every row up to its count.
  The two buttons sit above the list and move everything at once, or clear it.
  ([#117](https://github.com/juanjux/dcs-retribution/pull/117))
- **Your payload library is backed up on startup.** DCS keeps your custom
  loadouts as one `.lua` per airframe under `MissionEditor/UnitPayloads`, and
  nothing else holds a copy — not the campaign save, not the generated `.miz`.
  That folder is also the one people are told to delete when the Mission Editor
  misbehaves, so Retribution now snapshots it before anything can write to it
  and keeps the last ten under `Retribution/PayloadBackups`. Recovering is
  copying a folder back.
  ([#102](https://github.com/juanjux/dcs-retribution/pull/102))
- **Mission dashboard** — an embedded in-progress panel (live clocks, weather,
  per-flight status and a kill feed, with accept / submit-manually / abort)
  that replaces the old modal "waiting for mission result" dialog.
  ([#27](https://github.com/juanjux/dcs-retribution/pull/27))
- **SAM ring tooltips** — hover a threat/detection ring to see the site name and
  its emitters; package route lines show flight/package info on hover. (The
  click-to-select half of this made it upstream as #761.)
  ([#8](https://github.com/juanjux/dcs-retribution/pull/8))
- **IADS network links coloured by STATE** — upstream already tints them by kind
  (comms / power); this adds active vs inactive on top, plus an easier tooltip
  hover margin.
  ([#10](https://github.com/juanjux/dcs-retribution/pull/10))
- **Finances dialog** showing income, automated HQ spending and net per turn.
  ([#7](https://github.com/juanjux/dcs-retribution/pull/7))
- **Hide destroyed ground objects** — map layer toggles to hide destroyed,
  non-repairable ground objects.
  ([#16](https://github.com/juanjux/dcs-retribution/pull/16))
- **Carrier/LHA ship groups on the map** like other naval groups.
  ([#23](https://github.com/juanjux/dcs-retribution/pull/23))
- **Air Wing dialog improvements** — clickable squadron names and parking info
  (the rest of the series — pilots, inventory/purchasing, transfers, idle counts —
  made it upstream as #737–#741 and #855).
  ([#25](https://github.com/juanjux/dcs-retribution/pull/25),
  [#26](https://github.com/juanjux/dcs-retribution/pull/26))
- **Set loadout as default** — in the Edit Flight payload tab, a "Set as default
  for plane and mission" button makes the selected named payload the default for
  that aircraft and mission type, so new flights of that type start with it. It
  remembers your choice by name — it does not rename or overwrite any payload.
  ([#49](https://github.com/juanjux/dcs-retribution/pull/49),
  [#51](https://github.com/juanjux/dcs-retribution/pull/51))
- **Persistent map layers** — the map-layers panel remembers its visible layers,
  base map and open groups in the campaign save, so they survive turns and
  reopening the app instead of resetting to defaults.
  ([#54](https://github.com/juanjux/dcs-retribution/pull/54))
- **Ground-object health bars with a full contract** — green intact, yellow
  damaged, **orange whenever repairs are pending** (partial or fully-dead), red
  dead-unrepaired. Also fixes damaged SAMs that showed no bar at all while they
  still projected a threat ring, hiding real attrition.
  ([#56](https://github.com/juanjux/dcs-retribution/pull/56),
  [#86](https://github.com/juanjux/dcs-retribution/pull/86))

### Kneeboards
- **Friendly-packages list** plus a **package-targets map** page.
  ([#11](https://github.com/juanjux/dcs-retribution/pull/11))
- **DEAD/SEAD target page** — one waypoint per target with an STPT column.
  ([#18](https://github.com/juanjux/dcs-retribution/pull/18))
- **COMM2 presets** mirrored from COMM1 on twin-radio aircraft (plus an
  F/A-18-family COMM1/COMM2 fix) and clearer auto-assigned **TACAN** codes.
  ([#12](https://github.com/juanjux/dcs-retribution/pull/12),
  [#20](https://github.com/juanjux/dcs-retribution/pull/20))

### Missions, AI & tasking
- **Mission Log** (plugin, off by default) — a running commentary of what happens to
  your side while you fly: who shot down whom and with what, which targets went down,
  who ejected, who crashed with nobody shooting. DCS has all of these events but calls
  the aircraft `STAG BARCAP|2|14|F-15C Eagle| Pilot #2` and does not know the pilot at
  all, so the generator seeds `RETRIBUTION_PILOTS` (unit name → pilot name) and the
  script reads the aircraft type straight out of the unit name — mod aircraft come out
  right without a table of their own. Each message goes only to the coalition it is news
  for: a kill for the shooter, a loss for the other side. Every category has its own
  toggle, and the roster is only seeded when the plugin is on. Interceptions are polled
  rather than eventful — DCS fires nothing for "I have seen him and I am going after
  him" — so every fighter group is asked what its radar holds and what the datalink
  handed it, and the message says which of the two found the target.
  ([#120](https://github.com/juanjux/dcs-retribution/pull/120))
- **Turn times from the sun** — the four turn slots are derived from the
  theater's latitude and the campaign date instead of one fixed window per map.
  Kola's shipped table gives `dawn: [3, 9]` and `day: [9, 18]` all year, so a
  December dawn turn started at 03:00 in the pitch dark and a day turn could
  begin after sunset; now dawn sits an hour after sunrise, day at solar noon,
  dusk an hour before sunset and night two hours after it, each with an hour of
  slack either side. North of the arctic circle there is no sunrise to anchor to,
  so the slots hang off solar noon and stay dark — if it is night, it is night.
  A theater keeps its old table with `daytime_mode: table` in
  `resources/theaters/<map>/info.yaml`; campaigns saved before this keep theirs.
  ([#113](https://github.com/juanjux/dcs-retribution/pull/113))
- **Campaign Doctrine: "non-combat (crash) air losses don't count"** — AI
  crashes/collisions DCS not credited to a weapon or SAM (which happen a lot because DCS AI is stupid) no longer deplete a
  squadron or kill the pilot; backed by per-loss kill attribution and shown in
  the debriefing.
  ([#1](https://github.com/juanjux/dcs-retribution/pull/1))
- **Best standoff/PGM loadouts for AI DEAD flights**, per airframe.
  ([#6](https://github.com/juanjux/dcs-retribution/pull/6))
- **Realistic helicopter range** — carrier/LHA-capable transport helos (CH-53E,
  CH-47D/F, SH-60B, UH-60A/L, UH-1H) get a proper `max_range` (their round-trip
  combat radius) instead of the 50 nm helicopter default, so air-assault flights
  are no longer under-ranged by the planner.
  ([#64](https://github.com/juanjux/dcs-retribution/pull/64))
- **One-way air assault ("remain at destination")** — a helicopter-only Air Assault
  option: the helos land at the objective and do NOT return home, so a one-way assault
  uses their full ferry range instead of a round-trip radius. At turn end the survivors
  redeploy there if you capture the base, otherwise they are lost.
  ([#64](https://github.com/juanjux/dcs-retribution/pull/64))
- **Manual DEAD tasking** — non-DEAD-role aircraft can fly DEAD as a secondary task.
  ([#4](https://github.com/juanjux/dcs-retribution/pull/4))
- **Money cheat for both coalitions** (OWNFOR + OPFOR).
  ([#3](https://github.com/juanjux/dcs-retribution/pull/3))
- **Air Wing cheat** — per-squadron aircraft count with free +/- controls to add
  or remove aircraft (shown only when opened from the Cheats tab), handy for
  testing mod aircraft without spending money.
  ([#41](https://github.com/juanjux/dcs-retribution/pull/41))
- **Automated ground-object / building repair** — the HQ repairs damaged SAM
  sites, vehicle groups and buildings each turn, with tunable budgets and priorities.
  ([#29](https://github.com/juanjux/dcs-retribution/pull/29))
- **Repair reporting in the turn panel** — shows what each side finished repairing
  this turn (all object types, not just runways), and your side's in-progress
  repairs with turns remaining.
  ([#43](https://github.com/juanjux/dcs-retribution/pull/43))
- **Smart Threat Reaction** — a plugin that keeps AI aircraft at Passive Defense
  by default and switches only the flight a missile is actually guiding on to
  Evade Fire (read from the engine via `weapon:getTarget`), so one SAM launch no
  longer sends every nearby package defensive. Prototype.
  ([#63](https://github.com/juanjux/dcs-retribution/pull/63))
- **Custom cloud preset packs** — a campaign setting that makes a community
  cloud-preset weather mod's presets available to the mission generator: choose
  Bandit's Cloud Presets, Weather 2.0 or ATMOS-X to match the pack you have
  installed in DCS (only one active at a time, since the packs reuse the same
  preset keys for different clouds).
  ([#53](https://github.com/juanjux/dcs-retribution/pull/53))
- **ATMOS-X live weather** — with the ATMOS-X pack selected, the turn's weather can be
  a real METAR observation fetched through the ATMOS-X CLI, for a station picked
  automatically (the airfield you fly from if it reports, otherwise the nearest that
  does) or set by ICAO. It is fetched when the turn is built, so the turn panel, the
  kneeboards, the active runway and the carrier's course into wind all match the
  mission. The campaign keeps its own date and time. The weather panel also gained a
  full tooltip and a button to re-fetch the observation.
  ([#101](https://github.com/juanjux/dcs-retribution/pull/101))
- **IADS infrastructure can be rebuilt** — comms towers, power stations and command
  centres produce no income, so they had no repair price and stayed rubble for the rest
  of the campaign once bombed. A network you can only dismantle is not worth attacking
  twice, and neither side ever restored its own. They now have a flat rebuild cost
  (power 15M, command centre 10M, comms tower 5M) and still earn nothing, so striking
  the network becomes an attrition loop rather than a one-off: the SAMs behind a
  destroyed power station go dark, and the owner has to pay to bring them back. The AI
  ranks them alongside its ammo depots so it does not rebuild every oil derrick first.
  ([#97](https://github.com/juanjux/dcs-retribution/pull/97))
- **A destroyed IADS building now reads as destroyed, not as absent.** `skynet_nodes`
  dropped any node or connection whose units were all dead, and Skynet treats a missing
  dependency as satisfied — so bombing a power station switched its SAMs back on the
  next mission, and destroying a coalition's *last* command centre emptied the table and
  handed it perfect command back. Buildings keep reaching Skynet destroyed; verified in
  DCS that a static spawned dead answers `getByName=ok, isExist=false, life=0`, which is
  exactly what Skynet tests. Vehicle-backed roles still drop out, since their groups have
  no name left once every unit is gone.
- **Ferry flights may return fire** — a relocating squadron flew on Weapon Hold, so it
  would evade a missile without ever shooting at the fighter that launched it and a
  relocation across contested airspace was a free kill. Ferries now fly Return Fire:
  still a transit that will not go hunting, but no longer defenceless.
  ([#99](https://github.com/juanjux/dcs-retribution/pull/99))

### Campaigns
- **Syria — Invasion of the Canary Islands 2030**, with the **Spain 2030** and
  **Morocco 2030** factions. A rework of NoGoodNews' original: both sides fly what they
  are expected to field by 2030 (Spain on Eurofighters plus one Hornet wing, Morocco on
  F-16s, JF-17s and F-35s), each Spanish wing carries its own livery, and both navies are
  built from real hulls with pinned compositions -- the Juan Carlos I as an LHA, Castilla
  and Galicia as L-52 landing docks, and a Moroccan surface group south of the islands.
  Air defences are roughly a third lighter than the original, mostly duplicates removed
  from the same field, which shortens the DEAD grind and helps the frame rate. The IADS
  is fully wired: every command centre, comms tower and power station feeds something
  local, so striking the network actually degrades it, and every base on a front has a
  motorpool holding its undeployed armour as a bombable target.
  ([#98](https://github.com/juanjux/dcs-retribution/pull/98))
### LLM-controlled OPFOR (REST API + MCP)
- **An external LLM can play the enemy commander.** A REST API and an MCP server
  expose a token-frugal turn context (forces, targets, threats, economy, naval,
  motorpools, runway states, plus an optional rendered map image) and full player
  parity to act on it: create packages and flights, buy/sell aircraft and ground
  units, set front-line stances, relocate squadrons, move fleets, repair and
  rebuild sites. The LLM gets its own briefing served at `/start` and `/howtoplay`,
  refined across real campaigns played against it. Lives on the
  [`experiment-mcp`](https://github.com/juanjux/dcs-retribution/tree/experiment-mcp)
  branch (and master); not intended for upstream.

### Modding & data
- **F-15EX Eagle II, F-15C EG (Golden Eagle) and Eurofighter Typhoon** mod aircraft.
  ([#31](https://github.com/juanjux/dcs-retribution/pull/31),
  [#32](https://github.com/juanjux/dcs-retribution/pull/32),
  [#33](https://github.com/juanjux/dcs-retribution/pull/33))
- **High Digit SAMs updated to 1.4.0 → 2.1.0** — the New Game wizard still offered
  v1.4.0 while the mod had moved on in both directions. Adds the **SAMP/T battery**
  (Aster 30 — Block 1/1NT/2 launchers at 120/150/200 km, ARABEL fire control, Ground
  Fire 300 search radar at 400 km) and the **SA-7/SA-7b Strela-2 MANPADS**, which go to
  six 1970s-80s factions that fielded no MANPADS at all. Retires what the mod dropped.
  A unit type DCS cannot resolve is discarded in silence, so a stale preset costs you a
  site that never spawns while Retribution still counts it: a new test walks every
  preset and fails on anything that does not exist. The same change fixes **SA-10B/
  S-300PS sites that never spawned and were immortal**: 2.1.0 dropped the S-300PS
  family, DCS discards unit types it cannot resolve, and Retribution kept the empty
  site alive with its threat ring up. They now use the stock S-300PS.
  ([#96](https://github.com/juanjux/dcs-retribution/pull/96))
- **High Digit SAMs Ultimate Compilation, as a second selectable build.** The two HDS
  builds are separate mods that cannot both be installed, so the New Game wizard now
  offers them as mutually exclusive choices instead of assuming the classic one. The
  Ultimate adds its own sites on top of 2.1.0's, and a faction only sees the presets its
  chosen build actually ships. Campaign authors have to wire the new sites in themselves;
  nothing is enabled by default.
  (branch [`juanjux/hds_2_1_0_and_ultimate`](https://github.com/juanjux/dcs-retribution/tree/juanjux/hds_2_1_0_and_ultimate),
  upstream [#956](https://github.com/dcs-retribution/dcs-retribution/pull/956))
- **CurrentHill China pack synced to 1.1.6** — the New Game wizard label and unit
  data track the latest CH China Military Asset Pack. 1.1.4→1.1.6 added/removed no
  units (only upstream fixes), so this is a version-note sync, not a data migration.
  (branch [`juanjux/ch_china_1.1.6`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ch_china_1.1.6))

### Fixes
- **Neutral FARPs were invisible on the map.** The map hides a control point whose ship
  group is sunk, so a destroyed carrier disappears with the other non-repairable wrecks.
  That flag was read from whichever ground object of the control point is flagged
  `is_control_point`, on the assumption that only a carrier or an LHA has one — but a FOB
  has one too, its own structures. Reading that as destroyed filed both neutral FARPs
  under the "destroyed (non-repairable)" layer, which is off by default, so they were
  never drawn. The auto-planner kept fragging Air Assaults at them, because it works off
  the model rather than the map, but a human could not select what was not there. Now
  gated on `is_fleet`. ([#119](https://github.com/juanjux/dcs-retribution/pull/119))
- **A CAP guarding its own base could vanish the instant the mission started.** DCS
  deletes an air-started flight on spawn if its route is short enough, without it flying
  a metre: the engine runs the last waypoint's tasks straight away, and for an
  air-started AI flight that waypoint carries the script that despawns it over its base.
  No event, nothing in the debriefing — the flight simply never existed. Measured by
  editing only the patrol coordinates of one generated mission and flying each: total
  routes of 35.8 and 42.6 nm died, 46 nm and up flew, whatever the shape. It is the
  total and not any single leg (a triangle of three 20 nm legs flies). The cold war
  doctrine can put the end of the track 8 nm from the field with a 12 nm track — a 24 nm
  round trip — and Retribution's own planner produced a 4.4 nm track start for a BARCAP
  over Banak. Patrol routes are now lengthened **away from the enemy** until they reach
  60 nm, so the threat-facing end and the station stay where the planner put them.
  (branch [`juanjux/min-patrol-route`](https://github.com/juanjux/dcs-retribution/tree/juanjux/min-patrol-route))
- **Some building objectives could never be recorded as destroyed, however often you
  levelled them.** An objective is credited by a `MapObjectIsDead` trigger on its zone,
  which is only true once *every* map object inside the polygon is dead — and many of
  those polygons hold scenery that cannot be destroyed at all (`WOODPILE_01` and friends
  report a life of 1e38), so those objectives survive their own destruction indefinitely.
  Nothing else catches them: DCS does report the death, but `getName()` on scenery
  returns the object's numeric id rather than a name, so the id went into `dead_events`
  and the debriefing, which resolves scenery by trigger-zone name, discarded it. It reads
  as flaky rather than broken because the objectives whose zones happen to be clean do
  score. Over one Kola mission: **978 scenery deaths, 15 of them direct hits on named
  objectives; two objectives credited normally while CAPYBARA, CICADA and IBIS recorded
  nothing at all across three turns, being levelled each time.** Deaths are now matched
  to the nearest objective by position, with a radius measured rather than guessed: hits
  that destroyed the objective landed within 29 m of its zone and collateral died from
  31 m out, so 30 m keeps the first and rejects the second. The `MapObjectIsDead`
  triggers go with it — 342 of them in one mission. Verified in game: those same three
  came back **4/4, 6/6 and 9/10** destroyed, matching the log building by building and
  the save afterwards, against 667 pieces of collateral rejected and no false positives.
  ([`b7cbd73`](https://github.com/juanjux/dcs-retribution/commit/b7cbd73df),
  [`afff790`](https://github.com/juanjux/dcs-retribution/commit/afff790e0))
- **A bombed-out motorpool showed on the map as a permanent loss.** `repairable` falls
  back to `purchasable`, which is `False` for a motorpool because it is never bought as a
  group — but the motorpool is only a view of the base's undeployed armor, so procuring
  ground units refills it. There is nothing to repair and nothing permanently lost.
  ([`81fb0d4`](https://github.com/juanjux/dcs-retribution/commit/81fb0d4d8))
- **A Strike put every iron bomb on a single aimpoint, so repeat raids re-cratered
  the same rubble.** The planner spreads a Strike across one waypoint per target, but
  the dumb-bomb task ignored that and aimed at the centroid of the whole objective. Two
  causes: the bombing carpet was sized from the *mean* distance to the targets rather
  than their spread, which is about a third of what it must cover — 65 m over a camp
  several hundred metres across — and the carpet was chosen by the group's DCS task
  instead of by airframe, so tactical aircraft carpet bombed as well. Heavy bombers now
  lay a carpet over the real extent in one pass; everything else re-attacks with one
  aimpoint per target and the load split between them, exactly as guided bombs and ASMs
  already did. A B-52 could fly two raids of thirty-odd Mk 82 at a ten-building camp and
  leave eight of them untouched.
  ([`1209839`](https://github.com/juanjux/dcs-retribution/commit/120983924))
- **Stores that no weapon file claimed slipped past their own introduction date.**
  The A-6E carries the TALD on four MER clsids that `ADM-141A.yaml` did not list, so
  they read as unknown stores: no DECOY type for SEAD planning, and no year, which armed
  a 1983 campaign with a 1987 decoy. The AN/ALQ-167 had no weapon file at all and so
  never counted as a jammer; it is dated 1982 now. Same class of hole on the Hornet's
  LAU-115 rails, where only three of the AIM-7P's four clsids were declared and the
  fourth flew a 1987 Sparrow in any campaign.
  ([`309b39c`](https://github.com/juanjux/dcs-retribution/commit/309b39c24), [`06b7955`](https://github.com/juanjux/dcs-retribution/commit/06b7955e1))
- **The A-6E dropped iron instead of its laser-guided bombs, always.** Its TRAM turret
  is an internal designator, but nothing declared it, so the planner saw a loadout with
  no targeting pod and swapped every GBU out — at every date, in every campaign. Strike
  flew Mk 83 instead of GBU-16, OCA/Runway Mk 84 instead of GBU-10.
  ([`5545351`](https://github.com/juanjux/dcs-retribution/commit/55453512e))
- **The naval magazines plugin never loaded.** Plugin options were written into the
  mission unquoted and lowercased, which is fine for `true`/`false` and numbers but not
  for a string: the anti-ship weapon patterns contain `3M24`, and an unquoted `3M24` is a
  malformed Lua number, so DCS threw a syntax error over the whole configuration block.
  No staggered weapons release and no cross-turn magazine, in every mission.
  ([`5b73214`](https://github.com/juanjux/dcs-retribution/commit/5b73214e7))
- **Blufor Late Cold War (80s) had no beyond-visual-range fighter.** Its only Viper was
  the Block 50, a 1991 jet that DCS gives no Sparrow on any pylon, so before the AMRAAM's
  1994 it degraded to four AIM-9M. The faction now also fields the F-16A, which is
  period-correct and does carry the AIM-7M. The Block 50 stays for the player to fly.
  ([`a603bfd`](https://github.com/juanjux/dcs-retribution/commit/a603bfd86))
- **The AH-1W had no anti-armour weapon in a 1983 campaign.** DCS models only the
  BGM-71D, whose IOC is 1985, so the Cobra degraded to rocket pods and the faction
  had nothing guided against armour — the AH-1 has carried TOW since 1973. Blufor
  Late Cold War (80s) now overrides the weapon's year, which the weapon file itself
  suggests as the stand-in for the variants DCS does not model.
  ([`8ea3214`](https://github.com/juanjux/dcs-retribution/commit/8ea3214c7))
- **Take Off died with "Duplicate convoy unit", stranding the campaign** — the name
  counter reset each turn onto a convoy still in transit. Same bug upstream.
  ([#93](https://github.com/juanjux/dcs-retribution/pull/93))
- **SA-10B/S-300PS sites never spawned and were immortal.** High Digit SAMs 2.1.0 no
  longer ships the S-300PS family, DCS silently drops unit types it cannot resolve, and
  Retribution kept the site alive and its threat ring up. Now the stock S-300PS.
  ([#96](https://github.com/juanjux/dcs-retribution/pull/96))
- **A refused purchase now says why.** "Cannot buy more X" was the same message
  whether you were short of money, out of parking, or at the squadron's aircraft
  cap — three problems with three different answers. It now names the one that
  applied ("costs 20M, budget is 16.2M", "no free parking at Beirut-Rafic Hariri",
  "squadron is at its cap of 24"). The LLM planner reads the same string over the
  API, where an opaque refusal is worse still.
  ([#87](https://github.com/juanjux/dcs-retribution/pull/87))
- **A faction edited mid-campaign now reaches the buy menus.** A coalition's forces
  are built from its faction once, at campaign start, and each force group freezes
  the units it could reach then. The Air Wing dialog lets you edit a running
  campaign's faction, but only a preset-group change triggered a rebuild — adding a
  unit changed nothing you could buy. Adding an early-warning radar left every EWR
  site still offering the SAM search radars it had fallen back to.
  ([#110](https://github.com/juanjux/dcs-retribution/pull/110))
- **A package with an impossible TOT could hold for the whole mission** — flight plans
  are built backwards from the time on target, so a TOT the flights cannot physically
  reach puts the push time before the mission even starts. The hold point emitted that
  as its release timer without a floor, and DCS never fires a trigger scheduled for a
  negative time. Seen on a DEAD package given TOT +5 min from a base 29 minutes away:
  four aircraft orbited instead of flying. The release is now clamped to mission start.
  ([#100](https://github.com/juanjux/dcs-retribution/pull/100))
- **Spanish AAA sites were empty, and then wrong.** The faction listed the WWII 2 cm
  Flak 38, which needs the WWII Assets Pack; without it DCS discards every gun and the
  site defends nothing. It now fields the Flakpanzer Gepard, the gun Spain actually
  bought from Germany, alongside its Roland, Avenger and Stinger short-range cover.
  ([#95](https://github.com/juanjux/dcs-retribution/pull/95))
- **Air-assault troops stood still instead of taking the base.** Capturing needs
  every enemy ground unit out of a 3 km radius, but CTLD walked unloaded troops to
  their waypoint and left them there, so one surviving vehicle a kilometre away
  blocked the capture indefinitely. Dropped troops and vehicles now sweep for the
  nearest enemy ground unit inside that same radius and advance on it, and are left
  to fight once within 250 m. New CTLD option, on by default.
  ([#85](https://github.com/juanjux/dcs-retribution/pull/85))
- **Front-line ground units never fought** — three stacked causes: defenders held
  position waiting for the enemy's first CAS package (a running Hold the AI never
  drops, up to half an hour); a negative hold duration wrapped to ~24 h; and the
  FLOT took its alarm state from a mislabelled SAM performance toggle, leaving
  every vehicle green/passive. Defenders now engage from minute one; the toggle is
  relabelled "Air defenses start in red alert mode" and no longer touches the FLOT.
  ([#79](https://github.com/juanjux/dcs-retribution/pull/79))
- **The recurring in-mission freeze** (~100 s stalls repeating until mission end,
  runaway RAM, and the long-standing 0-byte `state.json`) — scenery objects report a
  numeric name, and one scenery death (a taxiing aircraft clipping a runway light is
  enough) made the state encoder build a multi-million-hole array on the sim thread.
  Scenery deaths are now ignored by the state export.
  ([#80](https://github.com/juanjux/dcs-retribution/pull/80))
- The **Support Info** kneeboard page now spans multiple pages when a package has
  many flights, instead of pushing the AEW&C / tanker / JTAC tables off the bottom
  of a single page (they were silently lost). Sections are packed by measured height
  and a long table is split across pages; the title shows `(n/total)` only when there
  is more than one page, and a package that fits still renders on a single page.
  ([#69](https://github.com/juanjux/dcs-retribution/pull/69))
- Bumped PySide6/Qt to 6.8.3 which switches acceleration to D3D11 and thus fixes
  some OpenGL hangs that probably happened in combination with other software.
  ([#52](https://github.com/juanjux/dcs-retribution/pull/52))
- Qt non-native dialogs avoid a QtWebEngine file-dialog deadlock.
  ([#17](https://github.com/juanjux/dcs-retribution/pull/17))
- Robust payload handling — unparseable payload files are skipped; loadouts are
  written atomically.
  ([#21](https://github.com/juanjux/dcs-retribution/pull/21))
- Player ground-start flights no longer spawn in the air.
  ([#19](https://github.com/juanjux/dcs-retribution/pull/19))
- The sell-aircraft exploit that corrupted squadron counts is fixed.
  ([#5](https://github.com/juanjux/dcs-retribution/pull/5))
- Kneeboard waypoint numbering is correct for in-air-start flights.
  ([#14](https://github.com/juanjux/dcs-retribution/pull/14))
- Escorts of an AWACS/tanker hold on the protected flight's racetrack instead of a
  far-away point, so they actually protect it.
  ([#42](https://github.com/juanjux/dcs-retribution/pull/42))
- **Air-assault ingress no longer zig-zags.** The join leg is anchored to the
  package's ingress point rather than the initial point, so helicopters (and the
  C-130) fly a straight run-in instead of doubling back five miles.
  ([#9](https://github.com/juanjux/dcs-retribution/pull/9), upstream
  [#804](https://github.com/dcs-retribution/dcs-retribution/pull/804))

## From the 414Ret fork

These are adapted from the [**414Ret** fork](https://github.com/bradyccox/414Ret)
(414th Joint Fighter Group), with thanks to its authors — 414Ret bundles many
more features; listed here are the ones incorporated into this fork, each
crediting the original 414Ret author (the recent additions land via attributed
PRs on `juanjux-dev`, so any can be reverted cleanly). TIC vendors Grendel's
TIC script (MIT).

414Ret moves fast, so its feature list is re-reviewed periodically and only a
part of it is taken: every feature carried here is one more thing to reconcile
on each upstream sync, so the bar is "clearly worth the maintenance", not
"interesting". The last review covered the 1087 commits between 2026-06-23 and
2026-08-22. Ports are cherry-picked with the original author preserved —
`git log --author=bradyccox` is the authoritative list of what has been taken,
and it is longer than this section.

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
- **CurrentHill Iran pack** — Shahed-136, IRGCN fast-attack craft and a
  `[CH] Iran 2020` faction. Upstream now ships the Sweden, China, Russia, USA, UK
  and Ukraine CurrentHill packs; Iran is the one it does not.
- Selected crash fixes (flight-exit, AWACS/tanker orbit deconfliction, malformed
  mod payloads).
- **Escorts can defend themselves before the JOIN point** — an escort was generated
  at an ROE that only permits engaging *designated* targets, and the task that
  designates them attaches at JOIN, so through the whole hold and transit it could
  not shoot even while being shot at. Escorts now spawn able to return fire and
  escalate at JOIN.
- **Kills on scenery objectives inside culled regions are recorded** — the buildings
  behind such an objective exist whether or not the region is culled, so bombing one
  collapsed it but the strike never reached the debrief.
- **TIC: a combatant killed mid-move no longer crashes the scheduler** — a dead
  group's missing coordinate was indexed inside MOOSE, producing a caught crash and a
  `dcs.log` flood.
- **A patrol's orbit is charged to its fuel** — the on-station leg is scheduled by
  time but its fuel was billed as the straight line between the racetrack ends, so a
  45-minute CAP was undercharged about fivefold and every fuel figure (kneeboard
  ladder, RTB margin, sim) was optimistic.
- **Coastal batteries can engage ships** — land-based anti-ship sites fire on their
  own at hulls in range, the way fleets do, instead of watching them sail past.
  Off by default (a mod battery firing anti-ship missiles has crashed DCS).
- **Unified map-layers panel** — the scattered map layer toggles consolidated into
  one dark, grouped, collapsible panel with presets.
  ([#38](https://github.com/juanjux/dcs-retribution/pull/38), porting 414Ret #96/#98)
- **DEAD reachability gate** — the planner no longer optimistically marks a SAM
  "cleared" when the assigned flight cannot actually reach it.
  ([#37](https://github.com/juanjux/dcs-retribution/pull/37), porting 414Ret #83)
- **Weapons coverage refresh** — more modern PGMs and air-to-air missiles across
  factions, without the era date-gating (our introduction years are kept).
  ([#35](https://github.com/juanjux/dcs-retribution/pull/35), porting 414Ret #82)
- **Player despawns aren't combat losses** — leaving an aircraft mid-mission no
  longer depletes your squadron in the debrief.
  ([#34](https://github.com/juanjux/dcs-retribution/pull/34), porting 414Ret #64)
- **Two guidance radars per SAM site** — every layout fielded exactly one
  engagement radar, so a single anti-radiation missile on it was a functional site
  kill (launchers alive but blind) and SEAD collapsed into one shot per site. The
  Track Radar slot doubles across the generic 2/4/6-launcher layouts, SA-2, SA-3,
  SA-5, S-300, HQ-22, S-350, the mixed SA-2/SA-3 site, the reinforced SA-6, NASAMS-3
  and Sky Sabre, with the second position 45-121 m from the first so one blast
  cannot take both. The Patriot family already fielded two and is now test-locked.
  (porting 414Ret #582)
- **More SAM site layouts, tighter EWR radar pool** — dedicated battery layouts
  instead of every site reusing the same handful of shapes.
- **Bulk flight altitude** — "apply to all" for en-route waypoint altitude, and the
  per-waypoint arrows step 1000 ft instead of 1 ft. (porting 414Ret #805)
- **Era-gated cockpit options** — the payload editor stops offering a JHMCS on an
  airframe and date that never had one. (porting 414Ret #843)
- **Targeting-pod era data** — introduction years and the CLSIDs that were missing.
  (porting 414Ret #871)
- **Self-documenting plugin options** — per-plugin description text with cleaned-up
  labels and units. (porting 414Ret #841)
- **The OPFOR aggressiveness roll was inverted** — a cautious setting made red
  bolder and vice versa. (porting 414Ret #789)
- **Weapon CLSID repairs** — broken ids fixed and coverage brought up to the current
  DCS patch. (porting 414Ret #826)
- **The early F-14A flew unarmed** — its payload was bound to the wrong `unitType`,
  so DCS silently dropped every store. (porting 414Ret #889)
- **Ship groups generate as task groups** — a group was N copies of one hull, so a
  carrier screen was four identical destroyers whatever the navy actually fielded.
  A slot now takes one type per position, drawn from the lead's own class family
  and capped at three types, so a screen mixes destroyers, frigates and a cruiser
  while a patrol boat never lands in a cruiser's slot. Naval layouts only; the buy
  menu still gives exactly the hull that was picked.
  ([#104](https://github.com/juanjux/dcs-retribution/pull/104), porting 414Ret #764)
- **Every generated mission is archived** — each turn wrote to one fixed path, so
  every Take off silently overwrote the mission just flown, and with it the evidence
  for anything that went wrong in it. Each mission is additionally copied to
  `Missions/Retribution Archive/<campaign>_turn<NN>_<timestamp>.miz`, self-pruning,
  with the fixed output path unchanged.
  ([#103](https://github.com/juanjux/dcs-retribution/pull/103), porting 414Ret #615)
- **GPS jamming** — a JDAM, JSOW, JASSM or SLAM-ER released against a target
  inside an enemy jamming bubble flies its normal profile and lands off the
  aimpoint, further off the deeper in. Laser, TV and anti-radiation weapons are
  unaffected, and killing the jammer restores accuracy on the next weapon in the
  same mission. The jammer is an ordinary bombable ground unit — any type whose
  data file carries a `gps_jamming` block — so it is bought and repaired like any
  other, and it is not a SEAD target: a real GPS jammer is L-band, invisible to
  RWR and un-homeable by a HARM. Off by default.
  ([#109](https://github.com/juanjux/dcs-retribution/pull/109), porting 414Ret #778)
- **Finite anti-ship magazines, and a staggered weapons release** — a fleet
  reloaded for free every turn, so sinking hulls was the only thing that reduced
  the volume. A warship group now carries a campaign stock of anti-ship missiles
  that never rearms, and a group that runs dry drops to return-fire rather than
  being disarmed. Optionally, ships spawn on return-fire and are released to
  weapons-free one group at a time, because a modern anti-ship missile out-ranges
  the theatre and an unstaggered fleet empties its tubes in the opening minute.
  Both off by default.
  ([#106](https://github.com/juanjux/dcs-retribution/pull/106), porting 414Ret #766)
- **The AI buys its better ground units more often** — the ground buy rolled
  uniformly over everything affordable of the right class, so a faction fielding a
  modern MBT and a gun truck bought as many of one as the other. The roll is
  weighted by price; a weighting, not a maximum, so the cheap end still appears.
  ([#105](https://github.com/juanjux/dcs-retribution/pull/105), porting the
  capability-weighted half of 414Ret #68)

## Queued

Planned, not started. Enough detail here to pick each one up cold.

- **IADS: a power generator keeps its own battery alive.** A SAM whose power line is cut
  goes dark. A battery that carries its own generator should stay up regardless, and only
  go dark when that generator is destroyed — it powers itself, it does not feed the
  neighbour. Five `class: Power` units are already modelled (Patriot EPP, two CurrentHill,
  LvS-103, the SAMP/T MGE) and all of them already live inside their own SAM's group, so
  the data is there. The catch is that this is not a Python-only change:
  `skynetiads-config.lua` resolves power sources with `StaticObject.getByName`, which
  returns nil for a vehicle, so the generators need their own array on the Lua side.
  Apply it only to sites already wired to a substation — otherwise a Patriot goes from
  "always powered" to "switched off by killing one truck", which is worse than today.
  `game/agent/docs/howtoplay.md` currently states the opposite and has to be corrected in
  the same change.
- **IADS: network state on the map.** Show which sites are autonomous or dark, on the
  health bar and the threat ring, instead of leaving the player to guess. The state is
  never persisted and never comes back from DCS, so it has to be derived from which nodes
  are still alive — which is exactly what Skynet itself looks at. Suppressing the ring is
  free. The trap: without also pushing the TGO when a power station dies, the map keeps
  drawing the stale ring until the campaign is reloaded.
- **[from 414Ret] Strikes timed behind their SEAD.** Packages are scheduled independently
  today, so nothing stops a strike entering a threat ring before the SEAD servicing it.

## Halted for Now

Work that was built and soak-tested but **parked** — pulled out of `master` and
`juanjux-dev` to keep them clean, with every branch preserved here so it can be
revived later.

### SYNTAX weapon mods (AARGM-ER, LRASM, JASSM-ER)

Optional-mod toggles in the New Game wizard that swapped a stock weapon for a
SYNTAX one: the AGM-88G AARGM-ER in place of the HARM in SEAD loadouts
([#65](https://github.com/juanjux/dcs-retribution/pull/65)), the AGM-158C LRASM
in place of the Harpoon ([#66](https://github.com/juanjux/dcs-retribution/pull/66)),
and the AGM-158B JASSM-ER in place of the JSOW-A
([#67](https://github.com/juanjux/dcs-retribution/pull/67)).
**Parked because the mods are not reliable enough** to build campaign balance on.
Removed from `master` and `juanjux-dev`; the branches are preserved.

### Electronic Warfare (EWAR "Jamming")

A dedicated **EWAR / "Jamming" flight task** for EW aircraft (EA-18G, EA-6B,
Su-34, Mi-8, plus emulated EC-130 Compass Call / Su-24MP / Tornado ECR variants),
built on upstream's `ewrj` jammer plugin: offensive radar suppression, a
defensive missile-deletion bubble, engine ECM, naval point-defense handling and a
launcher-jam missile kill — all tuned to *degrade* enemy air defenses, not
silence them.

**Why halted:** after a lot of in-game soak-testing, a *reliable and good* EWAR
turned out to be basically impossible without proper support from the DCS engine
itself. The available levers (scripted ROE, missile deletion, engine ECM) don't
scale consistently — e.g. a few jammers saturate a fleet's radar into total
silence, which is neither realistic nor fun. Parked until DCS exposes real EW
hooks.

Reverted from `master` and `juanjux-dev` (the upstream `ewrj` plugin base, off by
default, stays). Everything is preserved on these branches:

- **[`juanjux/ew_jamming_parked`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ew_jamming_parked)** — the complete pre-removal state (feature + all tuning + debugging); branch from here to revive it.
- [`juanjux/ewr`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ewr) (consolidated feature) · [`juanjux/ew_jamming`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ew_jamming) (original feature branch)
- Tuning: [`ew_attenuate_defensive_bubble`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ew_attenuate_defensive_bubble) · [`ew_arh_launcher_jam`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ew_arh_launcher_jam) · [`ew_sarh_modulate`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ew_sarh_modulate) · [`ew_ship_point_defense`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ew_ship_point_defense) · [`jamming_degrade_not_silence`](https://github.com/juanjux/dcs-retribution/tree/juanjux/jamming_degrade_not_silence) · [`jamming_degrade_returnfire`](https://github.com/juanjux/dcs-retribution/tree/juanjux/jamming_degrade_returnfire)
- Debug tooling: [`ew_harpoon_loggers`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ew_harpoon_loggers) (Harpoon leak-rate / ship-hit loggers)
- Removal: [`remove_ew_jamming`](https://github.com/juanjux/dcs-retribution/tree/juanjux/remove_ew_jamming) · [`remove_ew_dev_v2`](https://github.com/juanjux/dcs-retribution/tree/juanjux/remove_ew_dev_v2) · [`remove_ew_jamming_dev`](https://github.com/juanjux/dcs-retribution/tree/juanjux/remove_ew_jamming_dev) · [`ew_removal_howtoplay`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ew_removal_howtoplay)
- Pre-removal backups: [`backup/master-pre-ewremoval-20260630`](https://github.com/juanjux/dcs-retribution/tree/backup/master-pre-ewremoval-20260630) · [`backup/juanjux-dev-pre-ewremoval-20260630`](https://github.com/juanjux/dcs-retribution/tree/backup/juanjux-dev-pre-ewremoval-20260630)

> Saves that use EW units won't load on a build without this feature.

---

For installation and general usage, see the upstream
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution) documentation.
