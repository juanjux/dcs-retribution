# DCS Retribution — juanjux fork

A personal fork of [DCS Retribution](https://github.com/dcs-retribution/dcs-retribution)
that bundles a number of features and fixes which are not (yet) in upstream
Retribution. Some features and fixes are also adapted from the
[414Ret fork](https://github.com/bradyccox/414Ret).

## How development works here

Development happens **in this fork**. New work is opened as a
[Pull Request against this repository](https://github.com/juanjux/dcs-retribution/pulls),
targeting `master`, **not** against upstream — this keeps the upstream review
queue light and makes it easy for other forks to cherry-pick whatever they want.
Each PR describes the feature or fix it adds. Individual fixes may still be
offered upstream case by case.

## Branches

| Branch | Purpose |
| --- | --- |
| **`dev`** | A clean mirror of upstream `dcs-retribution/dev`. Pristine, untouched — the base everything is cut from. |
| **`master`** | The line you build. Every feature and fix lands here through a PR, after it has been tested. |

When upstream `dev` gets new commits they are occasionally pulled into `master`.

## Features not in upstream Retribution

Each item links to the fork PR that implements it. The authoritative, up-to-date
list is the [pull requests](https://github.com/juanjux/dcs-retribution/pulls?q=is%3Apr).

### Interface

- **The interface has been rebuilt.** Dialogs, lists and panels were redrawn to one
  visual language. Nothing about how the campaign plays changed.

  <img src="https://raw.githubusercontent.com/juanjux/dcs-retribution/juanjux/screenshots/airwing-redesign.png" width="760">

### IADS

- **Skynet comes from our own fork**,
  [juanjux/Skynet-IADS](https://github.com/juanjux/Skynet-IADS): upstream 3.3.0 with its
  HARM fixes, plus `ActMobile` and the four High Digit SAMs systems (S-400, S-300V4,
  SAMP/T, Pantsir-SM). The build is labelled `3.3.0-juanjux-fork` in `dcs.log`.
- **A performance pass on the Skynet script.** Indexed contact merging, HARM tracks
  rejected by distance before any geometry, values sampled once per instant, radar
  coverage built once per pair, and world events dispatched only to the elements that
  subscribed to them. Two bugs with it: a zero-speed contact aborted the whole HARM
  sweep, and the periodic maintenance that clears spent missiles and expires HARM tracks
  was switched off for point defences and every EWR.
- **The IADS update interval is a setting**, default 15 seconds instead of 5. The price
  of raising it is latency.
- **A radius for what Skynet manages.** Only what lies within a given distance of the
  front line, a package target or a carrier is coordinated; everything else still spawns
  and fights, forced to red alert, but never goes dark and never reacts to a HARM. The
  radius reaches radars only — command centres, comms towers and power stations always
  reach Skynet, and a site that stays keeps every dependency it has. Default 0, the
  whole map.
- **Stock SAMs play the SEAD game the modded ones already did.** Forty stock search and
  track radars get a 90% chance of noticing an inbound HARM and going dark for it, and
  wake at 120–130% of their own envelope instead of only once you are inside the kill
  zone. The "Adjust default SAM go-live range" setting still overrides them per system.
- **A battery with its own generator is not on the grid.** A Patriot's EPP-III or a
  SAMP/T's MGE keeps the site powered when the nearest substation is bombed; killing the
  generator itself puts it back on the grid. Read from the `class: Power` in the unit
  data, so a mod that ships a generator works the day it is registered.
- **A destroyed IADS building reads as destroyed, not as absent.** Nodes whose units were
  all dead were dropped from `skynet_nodes`, and Skynet treats a missing dependency as
  satisfied — so bombing a power station switched its SAMs back on, and destroying a
  coalition's last command centre handed it perfect command back.
- **A destroyed site keeps its place in the network, and its links on the map.** A site
  with nothing alive was dropped from the network, so the link whose power station died
  was the one link never drawn. Campaigns saved before this rebuild their network once on
  load.
- **A site with no power stays dark when it loses its comms.** Going autonomous under
  `AUTONOMOUS_STATE_DCS_AI` called `goLive()` unconditionally, so bombing the comms node
  of an unpowered site woke a battery the command centre was keeping dark.
- **IADS infrastructure can be rebuilt.** Comms towers, power stations and command
  centres get a flat rebuild cost (5M, 15M, 10M) and still earn nothing, so striking the
  network is an attrition loop rather than a one-off. The AI ranks them alongside its
  ammo depots.
  ([#97](https://github.com/juanjux/dcs-retribution/pull/97))
- **Autonomous and dark sites are told apart from working ones.** The state is derived
  from Skynet's own rules and published: a dark site draws no range rings and its health
  bar says why, network links are coloured by state, and the API carries `iads_state` /
  `iads_reason` / `iads_blind` on targets and threats and `state` / `state_reason` /
  `blind` on `/iads`, omitted whenever a site is working normally.
  ([#10](https://github.com/juanjux/dcs-retribution/pull/10))
- **Radar, missile battery and jamming site are one slot.** Buy any of the three where
  any one of them stands; the map symbol follows what is parked there, and a site that
  only watches draws its detection ring dashed in its faction's colour.
  ([#183](https://github.com/juanjux/dcs-retribution/pull/183))
- **The IADS configs resolve.** Thirty-nine buildings the campaign configs named had a
  trigger zone and no object placed, so bombing the infrastructure did nothing and some
  command centres never reached Skynet at all.
  ([#183](https://github.com/juanjux/dcs-retribution/pull/183))

### Kneeboards
- **Friendly-packages list** plus a **package-targets map** page.
  ([#11](https://github.com/juanjux/dcs-retribution/pull/11))
- **DEAD/SEAD target page** — one waypoint per target with an STPT column.
  ([#18](https://github.com/juanjux/dcs-retribution/pull/18))
- **COMM2 presets** mirrored from COMM1 on twin-radio aircraft (plus an
  F/A-18-family COMM1/COMM2 fix) and clearer auto-assigned **TACAN** codes.
  ([#12](https://github.com/juanjux/dcs-retribution/pull/12),
  [#20](https://github.com/juanjux/dcs-retribution/pull/20))
- The **Support Info** page spans several pages when a package has many flights, instead
  of silently pushing the AEW&C, tanker and JTAC tables off the bottom of one.
  ([#69](https://github.com/juanjux/dcs-retribution/pull/69))

### Missions, AI & tasking
- **An Escort or SEAD Escort with an "ahead" TOT offset reaches the target ahead of its
  package.** The DCS escort task is held back until the flight it protects reaches its
  ingress point, so the escort keeps its head start and still covers the attack and the
  way home.
  ([#220](https://github.com/juanjux/dcs-retribution/pull/220))
- **Refuelling that actually happens.** One setting instead of three per-task tanker
  options, and the fuel decides: a package's route is costed leg by leg against what each
  flight leaves the ground with, and a flight that will not make it gets a refuelling
  waypoint after the target plus a tanker request. The question is asked again when you
  edit the flight. The DCS task no longer carries the *"every unit at or above 20%
  fuel"* start condition that stopped a thirsty flight refuelling at all. A tanker orbits
  the waypoint itself, is not offered inside enemy air defences, is listed with the
  refuelling system it uses, and is on station ten minutes early for the campaign's
  configured duration.
  ([#211](https://github.com/juanjux/dcs-retribution/pull/211),
  [#213](https://github.com/juanjux/dcs-retribution/pull/213),
  [#214](https://github.com/juanjux/dcs-retribution/pull/214))
- **Live Pilots** (off by default) — a pilot holds a *rank* instead of a bare AI skill
  level and carries it into the mission, so the flight label reads `1stLt Pepito Perez`
  where DCS would leave `Pilot #2`. Ranks are named in each squadron's own service (31
  countries), generically, by the DCS skill names, or by five names you type in. DCS has
  five air skills rather than four; `game/dcs/skills.py` adds the missing bottom rung and
  owns the ladder.
  ([#129](https://github.com/juanjux/dcs-retribution/pull/129))
- **Live Pilots II: a rank has to be earned.** XP is paid per result — 500 an air kill,
  500 for coming home, 200 a vehicle, 300 a hull, buildings worth what they are worth —
  with an assist worth a quarter of a kill, thresholds doubling at every rung, and the
  coalition skill setting as a floor rather than a starting point. Rank decides whether a
  pilot walks away from a loss (one in five for a cadet, four in five for a squadron
  leader), and a loss that rank did not save gets one more throw at being **wounded
  rather than killed**: out of the roster for one to four turns, keeping his place on the
  books. The debriefing gains a Pilots box with promotions, recoveries, wounds and deaths.
  ([#134](https://github.com/juanjux/dcs-retribution/pull/134))
- **Live Pilots III: a pilot has a state of mind.** He carries **morale**, 0 to 100 from
  50, moved by what is already in the debriefing and drifting back a step each turn, with
  rank as armour. It decides what a sortie pays, the skill level he flies at (a rung
  better above 85, a rung worse below 15), what his flight will put up with (a lead below
  20 routes around threats, below 10 he turns for home), and his survival roll. At the
  bottom he refuses to fly and after three turns there he is gone. **Leave** answers
  that: a pilot asks, and a dialog after the debriefing lists the requests with the turns
  to grant. His Air Wing row names the band — Triumphant to Broken — and turns yellow,
  then red. Fifteen settings; old saves read as morale 50.
  ([#142](https://github.com/juanjux/dcs-retribution/pull/142))
- **Live Pilots IV: a pilot has an opinion of the man next to him.** Each pilot holds a
  **friendship** with each other pilot, 0 to 10 from 5, and it is **one-way**. It moves
  slowly between everyone at a base and faster in the air, and a quiet turn can never
  carry a pair past *Friendly*, so the levels that pay for anything are earned flying
  together. It changes what a mission pays, lifts a flight or package that reaches
  *Close* one skill level above its rank (weighted so what each man thinks of his lead
  counts double), makes the men who think well of him look harder when he goes down,
  holds him in his seat, and makes a death land on the men who were up there with him as
  many times over as they thought of him. Alongside it, **hardening**: a point for every
  turn spent Shaken or worse, never lost, which softens every morale hit and thickens his
  skin both ways. Every figure is a setting.
  ([#217](https://github.com/juanjux/dcs-retribution/pull/217))
- **Ranks, with a price.** What each rung costs in XP is set beside its name, and the
  morale bands are settings too.
  ([#174](https://github.com/juanjux/dcs-retribution/pull/174),
  [#179](https://github.com/juanjux/dcs-retribution/pull/179))
- **A squadron carries its own Max pilots** beside its Max size, instead of every
  squadron following the campaign-wide limit. It follows the setting until you move it.
- **Two morale rules re-weighed.** A wound is felt every turn the medics keep him rather
  than only the first three, and going without leave costs the same each turn rather than
  compounding.
- **Mission Log** (plugin, off by default) — a running commentary of what happens to your
  side while you fly: who shot down whom and with what, which targets went down, who
  ejected, who crashed. The generator seeds a unit-name → pilot roster, so messages name
  the pilot and mod aircraft come out right without a table of their own. Each message
  goes only to the coalition it is news for, every category has its own toggle, and
  interceptions are polled because DCS fires no event for them.
  ([#120](https://github.com/juanjux/dcs-retribution/pull/120))
- **The LLM can see and choose its pilots, and read every setting.**
  `GET /squadrons/{id}/pilots` is the Air Wing roster, `GET /flights/{id}/crew` shows one
  flight's seats and who is free, and `POST /flights/crew` seats a named pilot or empties
  a seat. `/settings` gains `all_settings`: every box on the settings pages with its
  label, value and explanation.
  ([#139](https://github.com/juanjux/dcs-retribution/pull/139))
- **The LLM is warned when it sends a CAS flight higher than it will shoot from.** The
  edit is applied regardless.
  ([#136](https://github.com/juanjux/dcs-retribution/pull/136))
- **A TARCAP gets its own on-station time**, instead of reading a doctrine field no
  setting ever reached. Defaults to the 30 minutes it always was, and still gives way to
  the escorted mission.
  ([#137](https://github.com/juanjux/dcs-retribution/pull/137))
- **Turn times from the sun** — the four turn slots are derived from the theater's
  latitude and the campaign date rather than one fixed window per map, so a December dawn
  turn no longer starts in the pitch dark. North of the arctic circle the slots hang off
  solar noon and stay dark. A theater keeps its old table with `daytime_mode: table`.
  ([#113](https://github.com/juanjux/dcs-retribution/pull/113))
- **ATMOS-X live weather** — with the ATMOS-X pack selected, the turn's weather can be a
  real METAR observation fetched through the ATMOS-X CLI, for a station picked
  automatically or set by ICAO. Fetched when the turn is built, so kneeboards, the active
  runway and the carrier's course into wind all match.
  ([#101](https://github.com/juanjux/dcs-retribution/pull/101))
- **Custom cloud preset packs** — a campaign setting that makes a community cloud-preset
  mod's presets available to the generator: Bandit's Cloud Presets, Weather 2.0 or
  ATMOS-X, one at a time since the packs reuse the same preset keys.
  ([#53](https://github.com/juanjux/dcs-retribution/pull/53))
- **Smart Threat Reaction** — a plugin that keeps AI aircraft at Passive Defense and
  switches only the flight a missile is actually guiding on to Evade Fire, so one SAM
  launch no longer sends every nearby package defensive.
  ([#63](https://github.com/juanjux/dcs-retribution/pull/63))
- **Campaign Doctrine: "non-combat (crash) air losses don't count"** — AI crashes and
  collisions DCS credits to no weapon no longer deplete a squadron or kill the pilot.
  ([#1](https://github.com/juanjux/dcs-retribution/pull/1))
- **Best standoff/PGM loadouts for AI DEAD flights**, per airframe.
  ([#6](https://github.com/juanjux/dcs-retribution/pull/6))
- **Realistic helicopter range** — carrier-capable transport helos (CH-53E, CH-47D/F,
  SH-60B, UH-60A/L, UH-1H) get their real combat radius instead of the 50 nm helicopter
  default.
  ([#64](https://github.com/juanjux/dcs-retribution/pull/64))
- **One-way air assault ("remain at destination")** — a helicopter-only option: the helos
  land at the objective and do not return, so the assault uses their full ferry range. At
  turn end the survivors redeploy there if you capture the base, otherwise they are lost.
  ([#64](https://github.com/juanjux/dcs-retribution/pull/64))
- **Manual DEAD tasking** — non-DEAD-role aircraft can fly DEAD as a secondary task.
  ([#4](https://github.com/juanjux/dcs-retribution/pull/4))
- **Ferry flights may return fire.** A relocating squadron flew on Weapon Hold, so a
  transit across contested airspace was a free kill.
  ([#99](https://github.com/juanjux/dcs-retribution/pull/99))
- **Automated ground-object / building repair** — the HQ repairs damaged SAM sites,
  vehicle groups and buildings each turn, with tunable budgets and priorities, and the
  turn panel reports what each side finished and what is still in progress.
  ([#29](https://github.com/juanjux/dcs-retribution/pull/29),
  [#43](https://github.com/juanjux/dcs-retribution/pull/43))
- **Ignore parking space at airbases** — airbases hold as many aircraft as you can pay
  for, whatever their ramp size. Carriers and FOBs are unaffected.
  ([#184](https://github.com/juanjux/dcs-retribution/pull/184))
- **Set loadout as default** — a named payload can be made the default for an aircraft
  and mission type, so new flights start with it. Remembered by name; no payload is
  renamed or overwritten.
  ([#49](https://github.com/juanjux/dcs-retribution/pull/49),
  [#51](https://github.com/juanjux/dcs-retribution/pull/51))
- **A fuel estimate for the plan**, beside the route total and the per-leg distances:
  taxi, the legs at their own climb/cruise/combat rates, the landing reserve and a
  margin, against what the flight carries. Only 24 aircraft have measured consumption
  figures; the rest are estimated from their capacity over a nominal range for their
  kind, leaning high.
  ([#190](https://github.com/juanjux/dcs-retribution/pull/190),
  [#189](https://github.com/juanjux/dcs-retribution/pull/189),
  [#191](https://github.com/juanjux/dcs-retribution/pull/191))
- **The debriefing is kept in the save**, so it can be reopened from the Misc bar after
  the session that produced it. 1.6 KB of a 12 MB campaign.
- **Money cheat for both coalitions** (OWNFOR + OPFOR).
  ([#3](https://github.com/juanjux/dcs-retribution/pull/3))
- **Air Wing cheat** — per-squadron aircraft count with free +/- controls, for testing
  mod aircraft without spending money.
  ([#41](https://github.com/juanjux/dcs-retribution/pull/41))

### Campaigns
- **Battle for Area 51: one red IADS instead of three, and a power station for blue.**
  Red's west, central and east groups shared no comms node, so the map drew three
  networks a few miles apart; the comms are cross-linked and the power stations left
  local, so each one still blacks out its own cluster. Blue had no power station at all
  and now has one at the Creech industrial area, feeding both Creech SAMs, the Hawk
  half-way to Nellis and the command centre.
- **Syria — Invasion of the Canary Islands 2030**, with the **Spain 2030** and
  **Morocco 2030** factions. A rework of NoGoodNews' original: both sides fly what they
  are expected to field by 2030, each Spanish wing carries its own livery, and both
  navies are built from real hulls with pinned compositions. Air defences are about a
  third lighter than the original, the IADS is fully wired, and every base on a front has
  a motorpool holding its undeployed armour as a bombable target.
  ([#98](https://github.com/juanjux/dcs-retribution/pull/98))
- **GPS jamming in every modern campaign.** One site apiece, on the enemy early-warning
  radar whose bubble covers the most of its own air defences. Thirty-eight campaigns.
  ([#183](https://github.com/juanjux/dcs-retribution/pull/183))

### LLM-controlled OPFOR (REST API + MCP)
- **An external LLM can play the enemy commander.** A REST API and an MCP server expose a
  token-frugal turn context (forces, targets, threats, economy, naval, motorpools, runway
  states, plus an optional rendered map image) and full player parity to act on it:
  packages and flights, buying and selling, front-line stances, squadron relocation,
  fleet movement, repairs and rebuilds. The LLM gets its own briefing at `/start` and
  `/howtoplay`. Lives on the
  [`experiment-mcp`](https://github.com/juanjux/dcs-retribution/tree/experiment-mcp)
  branch (and master); not intended for upstream.

### Modding & data
- **F-15EX Eagle II, F-15C EG (Golden Eagle) and Eurofighter Typhoon** mod aircraft.
  ([#31](https://github.com/juanjux/dcs-retribution/pull/31),
  [#32](https://github.com/juanjux/dcs-retribution/pull/32),
  [#33](https://github.com/juanjux/dcs-retribution/pull/33))
- **High Digit SAMs updated to 2.1.0.** Adds the **SAMP/T battery** (Aster 30 at
  120/150/200 km, ARABEL fire control, Ground Fire 300 search radar) and the **SA-7/SA-7b
  Strela-2 MANPADS**, which go to six 1970s-80s factions that fielded no MANPADS at all,
  and retires what the mod dropped. A new test walks every preset and fails on any unit
  type DCS cannot resolve, since those are discarded in silence.
  ([#96](https://github.com/juanjux/dcs-retribution/pull/96))
- **High Digit SAMs Ultimate Compilation, as a second selectable build.** The two builds
  cannot both be installed, so the New Game wizard offers them as mutually exclusive
  choices and a faction only sees the presets its chosen build ships. Campaign authors
  have to wire the new sites in themselves.
  (branch [`juanjux/hds_2_1_0_and_ultimate`](https://github.com/juanjux/dcs-retribution/tree/juanjux/hds_2_1_0_and_ultimate),
  upstream [#956](https://github.com/dcs-retribution/dcs-retribution/pull/956))
- **CurrentHill China pack synced to 1.1.6** — a version-note sync; 1.1.4→1.1.6 added and
  removed no units.
  (branch [`juanjux/ch_china_1.1.6`](https://github.com/juanjux/dcs-retribution/tree/juanjux/ch_china_1.1.6))
- **Your payload library is backed up on startup.** DCS keeps your custom loadouts as one
  `.lua` per airframe under `MissionEditor/UnitPayloads` and nothing else holds a copy —
  not the save, not the generated `.miz`. The folder is snapshotted before anything can
  write to it, keeping the last ten under `Retribution/PayloadBackups`.
  ([#102](https://github.com/juanjux/dcs-retribution/pull/102))

### Fixes

- **A squadron with nobody willing to fly read as fully manned.** The squadron dialog and
  the Air Wing row counted pilots who refuse to fly as available; both go through
  `Squadron.fit_for_duty` now, and the refusers are named beside the wounded.
- **A pilot on leave held no place, so squadrons grew past their own limit.** A slot is
  now held by anyone still on the books; only the dead, the deserted and the discharged
  free one. A squadron already over its limit recruits nobody and comes back down as men
  are lost.
- **The same pilot could fly two missions in one turn.** Clearing a roster handed its crew
  back to the squadron and then went on holding them.
  ([#138](https://github.com/juanjux/dcs-retribution/pull/138))
- **Saves still carried pilots who were flying and available at once.** A migration step
  takes anyone in a cockpit out of the pool on load.
  ([#141](https://github.com/juanjux/dcs-retribution/pull/141))
- **Bombing the parking killed the pilots who were not in the aircraft.** Reserves on the
  apron are given a stand-in flight so the debriefing can account for the airframe, and
  that flight claimed a real pilot. The airframe is still lost; the pilot is not.
  ([#134](https://github.com/juanjux/dcs-retribution/pull/134))
- **Switching Live Pilots on demoted one coalition and not the other.** Starting the
  ladder wrote Cadet into the difficulty page, which carries into the next campaign. The
  floor is computed now instead of stored.
  ([#134](https://github.com/juanjux/dcs-retribution/pull/134))
- **Turning Live Pilots off and back on left its settings dead.** The master switch only
  ever disabled, and could not reach the pages it did not own.
  ([#174](https://github.com/juanjux/dcs-retribution/pull/174),
  [#179](https://github.com/juanjux/dcs-retribution/pull/179))
- **Player pilots were playing the morale game.** Morale is for the AI pilots.
  ([#173](https://github.com/juanjux/dcs-retribution/pull/173))
- **The debriefing's morale section listed everyone who flew.** It reported any movement
  past a fixed size, and flying the mission is exactly that size. It reports a change of
  state now.
- **A flight sent AHEAD of its package arrived behind it.** The package TOT was worked out
  from the slowest flight's transit alone, ignoring each flight's own offset, so the plan
  was built backwards from a time it could not reach and the clamp turned the head start
  into an equal delay. The earliest reachable package TOT accounts for the offsets, and
  changing one slides the package later when it has to.
- **A package with an impossible TOT could hold for the whole mission.** The hold point
  emitted its release timer without a floor, and DCS never fires a trigger scheduled for
  a negative time. Clamped to mission start.
  ([#100](https://github.com/juanjux/dcs-retribution/pull/100))
- **A CAP guarding its own base could vanish the instant the mission started.** DCS runs
  the last waypoint's tasks immediately for an air-started flight whose total route is
  short enough, and for AI that waypoint carries the despawn script. Patrol routes are
  lengthened away from the enemy until they reach 60 nm, so the threat-facing end and the
  station stay put.
  (branch [`juanjux/min-patrol-route`](https://github.com/juanjux/dcs-retribution/tree/juanjux/min-patrol-route))
- **Take Off crashed on any flight with a racetrack.** Five places still read the removed
  EW jamming plugin's options, and the check for whether it was there sat after the read.
  ([#194](https://github.com/juanjux/dcs-retribution/pull/194))
- **Take Off died with "Duplicate convoy unit", stranding the campaign** — the name
  counter reset each turn onto a convoy still in transit.
  ([#93](https://github.com/juanjux/dcs-retribution/pull/93))
- **The recurring in-mission freeze** (~100 s stalls repeating until mission end, runaway
  RAM and the 0-byte `state.json`) — scenery objects report a numeric name, and one
  scenery death made the state encoder build a multi-million-hole array on the sim
  thread. Scenery deaths are ignored by the state export.
  ([#80](https://github.com/juanjux/dcs-retribution/pull/80))
- **Some building objectives could never be recorded as destroyed.** An objective is
  credited by a `MapObjectIsDead` trigger over its zone, and many of those zones hold
  scenery that cannot be destroyed at all. Deaths are matched to the nearest objective by
  position within 30 m instead, and the triggers are gone.
  ([`b7cbd73`](https://github.com/juanjux/dcs-retribution/commit/b7cbd73df),
  [`afff790`](https://github.com/juanjux/dcs-retribution/commit/afff790e0))
- **A Strike put every iron bomb on a single aimpoint.** The dumb-bomb task aimed at the
  objective's centroid and sized its carpet from the mean distance to the targets rather
  than their spread. Heavy bombers now carpet the real extent in one pass; everything
  else re-attacks with one aimpoint per target and the load split between them.
  ([`1209839`](https://github.com/juanjux/dcs-retribution/commit/120983924))
- **Scud and ATACMS sites cratered empty fields.** A missile site fired at the enemy
  control point's map coordinate, displaced by up to 2500 m at random. They now aim at
  live, immobile ground objects at the target base, with range measured to the aimpoint,
  minimum ranges respected, and the top 15% of the envelope off limits.
  ([#128](https://github.com/juanjux/dcs-retribution/pull/128))
- **Air-assault troops stood still instead of taking the base.** CTLD walked unloaded
  troops to their waypoint and left them there, so one surviving vehicle blocked the
  capture indefinitely. Dropped troops and vehicles now advance on the nearest enemy
  ground unit inside the capture radius. New CTLD option, on by default.
  ([#85](https://github.com/juanjux/dcs-retribution/pull/85))
- **Air-assault ingress no longer zig-zags.** The join leg is anchored to the package's
  ingress point rather than the initial point.
  ([#9](https://github.com/juanjux/dcs-retribution/pull/9), upstream
  [#804](https://github.com/dcs-retribution/dcs-retribution/pull/804))
- **Front-line ground units never fought** — three stacked causes: defenders held position
  waiting for the enemy's first CAS package, a negative hold duration wrapped to ~24 h,
  and the FLOT took its alarm state from a mislabelled SAM toggle. Defenders engage from
  minute one; the toggle is relabelled and no longer touches the FLOT.
  ([#79](https://github.com/juanjux/dcs-retribution/pull/79))
- **Transferring an army mid-turn made it vanish from the ground war.** The ground war was
  planned once at the start of the turn and cached, so anything moved afterwards was
  deployed from a stale plan; and units waiting for a lift that did not exist were debited
  on order rather than on departure. Planning happens at mission generation now, and
  pending units are deployable, defending and counted until they actually leave.
  ([#133](https://github.com/juanjux/dcs-retribution/pull/133))
- **A dry run grounded a squadron for the turn.** `plan_mission` claims aircraft flight by
  flight and releases them when it scrubs a mission, but anything that *raised* in between
  walked out with the claims standing. Fixed at the claim, so planning is atomic for every
  caller.
  ([#131](https://github.com/juanjux/dcs-retribution/pull/131))
- **The Su-25 was planned to fight from a height it will not shoot from.** No aircraft in
  the fork declared a combat altitude, so both Frogfoots fell back to an estimate from
  their top speed and were tasked above the altitude the AI will attack from.
  ([#135](https://github.com/juanjux/dcs-retribution/pull/135))
- **The Su-25 flew DEAD carrying only weapons it cannot guide.** All six attack pylons
  were laser-guided and the plain Frogfoot has no designator, so the loadout was stripped
  and the aircraft flew unarmed. RBK-250 with PTAB-2.5M instead.
  ([#130](https://github.com/juanjux/dcs-retribution/pull/130))
- **Su-25s flew close air support with weapons they cannot guide.** The strip that exists
  for this checks `WeaponType.LGB`, and the whole Soviet laser family was typed
  `UNKNOWN`. S-25L, Kh-25ML, Kh-29L and the laser KABs now match; dual GPS/laser weapons
  are left alone, and the Su-25T gains its Klen-PS.
  ([#125](https://github.com/juanjux/dcs-retribution/pull/125))
- **The A-6E dropped iron instead of its laser-guided bombs, always.** Its TRAM turret is
  an internal designator and nothing declared it, so the planner swapped every GBU out at
  every date.
  ([`5545351`](https://github.com/juanjux/dcs-retribution/commit/55453512e))
- **Stores that no weapon file claimed slipped past their own introduction date.** The
  A-6E's TALD MER clsids, the AN/ALQ-167 and the Hornet's fourth AIM-7P clsid read as
  unknown stores: no weapon type for planning and no year.
  ([`309b39c`](https://github.com/juanjux/dcs-retribution/commit/309b39c24),
  [`06b7955`](https://github.com/juanjux/dcs-retribution/commit/06b7955e1))
- **A Patriot battery reported no threat at all.** The AN/MPQ-53 — the original Patriot
  array — was missing from `TRACK_RADARS`, and a launcher only counts when a paired
  tracker is alive.
  ([#126](https://github.com/juanjux/dcs-retribution/pull/126))
- **Factions with no early-warning radar fielded a SAM's acquisition radar as one.**
  Ukraine, Georgia, Morocco, France, Argentina, Peru and Iran were putting up a Patriot
  STR or a Hawk SR where a national radar belonged.
  ([#187](https://github.com/juanjux/dcs-retribution/pull/187))
- **A campaign's `ground_forces` pin was ignored on early-warning radar markers**, so
  every GPS jamming site any campaign had declared was silently an ordinary radar.
  ([#183](https://github.com/juanjux/dcs-retribution/pull/183))
- **A pinned site generated without its point defence.** The fill searched artillery,
  frontline and logistics units while air defence lives in its own list.
  ([#183](https://github.com/juanjux/dcs-retribution/pull/183))
- **A GPS jamming site drew the wrong circle** — its point defence's reach instead of the
  jamming bubble, and solid rather than dashed.
  ([#185](https://github.com/juanjux/dcs-retribution/pull/185))
- **SA-10B/S-300PS sites never spawned and were immortal.** High Digit SAMs 2.1.0 no
  longer ships the S-300PS family, DCS silently drops unit types it cannot resolve, and
  Retribution kept the site alive with its threat ring up. Now the stock S-300PS.
  ([#96](https://github.com/juanjux/dcs-retribution/pull/96))
- **Spanish AAA sites were empty.** The faction listed the WWII 2 cm Flak 38, which needs
  the WWII Assets Pack. It now fields the Flakpanzer Gepard.
  ([#95](https://github.com/juanjux/dcs-retribution/pull/95))
- **Blufor Late Cold War (80s) had no beyond-visual-range fighter.** Its only Viper was
  the Block 50, which DCS gives no Sparrow. The faction now also fields the F-16A.
  ([`a603bfd`](https://github.com/juanjux/dcs-retribution/commit/a603bfd86))
- **The AH-1W had no anti-armour weapon in a 1983 campaign.** DCS models only the BGM-71D,
  whose IOC is 1985; the faction overrides the weapon's year, as the weapon file itself
  suggests.
  ([`8ea3214`](https://github.com/juanjux/dcs-retribution/commit/8ea3214c7))
- **The naval magazines plugin never loaded.** Plugin options were written into the
  mission unquoted, and an unquoted `3M24` is a malformed Lua number, so DCS threw a
  syntax error over the whole configuration block.
  ([`5b73214`](https://github.com/juanjux/dcs-retribution/commit/5b73214e7))
- **Three Splash Damage options had never done anything.** Two called a `getAGL()` that is
  defined nowhere and the third was written to a misspelled key. All three came in with
  upstream's 3.4.2 update.
  ([#177](https://github.com/juanjux/dcs-retribution/pull/177))
- **A plugin could not ask the player for a word.** The plugin options dialog drew no
  control at all for a string setting.
- **A plugin's settings live with the plugin.** GPS jamming, cruise missile strikes and
  naval magazines each had a switch in Mission Generator that did nothing unless the
  plugin was on as well. Old campaigns keep what they had set.
  ([#186](https://github.com/juanjux/dcs-retribution/pull/186))
- **The pilot roster went missing whenever a second campaign was started**, so every
  Mission Log message named an aircraft with nobody flying it. The plugin manager is a
  class-level singleton holding whatever settings it was last loaded with.
  ([#124](https://github.com/juanjux/dcs-retribution/pull/124))
- **The Mission Log never showed our own launches, and claimed interceptions that were not
  happening.** A launch is now also reported to the shooter, and beyond 40 nm a patrol
  handed a contact reads "holds" rather than "is moving to intercept".
  ([#123](https://github.com/juanjux/dcs-retribution/pull/123))
- **`/prev_turns?n=1` answered with the turn you are sitting in**, because the turn being
  planned gets a stats entry the moment it starts.
  ([#127](https://github.com/juanjux/dcs-retribution/pull/127))
- **Neutral FARPs were invisible on the map.** The "destroyed, non-repairable" flag was
  read from whichever ground object is flagged `is_control_point`, on the assumption that
  only a carrier has one — a FOB has one too. Gated on `is_fleet` now.
  ([#119](https://github.com/juanjux/dcs-retribution/pull/119))
- **A bombed-out motorpool showed on the map as a permanent loss.** It is only a view of
  the base's undeployed armor, so procuring ground units refills it.
  ([`81fb0d4`](https://github.com/juanjux/dcs-retribution/commit/81fb0d4d8))
- **A refused purchase says why** — short of money, out of parking, or at the squadron's
  cap — instead of one message for three problems. The LLM reads the same string.
  ([#87](https://github.com/juanjux/dcs-retribution/pull/87))
- **A faction edited mid-campaign now reaches the buy menus.** Only a preset-group change
  triggered a rebuild of the coalition's forces, so adding a unit changed nothing you
  could buy.
  ([#110](https://github.com/juanjux/dcs-retribution/pull/110))
- **Three errors in the fuel figures.** Adding or removing a drop tank did not move the
  total, the estimate took no account of altitude, and it charged the join and split legs
  at the combat rate.
  ([#192](https://github.com/juanjux/dcs-retribution/pull/192))
- **"Apply to all" skipped every AGL waypoint**, which froze a helicopter's whole flight
  plan and most of a low-level one. It goes by waypoint type now.
  ([#193](https://github.com/juanjux/dcs-retribution/pull/193))
- **The settings dialog took a couple of seconds and flashed white windows first.** A
  group box added to a layout not yet installed on a widget has no parent, and in Qt a
  parentless widget shown is a top-level window; and the dialog raised all seven pages to
  show one. Pages are built the first time they are selected.
  ([#129](https://github.com/juanjux/dcs-retribution/pull/129))
- **Native dialogs again.** The file, colour and font pickers were switched to Qt's own
  because a native one opened over the live map deadlocked the app — the same synchronous
  path the ANGLE setting removes. Qt is on 6.11.2.
  ([#188](https://github.com/juanjux/dcs-retribution/pull/188))
- **Escorts of an AWACS/tanker hold on the protected flight's racetrack** instead of a
  far-away point, so they actually protect it.
  ([#42](https://github.com/juanjux/dcs-retribution/pull/42))
- Bumped PySide6/Qt to 6.8.3, which switches acceleration to D3D11 and fixes some OpenGL
  hangs. ([#52](https://github.com/juanjux/dcs-retribution/pull/52))
- Qt non-native dialogs avoid a QtWebEngine file-dialog deadlock.
  ([#17](https://github.com/juanjux/dcs-retribution/pull/17))
- Robust payload handling — unparseable payload files are skipped; loadouts are written
  atomically. ([#21](https://github.com/juanjux/dcs-retribution/pull/21))
- Player ground-start flights no longer spawn in the air.
  ([#19](https://github.com/juanjux/dcs-retribution/pull/19))
- The sell-aircraft exploit that corrupted squadron counts is fixed.
  ([#5](https://github.com/juanjux/dcs-retribution/pull/5))
- Kneeboard waypoint numbering is correct for in-air-start flights.
  ([#14](https://github.com/juanjux/dcs-retribution/pull/14))

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
- **CurrentHill Iran pack** — Shahed-136, IRGCN fast-attack craft and a
  `[CH] Iran 2020` faction. Upstream now ships the Sweden, China, Russia, USA, UK
  and Ukraine CurrentHill packs; Iran is the one it does not.
- Selected crash fixes (flight-exit, AWACS/tanker orbit deconfliction, malformed
  mod payloads).
- **Escorts can defend themselves before the JOIN point** — an escort was generated at an
  ROE that only permits engaging *designated* targets, and the task that designates them
  attaches at JOIN. Escorts now spawn able to return fire and escalate at JOIN.
- **Kills on scenery objectives inside culled regions are recorded.**
- **TIC: a combatant killed mid-move no longer crashes the scheduler.**
- **A patrol's orbit is charged to its fuel** — the on-station leg is scheduled by time
  but its fuel was billed as the straight line between the racetrack ends, so a 45-minute
  CAP was undercharged about fivefold.
- **Coastal batteries can engage ships** — land-based anti-ship sites fire on their own at
  hulls in range, the way fleets do. Off by default (a mod battery firing anti-ship
  missiles has crashed DCS).
- **DEAD reachability gate** — the planner no longer marks a SAM "cleared" when the
  assigned flight cannot actually reach it.
  ([#37](https://github.com/juanjux/dcs-retribution/pull/37), porting 414Ret #83)
- **Weapons coverage refresh** — more modern PGMs and air-to-air missiles across
  factions, without the era date-gating (our introduction years are kept).
  ([#35](https://github.com/juanjux/dcs-retribution/pull/35), porting 414Ret #82)
- **Player despawns aren't combat losses** — leaving an aircraft mid-mission no
  longer depletes your squadron in the debrief.
  ([#34](https://github.com/juanjux/dcs-retribution/pull/34), porting 414Ret #64)
- **Two guidance radars per SAM site** — every layout fielded exactly one engagement
  radar, so a single anti-radiation missile was a functional site kill. The Track Radar
  slot doubles across the generic layouts, SA-2, SA-3, SA-5, S-300, HQ-22, S-350, the
  mixed SA-2/SA-3 site, the reinforced SA-6, NASAMS-3 and Sky Sabre, with the second
  position 45-121 m from the first. (porting 414Ret #582)
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
- **Ship groups generate as task groups** — a group was N copies of one hull, so a carrier
  screen was four identical destroyers. A slot now takes one type per position, drawn from
  the lead's own class family and capped at three types. Naval layouts only; the buy menu
  still gives exactly the hull that was picked.
  ([#104](https://github.com/juanjux/dcs-retribution/pull/104), porting 414Ret #764)
- **Every generated mission is archived** to
  `Missions/Retribution Archive/<campaign>_turn<NN>_<timestamp>.miz`, self-pruning, with
  the fixed output path unchanged. Each turn used to overwrite the mission just flown.
  ([#103](https://github.com/juanjux/dcs-retribution/pull/103), porting 414Ret #615)
- **GPS jamming** — a JDAM, JSOW, JASSM or SLAM-ER released against a target inside an
  enemy jamming bubble lands off the aimpoint, further off the deeper in. Laser, TV and
  anti-radiation weapons are unaffected, and killing the jammer restores accuracy on the
  next weapon in the same mission. The jammer is an ordinary bombable ground unit and is
  not a SEAD target. Off by default.
  ([#109](https://github.com/juanjux/dcs-retribution/pull/109), porting 414Ret #778)
- **Finite anti-ship magazines, and a staggered weapons release** — a warship group
  carries a campaign stock of anti-ship missiles that never rearms, and a group that runs
  dry drops to return-fire. Optionally, ships spawn on return-fire and are released to
  weapons-free one group at a time. Both off by default.
  ([#106](https://github.com/juanjux/dcs-retribution/pull/106), porting 414Ret #766)
- **The AI buys its better ground units more often** — the ground buy rolled uniformly
  over everything affordable of the right class. The roll is weighted by price; a
  weighting, not a maximum, so the cheap end still appears.
  ([#105](https://github.com/juanjux/dcs-retribution/pull/105), porting the
  capability-weighted half of 414Ret #68)

## Removed from upstream

- **Fast forward.** It never worked well enough to be worth the machinery. Take Off hands
  DCS the mission at the time it was planned for.
  ([#176](https://github.com/juanjux/dcs-retribution/pull/176))
- **Four plugins.** EWRS is the 2016 script BigEye EWR was rewritten from; Mbot's Call
  Artillery only ever answered a player flying Armed Recon, while Carsten's answers
  anyone in range; the C-130 cargo script is for a mod we do not support; and the EW
  Jammer script cannot model jamming honestly without engine support.
  ([#175](https://github.com/juanjux/dcs-retribution/pull/175))
- **DCS: Pretense support.** A one-way export into a second, parallel game that never
  comes back to the Retribution campaign — ~5,400 lines of Python plus 590 KB of
  third-party Lua, carried through every upstream sync, for a project that is no longer
  maintained on either side. Gone with it: `game/pretense/`, the plugin resources, the
  toolbar actions, the settings page, `FlightType.PRETENSE_CARGO` and the four `*_full`
  campaigns tuned for it.

  **Saves still load.** `FlightType` maps the old `"Cargo Transport"` value onto
  `TRANSPORT`.

## Queued

Planned, not started. Enough detail here to pick each one up cold.

- **[from 414Ret] Strikes timed behind their SEAD.** Packages are scheduled independently
  today, so nothing stops a strike entering a threat ring before the SEAD servicing it.

## Halted for Now

Work that was built and soak-tested but **parked** — pulled out of `master` and
`juanjux-dev` to keep them clean, with every branch preserved here so it can be
revived later.

### Mission chronicle

An account of the mission in prose, from a button in the debriefing and as a `.md` beside
the archived `.miz`. Parked after reading one: with fixed templates it comes out
repetitive, and the Mission Log already tells you everything it does. The code has been
taken back out; the event recording it fed on still lands in `state.json`, so reviving it
means writing a better renderer against that timeline.
([#121](https://github.com/juanjux/dcs-retribution/pull/121))

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

A dedicated **EWAR / "Jamming" flight task** for EW aircraft (EA-18G, EA-6B, Su-34, Mi-8,
plus emulated EC-130 Compass Call / Su-24MP / Tornado ECR variants), built on upstream's
`ewrj` jammer plugin: offensive radar suppression, a defensive missile-deletion bubble,
engine ECM, naval point-defense handling and a launcher-jam missile kill.

**Why halted:** a reliable EWAR is not possible without proper support from the DCS
engine. The available levers (scripted ROE, missile deletion, engine ECM) do not scale
consistently — a few jammers saturate a fleet's radar into total silence. Parked until
DCS exposes real EW hooks.

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
