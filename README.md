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

### Map & UI
- **The interface has been rebuilt.** The Air Wing list, the squadron dialog, the ATO
  package and flight lists, the event log, the settings dialog, the command bar above the
  map and the flight dialog were all redrawn to one vocabulary: a task chip in a fixed
  colour family, the thing you came to read as the only large text, figures and times in
  mono so they line up down a column, and amber reserved for the one thing in a row that
  wants a decision. Dialogs remember the size you give them and open once rather than ten
  times. Nothing about how the campaign plays changed -- same fields, same signals, same
  validations, only where they live and how they read.
  ([design by Claude Design](https://claude.ai/))

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
- **A site cut off from its network stops looking like a live one.** An autonomous SAM
  engages only what its own radar finds, and a dark one never brings its radar up at all,
  but both drew the same confident threat ring as a fully networked battery. **The health
  bar** carries it: violet when the site is autonomous, grey when it is dark, with the
  reason in the tooltip — "No power: its substation is down and it carries no generator".
  A dark site draws **no range rings at all**, because it will neither see nor shoot for
  the whole mission; an autonomous one keeps its rings exactly as they are, since it does
  still shoot. Nothing is recoloured or dashed out there: a dashed ring already means a
  GPS jamming bubble. A battery whose substation is down but which runs on its own
  generator says so and **names the vehicle**, because bombing that one truck is how the
  other side switches it off. A destroyed site is left alone entirely: it keeps its own
  bar and whatever rings its surviving point defence has, which is a live threat.
  The state is derived, not measured: DCS never reports it, so the rules are lifted
  from the plugin function by function — `goLive()` refuses without power,
  `genericCheckOneObjectIsAlive` reads an empty dependency list as "fine",
  `setToCorrectAutonomousState` needs a live parent radar that covers the site, and
  `buildRadarCoverage` decides that by range. The same three fields ride the API
  (`iads_state` / `iads_reason` / `iads_blind` on targets and threats, `state` /
  `state_reason` / `blind` on `/iads`), omitted whenever a site is working normally, so
  a planner that sees one knows it has already broken something.
- **A battery with its own generator is not on the grid.** A Patriot deploys with an
  EPP-III and a SAMP/T with an MGE, so bombing whichever substation happened to be
  nearest should do nothing to it — and it was switching the battery off. Read from the
  `class: Power` the unit data already carries, so a mod that ships a generator works the
  day it is registered. No Lua change was needed after all: Skynet reads an empty power
  list as "powered", so leaving the connection out of the table *is* the feature. Kill
  the generator itself and the site is back on the grid next mission.
- **The Air Wing Configuration dialog was redrawn.** Three panes, one per question:
  what this coalition flies and how much of it, what each squadron is allowed to be
  given and where it is based, and — the one the old form did not have at all — whether
  it all fits. Parking was a grey line at the bottom of one group box, and going over it
  was the commonest mistake made in this window; now every base is on screen and turns
  red the moment you bump a max size, with the header saying "1 over" before you look.
  Squadron boxes became collapsible cards whose closed header answers what you go
  looking for, one open at a time. The twenty-row *Mission Type / Auto-Assign* grid is
  chips grouped into the three task families the rest of the app already colours by,
  showing only what the airframe can fly and naming what it cannot; the primary task is
  marked and cannot be switched off, which closes a trap the old form left open. And the
  two situations the window opens in — composing an air force before a campaign, and
  reaching into a running one with the cheat on — are now told apart by a blue or amber
  header, an amber block around the cheat's own controls, and a primary button that says
  which act it is. A squadron also gets a **Max pilots** of its own beside its Max size,
  because there was a campaign-wide pilot limit and nowhere to give one squadron a
  different one, so a wing could not hold a small training unit beside its front-line
  outfits. It shows the campaign's figure until you move it and stores nothing while it
  matches, so a squadron you never touched still follows that setting when you change it
  later.
- **The map can be searched.** A log line or a message from the OPFOR planner names a
  site — MINK, or "the Patriot north of Creech" — and finding it meant panning around
  hunting a code name among two hundred icons. The box on the top left searches every
  objective and every base by name, **by what is parked there** (so "Patriot" or
  "Linebacker" finds the site that holds one, and the row says which unit it was), and by
  what kind of thing it is, with chips to narrow it to a side or a kind. Hovering a
  result marks it on the map, clicking it goes there. Entirely client-side: the map
  already holds every name and unit list, so there is nothing to ask the server for.
- **Joining and splitting is something flights do with each other.** A flight that is the
  whole package has nobody to meet and nobody to leave, so calling its two package
  waypoints JOIN and SPLIT described something that was not happening — and it is the
  package that decides, not the flight, however many aircraft that one flight has. They
  read **NAV** on their own and are a join and a split again for everyone the moment a
  second flight is in the package, from the dialog, the API or anywhere else that adds or
  removes one. Only the labels move: the package still meets and parts there and every
  time in the plan is measured from those two points, so everything that acts on them was
  taught to ask the flight plan's **layout** which waypoint is which rather than reading
  its name — the escort task, the flag that releases the escorts, jamming and the
  unlimited-fuel toggle in the generator, and the map's drag handler. That last one was
  not merely going to miss a join labelled NAV: for the primary flight it propagates the
  drag to the others by waypoint type, so it would have dragged the first nav point of
  every other flight in the package. A custom flight plan has no layout to ask and falls
  back to the name, as before. Flight plans live in the save, so the ones already built
  are relabelled once on load.
- **A deletable waypoint can be deleted on an AI flight.** Hand-*adding* waypoints stays
  reserved for all-player flights — an edited route has taken DCS down before — but
  whether a waypoint can go is a property of the waypoint, not of the crew: one you added
  yourself, a refuelling stop, one of several target points, or the join and split of a
  flight that is the whole package all leave a plan the AI can still fly. The delete
  button leaves the greyed box and turns itself on for a selection it can actually reach
  — every waypoint in it, not just one, because half a deletion is worse than none — and
  the join and split it deletes come back the moment a second flight joins the package.
- **The squadron roster reads as figures.** Max, current, on leave, wounded, broken and
  available, in the same tiles as the aircraft inventory, with the Pilots header saying
  how full the squadron is. Pilots can be selected several at a time: sending nine men on
  leave one dialog at a time is a thing a squadron has every turn.
- **The long lists can be typed into.** A Hornet has 86 payload presets and one of its
  pylons takes up to 75 stores, and finding the TALD among sixty rocket pods was
  scrolling rather than choosing. The payload presets, the liveries, the predefined
  waypoints, every pylon's own store list and the loadout list in the flight creator all
  open with a search field above them. Below a dozen items the ordinary popup opens
  instead: a search box over six entries is one more thing to read past.
- **The flight editor is not modal, and it follows the flight you pick.** Editing a
  package means going round its flights, and every trip round cost closing this window
  and finding the next one in the list behind it — and picking one in the main window's
  Flights list, which is meant to bring it up here, was eaten by the modal dialog: the
  window flashed and nothing happened. A selector in the header lists the package's other
  flights, clicking one in the main window switches the open editor to it, and the footer
  has the *Go to package* that was previously reachable only by closing this and finding
  the package again on the map. Everything applies as it is changed, so there is no
  half-finished state a stray click can leave behind, and the checks that run on close now
  run on the way out of each flight, so a trip round the package cannot skip them.
- **Delete cancels a flight, not only a package.** The same key that already cancelled a
  package cancels the selected flight inside one, and keeps a flight selected afterwards
  so a held key works down the list. A flight already in the air is aborted rather than
  cancelled, exactly as it is from the menu.
- **The IADS update interval is a setting.** Skynet re-reads every radar in the network
  and re-decides who wakes every **5 seconds**, which is the single biggest cost it
  carries on a large map -- MANTIS, for comparison, runs its equivalent at 30. It is now
  a plugin option, default **15**. The price of raising it is latency: a site can take up
  to that long to notice something.
- **A radius for what Skynet manages.** Skynet is handed every SAM site, EWR, comms
  tower and power station on the map, for both coalitions, and its cost grows with the
  count: a Morocco save at turn 10 hands it 75 nodes and 100 connections. Setting a
  radius hands it only what lies within that distance of the front line, a package
  target or a carrier -- 45 nodes and 46 connections at 100 km, same save. What falls
  outside is **still generated and still fights**; it is simply not coordinated, so it
  never goes dark and never reacts to a HARM. It is also **forced to red alert**,
  because Retribution starts ground SAMs dark for Skynet to wake and nothing would be
  coming for these. Default 0, meaning the whole map, so no campaign changes unless you
  ask. Separate from the culling setting, which removes distant units from the mission
  altogether. The radius reaches **only radars**: command centres, comms towers and
  power stations are never left out, and a site that stays keeps every dependency it
  has however far away. Skynet reads an absent dependency as a working one, so leaving
  one out would not quieten the network -- it would tell the network everything is
  fine, switching a bombed power station's SAMs back on.
- **Skynet's own performance pass, from our fork.** Ten changes to the script itself,
  authored by Codex and reviewed here: an index for contact merging instead of a scan
  per detection, HARM tracks rejected by distance before any heading or aspect maths,
  short-circuited range checks, position and ammunition sampled once per instant,
  radar coverage built once per unordered pair, world events dispatched to the elements
  that subscribed to the object instead of every element inspecting every event, and
  the jammer filtering by distance before asking the terrain for line of sight. Two
  bugs went with them: a zero-speed contact aborted the whole HARM sweep rather than
  skipping itself, and the periodic maintenance -- the only thing that clears spent
  missiles, expires HARM tracks and lifts jamming -- had been switched off for point
  defences and zero-HARM-chance sites, which is every EWR and, among SAMs, the two
  mobile SHORAD whose shoot-and-scoot depends on it.
- **Skynet now comes from our own fork.** Upstream
  [walder/Skynet-IADS](https://github.com/walder/Skynet-IADS) has had no commit in about
  three years and every fork of it looks abandoned too, so the script lives at
  [juanjux/Skynet-IADS](https://github.com/juanjux/Skynet-IADS) where it can be fixed.
  What was shipped here until now was a build labelled `baron-branch` from May 2023 --
  baleBaron's `ActMobile` fork of Skynet 3.0.1, with unit tables this fork had extended
  since -- and that lineage never came back upstream, while upstream meanwhile fixed the
  HARM path: a site hiding from a HARM now switches its AI off rather than only its
  emissions, which is a DCS multiplayer bug. The fork is both at once, so nothing was
  given up either way: `ActMobile` and the four High Digit SAMs systems (S-400,
  S-300V4, SAMP/T, Pantsir-SM) on top of upstream 3.3.0 and its fixes. Its README is the
  inventory of what we change, and the build this ships is labelled
  `3.3.0-juanjux-fork` -- the line it prints to `dcs.log` on load says which one you are
  running.
- **The stock SAMs play the SEAD game the modded ones already did.** Skynet ships with
  HARM reaction switched off, and only 21 of 597 ground unit types ever turned it on --
  all of them Currenthill mods plus the Patriot STR. So an SA-10 or an S-400 sat there
  and took the missile, while a `[CH]` Buk ducked. Forty stock search and track radars
  now carry the same properties: a 90% chance of noticing an inbound HARM and going
  dark for it. They also wake earlier -- 120% of their own envelope for the long-range
  systems, 130% for the medium ones -- because Skynet's default is to emit only once
  you are already inside the kill zone, which leaves an AI SEAD flight with nothing to
  home on and is the reason those flights behave oddly. The percentages are what MANTIS
  calls `radiusscale`, and the existing "Adjust default SAM go-live range" setting still
  overrides them per system.
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

- **A Debriefing button in the Misc bar, and the report is kept in the save.** The
  debriefing is a modal dialog and an alt-tab can leave it behind the main window, or
  close it before it has been read; the button puts it back. The report itself no longer
  dies with the session: a `Debriefing` is built from the mission's state file and its
  unit map, so it was never storable, but the part the window shows -- counts, names and
  the pilot records -- is now kept as plain data on the game and travels in the save,
  1.6 KB of a 12 MB campaign. Reopening it re-offers the leave requests still waiting
  (the promotion box is told once, not on every reopening).

- **Two morale rules were re-weighed** when Live Pilots became a single master switch: a
  wound is felt every turn the medics keep him rather than only the first three, and going
  without leave costs the same each turn rather than compounding. "Show pilot ranks in
  mission" is gone -- it is part of Live Pilots, not a choice of its own.

- **The debriefing's morale section listed everyone who flew.** It reported any
  movement past a fixed size, and flying the mission is exactly that size, so every man
  who came home earned a row -- reading "Normal -> Normal", since the row names his
  state at each end. It reports a change of state now, which is the thing the row can
  show; the figures stay in the ledger.

- **Ignore parking space at airbases.** Airbases hold as many aircraft as you can pay
  for, whatever their ramp size. Carriers and FOBs are unaffected.
  ([#184](https://github.com/juanjux/dcs-retribution/pull/184))
- **Radar, missile battery and jamming site are one slot.** Buy any of the three where
  any one of them stands, and the map symbol follows what is parked there rather than what
  the campaign built: a dish for a site that only watches, an air-defence symbol for one
  that shoots, the electronic-warfare symbol for a jammer. A site that only watches draws
  its detection ring dashed, in its faction's colour, so an EWR's reach is visible without
  turning on the SAM detection layer. ([#183](https://github.com/juanjux/dcs-retribution/pull/183))
- **Search box for the settings.** Two hundred settings over six pages, plus the
  plugins' own options behind their gears. Type a word, pick a hit, and it opens the
  page, the gear or the plugin's options and flashes the setting. ([#181](https://github.com/juanjux/dcs-retribution/pull/181))
- **Ranks, with a price.** *Rank Names* is *Ranks*, and what each rung costs in XP is
  set there beside its name. The morale bands are settings too, and a pilot's rank
  shift follows them. ([#174](https://github.com/juanjux/dcs-retribution/pull/174), [#179](https://github.com/juanjux/dcs-retribution/pull/179))

- **A plugin's settings live with the plugin.** GPS jamming, cruise missile strikes and
  naval magazines each had a switch in Mission Generator that did nothing unless the
  plugin was on as well; the plugin's own switch is the only one now, and their numbers
  moved behind its gear along with the Skynet IADS radius. Old campaigns keep what they
  had set. ([#186](https://github.com/juanjux/dcs-retribution/pull/186))

- **The payload editor counts the drop tanks.** *Internal Fuel Quantity* is *Fuel
  Quantity* and says what the tanks add and what the aircraft therefore carries -- an
  F-15C on three 610-gallon tanks was reading 13,500 lb when it leaves with 24,800.
  ([#191](https://github.com/juanjux/dcs-retribution/pull/191))
- **Leg distances in the waypoint table**, with the route total under it. Target points
  and the bullseye read 0 and are left out of the total: they are in the list but not on
  the ground track, and the leg after one of them is measured from the last waypoint
  actually flown. ([#189](https://github.com/juanjux/dcs-retribution/pull/189))
- **Native dialogs again.** The file, colour and font pickers were switched to Qt's own
  because a native one opened over the live map deadlocked the app. That was the same
  synchronous path the ANGLE setting removes, so the workaround was costing a Windows
  file picker for nothing. Qt itself is on 6.11.2.
  ([#188](https://github.com/juanjux/dcs-retribution/pull/188))

- **A fuel estimate for the plan**, beside the route total: taxi, the legs at their own
  climb/cruise/combat rates, the landing reserve and a margin, against what the flight is
  carrying. Only 24 aircraft have measured consumption figures, so the rest are estimated
  from how much fuel they hold over a nominal range for their kind -- calibrated against
  those 24 and deliberately leaning high.
  ([#190](https://github.com/juanjux/dcs-retribution/pull/190))

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
- **Refuelling that actually happens.** Upstream had three per-task tanker options that
  asked for a tanker the fulfiller then always pruned, and it hung a refuelling waypoint
  on flights whether or not they needed one. Underneath, the waypoint could not work even
  when it was wanted: the DCS task carried a start condition of *"every unit is at or
  above 20% fuel"*, so a flight arriving at the tanker below a fifth of its fuel -- the
  one case the whole thing exists for -- never began refuelling at all, and went home, or
  to whatever airfield it could reach. That is why flights came back on fumes past a
  tanker that was right there.

  Now it is one setting, and the fuel decides. A package's route is costed leg by leg --
  the climb at the climb rate, the run in at the combat rate, everything else at cruise
  with the altitude correction -- against what the flight leaves the ground with,
  internal plus its drop tanks. If it will not make it, and the faction has a tanker to
  send, it gets a refuelling waypoint **after the target, on the way home**, in friendly
  airspace, and the package asks for a tanker. Patrols get one too: a BARCAP orbits for
  hours and is the flight most likely to want one.

  The decision is made again when **you** edit the flight. The planner decides once,
  while it builds the plan, so taking the drop tanks off or taking the route down to
  eight thousand feet left a flight short with nothing noticing. On the way out of the
  flight editor it asks, the way it already asks whether the ingress point should move:
  *"Add waypoint and tanker"* or *"Add waypoint only"*, with the first greyed out and the
  reason on screen when there is nothing to send. Saying yes does not rebuild the plan --
  that would throw away the edits that made the flight short in the first place.

  A tanker sent this way orbits at the very point the waypoint was put, so the two cannot
  disagree, and it is not offered at all when that point is inside enemy air defences: a
  tanker is large, slow, unarmed and flies in a straight line for an hour. Every idle
  tanker squadron is offered rather than the first, with **the refuelling system each one
  uses**, because nothing in the aircraft data -- ours or pydcs's -- says whether a
  receiver has a probe or a receptacle, and a Hornet sent to a boom-only KC-135 comes home
  empty.

  And it is still there when the flight arrives. The tanker used to hold for five minutes
  plus four a head -- ten minutes for a single flight -- centred on an arrival time that
  is itself an estimate, and to reach station ninety seconds before it. It now holds for
  the campaign's configured tanker on-station time and is there **ten minutes early**,
  because a flight that fought, routed around a threat or simply flew its legs at another
  speed is minutes out either way, and nearly always late.
  ([#211](https://github.com/juanjux/dcs-retribution/pull/211),
  [#213](https://github.com/juanjux/dcs-retribution/pull/213),
  [#214](https://github.com/juanjux/dcs-retribution/pull/214))
- **The LLM can see and choose its pilots, and read every setting.** Two parity gaps the
  OPFOR agent reported: it could see a flight's uncrewed count and nothing else about the
  people in it, and `/settings` was a hand-written subset that happened not to include
  mission durations. Now `GET /squadrons/{id}/pilots` is the Air Wing roster -- rank,
  experience, skill, wounds and the flight each man is already crewing -- `GET
  /flights/{id}/crew` shows one flight's seats and who is free, and `POST /flights/crew`
  seats a named pilot or empties a seat, refusing anyone dead, wounded, on leave or
  already flying. `/settings` keeps its curated fields and gains `all_settings`: every box
  on the settings pages with its label, value and explanation.
  ([#139](https://github.com/juanjux/dcs-retribution/pull/139))
- **Saves still had pilots who were flying and available at once.** The fault below is
  fixed, but every save written while it was live still carries the state -- five pilots
  across three squadrons in one campaign -- so the Edit Flight dropdown listed the same
  man twice and the next flight could claim him again. A migration step now takes anyone
  in a cockpit out of the pool on load, and the selector lists nobody twice however the
  save got that way.
  ([#141](https://github.com/juanjux/dcs-retribution/pull/141))
- **The same pilot could fly two missions in one turn.** Clearing a roster handed its crew
  back to the squadron and then went on holding them, so a pilot could be flying one
  mission and be offered for the next at the same time. Measured in a save: El Jefe and
  Yayo each flew a BARCAP over Kirkuk *and* a DEAD on BONGO, the same pilot objects in
  both, with the squadron's books reading fifteen active, eleven available and four
  claimed seats between two people.
  ([#138](https://github.com/juanjux/dcs-retribution/pull/138))
- **The Su-25 was planned to fight from a height it will not shoot from.** Neither
  Frogfoot declared a combat altitude -- no aircraft in the fork did -- so both fell back
  to the estimate made from their top speed, 20,000 ft clamped to the doctrine ceiling,
  and from up there the AI never attacks: a pair tasked at 5,000 m crossed a front full of
  armour unopposed and came home without firing, correctly armed and tasked with 65 enemy
  vehicles in the zone. The ceiling is the pilot's rather than the weapon's -- a cadet
  shoots to about 3,000 m and an average pilot to about 4,500 -- and Live Pilots starts
  everyone a cadet. The 5,000 m was deliberate, to stay above MANPADS; there is no
  altitude that does both.
  ([#135](https://github.com/juanjux/dcs-retribution/pull/135))
- **A TARCAP gets its own on-station time.** It read `doctrine.cap_duration`, a flat 30
  minutes in all three doctrines. `Doctrine.from_settings` maps the BARCAP setting onto
  that field and nothing has ever called it, so the number a player typed reached BARCAPs
  and never TARCAPs. They are different jobs anyway: one guards a base for hours, the
  other covers an attack. Defaults to the 30 minutes it always was, and still gives way
  to the escorted mission when a flight in the package asked for an escort. The pilot
  selector also addresses pilots by rank now and orders them by seniority.
  ([#137](https://github.com/juanjux/dcs-retribution/pull/137))
- **The LLM is warned when it sends a CAS flight higher than it will shoot from.** Height
  is not free the way distance is, and where the line sits depends on the airframe, the
  load and the pilot -- so the warning claims no ceiling, only that the flight is above
  what its own aircraft is planned to fight from. The edit is applied regardless.
  ([#136](https://github.com/juanjux/dcs-retribution/pull/136))
- **Bombing the parking killed the pilots who were not in the aircraft.** Every reserve
  on the apron is given a stand-in flight so the debriefing can account for the airframe,
  and that flight claims a real pilot from the roster. Nobody is sitting in one. An
  attack on the parking killed them anyway -- a JF-17 shot up on the ramp cost 2ndLt
  David Johnson his life without him leaving the squadron building. The airframe is
  still lost; the pilot is not.
  ([#134](https://github.com/juanjux/dcs-retribution/pull/134))
- **Live Pilots II: a rank has to be earned.** Rank used to be a count of missions flown --
  one tier every four sorties, ticked for every pilot in the ATO whether he flew, fought,
  or died on the ramp. It is paid for now: 500 for an air kill, 500 for coming home, 200 a
  vehicle, 300 a hull, and a building is worth what the building is worth (an oil platform
  500, a warehouse 100, from `REWARDS`). Thresholds double at every rung, 1000 to 8000, and
  the coalition skill setting becomes a **floor** rather than a starting point. Nothing new
  had to be recorded to find out who did it: the base plugin has written the killer's unit
  name on every kill all along and Python simply never read it. Proportionality comes from
  the pieces rather than a damage percentage, which DCS does not report anywhere -- a
  refinery is four platforms, each with its own death, so two of them is half a refinery.
  What DCS *does* report is who **hit** what, which makes an assist real rather than a
  guess: the plugin records the first hit each aircraft lands on each target -- once per
  pair, so a strafing pass is not paid by the round -- and that is worth a quarter of
  destroying it, never on top of the kill. Rank now also decides whether a pilot walks
  away from a loss, one in five for a cadet and four in five for a squadron leader, with
  the five percentages on the settings page under a switch of their own. A pilot climbs at most one
  rung a mission and arrives holding what that rank costs, nothing banked towards the
  next: a SEAD sortie that clears a whole site otherwise finished a cadet as a Captain.
  The debriefing scrolls as a whole and gains a Pilots box: promotions, who was shot
  down and recovered, who was wounded, and who was killed and by whom, flagging friendly
  fire -- and when the promoted pilot is one the player flies himself, he is told so in a
  box of his own, with the rank spelled out. The Air Wing lists the senior pilot first, in the
  living roster and the roll of the dead alike. And a loss that rank did not save gets
  one more throw: 35% by default that the pilot is **wounded rather than killed**, flat
  and rank-free, out of the roster for one to four turns exactly as a pilot on leave is
  -- keeping his place on the books, so the squadron flies short-handed instead of
  backfilling him and overflowing when he comes back. The wound is worth 200, against
  the 500 for a sortie: losing the aircraft now forfeits the mission-complete award it
  was quietly still paying, so being shot down is never the better outcome.
  ([#134](https://github.com/juanjux/dcs-retribution/pull/134))
- **Live Pilots IV: a pilot has an opinion of the man next to him.** A four-ship used to
  be four strangers sharing a frequency. Now each pilot holds a **friendship** with each
  other pilot, 0 to 10 from 5, and it is **one-way**: what he thinks of somebody is not
  what they think of him, which is not decoration -- the two effects that read it read
  opposite ends. It moves slowly between everyone at a base, faster in the air, and a
  quiet turn can never carry a pair past *Friendly*: the levels that pay for anything are
  earned flying together, so keeping a crew across turns is worth something. What it
  buys: **a mission pays more** with men he likes and less than flying alone with men he
  cannot stand; a flight or a package that reaches *Close* **flies one skill level above
  its rank**, weighted so that what each man thinks of his lead counts double, which
  makes spreading veterans one to a flight beat stacking them; the men who think well of
  *him* **look harder** when he goes down; friends **hold him in his seat** where rank
  alone did not, shorten a bad week and make leave taken together worth more. And it
  costs: a death lands on the men who were up there with him as many times over as they
  thought of him. Shooting down one of your own is the one thing that moves it sharply
  the other way. Alongside it, **hardening**: a point for every turn a pilot spends
  Shaken or worse, never lost, which softens every morale hit, makes him likelier to
  survive a wreck, and thickens his skin both ways -- the answer to a run of losses
  taking a whole squadron to Broken together and leaving it there. Friendship colours the
  pilot picker, the leave dialog and the Air Wing roster in the same bands, the Air Wing
  says which squadrons are crews rather than lists of names, the planner reads all of it
  over the API, and every figure is a setting with its arithmetic spelled out.
  ([#217](https://github.com/juanjux/dcs-retribution/pull/217))
- **Live Pilots III: a pilot has a state of mind.** Everyone used to fly the same
  whatever the campaign had done to him -- the man shot down twice, who watched his
  squadron die and has not had leave in eleven turns, took off exactly as steady as the
  one who was promoted twice and slept. Now he carries **morale**, 0 to 100, starting at
  50, moved by what is already in the debriefing: losing his aircraft, coming home from
  a strike having destroyed nothing, a squadron mate killed, a base lost, five turns
  without leave and worse every turn after -- against kills, targets of opportunity,
  completing the sortie, his promotion and rest. It drifts a step back towards 50 every
  turn, and rank is armour: a squadron leader loses less from the same event than a
  cadet, though nobody is too senior to enjoy a promotion. It buys four things. **What a
  sortie pays** is no longer flat -- half at the bottom, half again at the top, and +0.1
  per rung of difference to the best pilot in the flight, so a cadet on an Excellent
  wing earns 40% more and the veteran earns nothing extra for the company. **How he
  flies**: above 85 he flies a rung better than his rank and below 15 a rung worse,
  which is not cosmetic -- the attack ceiling belongs to the pilot, so a dropped rung can
  stop him attacking from the altitude he was planned at. That shift goes through a new
  `mission_skill` and never touches `pilot_skill`, because rank is derived from it and a
  bad week must not demote a Major. **What his flight will put up with**: a lead below 20
  routes around what frightens him instead of fighting through it, and below 10 he turns
  for home -- group options, so the formation follows the man in front. And **whether he
  comes back**: morale shifts the survival roll and the length of a wound. At the bottom
  he refuses to fly, does not mend on his own, and after three turns there he is simply
  gone. **Leave** answers that, and gains a length: a pilot asks -- more often the worse
  he is holding up, but a contented man asks now and then too -- and a dialog after the
  debriefing lists them with the turns to grant, per man, or a refusal that costs him.
  His row in the Air Wing names it -- Triumphant, Confident, Normal, Shaken, Shattered,
  Broken, the way a rank names a skill level rather than showing the number behind it --
  and turns yellow, then red, in time to do something about it. Fifteen settings, and a campaign in progress starts even: old saves
  read as morale 50 with no leave owing.
  ([#142](https://github.com/juanjux/dcs-retribution/pull/142))
- **Switching Live Pilots on demoted one coalition and not the other.** Starting the
  ladder wrote Cadet into the difficulty page, and settings carry into the next campaign
  started from them -- so a second campaign began at Cadet, seeding measured blue against
  a floor a previous campaign had lowered and gave every pilot zero, while red kept its
  rank. 261 second lieutenants against 295 first lieutenants, and no way back to whatever
  the difficulty had been. The floor is computed now instead of stored: Live Pilots puts
  every wing on the bottom rung and the difficulty page keeps saying what the player set,
  which is what the wing returns to when the feature is switched off and what still
  decides ground unit skill. ([#134](https://github.com/juanjux/dcs-retribution/pull/134))
- **Live Pilots** (off by default) — a pilot holds a *rank* instead of a bare AI skill
  level, and carries it into the mission: the flight label reads `1stLt Pepito Perez`
  where DCS would leave `Pilot #2`, and the Air Wing roster names the rank in full under
  the pilot. DCS turns out to have five air skills rather than four -- the mission
  editor's Cadet, Rookie, Trained, Veteran and Ace are written as `Cadet`, `Average`,
  `Good`, `High`, `Excellent`, and pydcs' enum was missing the bottom one, so
  `game/dcs/skills.py` adds it and owns the ladder. Ranks are named in each squadron's
  own service -- `FltLt` for the RAF, `Hptm` for the Luftwaffe, `MlLt` for the VVS,
  31 countries -- or generically, or by the DCS skill names themselves, or by five names
  you type in. Rank is a renaming of the skill level,
  not a second ladder: competence is the only thing DCS can be told about. The coalition
  skill setting now offers Cadet for pilots but not for vehicles -- blue shares that one
  setting with its tanks, where the editor has no such rung -- so anything not flying
  clamps back to `Average`. First slice of a larger feature; promotion is still by
  missions flown.
  ([#129](https://github.com/juanjux/dcs-retribution/pull/129))
- **Mission Log** (plugin, off by default) — a running commentary of what happens to
  your side while you fly: who shot down whom and with what, which targets went down,
  who ejected, who crashed with nobody shooting. DCS has all of these events but calls
  the aircraft `STAG BARCAP|2|14|F-15C Eagle| Pilot #2` and does not know the pilot at
  all, so the generator seeds `RETRIBUTION_PILOTS` (unit name → rank and pilot) and the
  script reads the aircraft type straight out of the unit name — mod aircraft come out
  right without a table of their own. Each message goes only to the coalition it is news
  for: a kill for the shooter, a loss for the other side. Every category has its own
  toggle, and the roster is only seeded when the plugin is on. Interceptions are polled
  rather than eventful — DCS fires nothing for "I have seen him and I am going after
  him" — so every fighter group is asked what its radar holds and what the datalink
  handed it, and the message says which of the two found the target. The log has since
  been quietened and then sharpened: *monitoring* — a fighter looking at something it has
  not committed to, the commonest line by a distance and the least eventful — is off
  until you ask for it; a ground kill carries the same "enemy" prefix an aircraft already
  had, because "DESTROYED 3 T-72" and "DESTROYED 3 enemy T-72" are not the same sentence
  on a front with both sides' armour on it (and whose it was is part of the batching key,
  so a friendly and an enemy T-72 killed in the same window cannot merge into one line
  that would have to lie about one of them); SHOT DOWN, CRASHED, EJECTED and DESTROYED
  are shouted, because a kill and a takeoff read the same in a scrolling column and are
  not the same news, while "hit" stays lower case since it is damage rather than a kill;
  and the two lines you actually want to find again get a word in front of them — YEAH!
  and OH NO! by default, both settings, an empty one turning it off. Good news only when
  what died was theirs: blue blowing up blue gets the other word.
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
  longer sends every nearby package defensive.
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
- **A destroyed site keeps its place in the network, and its links on the map.** The same
  fault one layer up: a site with nothing alive was dropped from the IADS network
  altogether, and its links went off the map with it — so a link whose power station died
  drew as a break, and a link whose SAM died simply vanished. The state you most want to
  see was the one state never drawn. On the Nevada save that is 9 nodes and 19 links
  drawn where there are 17 and 34, and 24 of those 34 are breaks. A dead site keeps its
  node now. Whoever is alive still *leads* it, though, so a site whose SAM is gone but
  whose point defence is not goes on reaching Skynet and fighting; handing the lead to
  the dead group would have taken a live Vulcan out of the IADS. The second fix of the
  class is the command centre: flattened, it used to leave the network, and Skynet's
  `isCommandCenterUsable()` returns true on an empty table, so losing the last one handed
  command back. The damage is already in the saves, and nothing recreates a node that was
  pruned, so a campaign that has been fought in builds its network once more on load,
  from the campaign configuration and the objectives as they stand — the same thing that
  happens when a campaign starts. Once is enough, because it cannot be pruned again.
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
- **GPS jamming in every modern campaign.** One site apiece, on the enemy early-warning
  radar whose 15 nm bubble covers the most of its own air defences, so a satellite-guided
  weapon aimed at anything in that belt lands wide until the trucks are dead. Thirty-eight
  campaigns, each verified by building it. ([#183](https://github.com/juanjux/dcs-retribution/pull/183))
- **The IADS configs actually resolve now.** Thirty-nine buildings the configs named were
  in no mission -- every one had a trigger zone marking where it went and no object placed
  -- so bombing the infrastructure did nothing, and command centres that were never keys
  never reached Skynet at all. ([#183](https://github.com/juanjux/dcs-retribution/pull/183))

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

- **A SAM with no power woke up the moment it lost its comms.** Reported as two Patriots
  keeping their threat rings and firing with their power stations destroyed. The data was
  right the whole way down — the archived mission for that turn hands both sites to
  Skynet with exactly what they depend on, and both power statics spawn into it with
  `dead = true`, which is what Skynet reads as "no power". The fault is in Skynet's own
  `goAutonomous()`: losing a connection node makes an element autonomous, and under
  `AUTONOMOUS_STATE_DCS_AI`, which is what we set, autonomous meant `goLive()`
  unconditionally. So bombing the comms node of a site whose power station was already
  rubble was *worse than bombing nothing* — it woke a site the command centre would
  otherwise have kept dark. Going autonomous means an element lost its network, not that
  it grew a generator, so it now stays dark without power whatever its autonomous
  behaviour says. Found by reading the archived `.miz` for the turn in question: the
  sites had been destroyed since, so nothing in the current save could have shown it.
- **A squadron with nobody willing to fly read as fully manned.** The engine was right —
  of 43 broken pilots in one campaign save, not one was in an availability pool. The text
  lied: the squadron dialog subtracted the wounded and the ones on leave and nothing
  else, so a squadron with eight men refusing to fly still read "8 available", and the
  Air Wing row showed the bare headcount, so one with nobody to send read "16 pilots".
  Both go through `Squadron.fit_for_duty` now — on the books, not hurt, not away, willing
  — which is what those counts have always meant to a player. Deliberately not
  `available_pilots`: that is the untasked pool and shrinks as you plan, which is a
  different question. The dialog names the refusers beside the wounded, because a
  squadron you know to rest is not the same as one that looks under-used.
- **A plugin could not ask the player for a word.** The plugin options dialog drew a
  checkbox for a boolean and a spinner for a number, and for a string it drew the label
  and no control at all — so the Mission Log's YEAH! and OH NO! arrived as two rows you
  could read and not change. Strings get a field, and an empty one is an empty one: the
  log already treats that as "say nothing".
- **A flight sent AHEAD of its package arrived behind it.** The package TOT was worked
  out from the slowest flight's transit alone, ignoring each flight's own TOT offset --
  but a flight three minutes early has to be over the target three minutes *before* the
  package, so it needs the package scheduled three minutes *later* than its transit
  demands. It wasn't, so its plan was built backwards from a time it could not reach,
  its takeoff landed before the mission started, and the clamp turned the requested
  head start into an equal delay -- worse the larger the offset. The earliest reachable
  package TOT now accounts for the offsets, and changing an offset in the flight dialog
  slides the whole package later when it has to, keeping the spacing the offset asked
  for. The offset direction is also now read from the control's state rather than
  flipped, so it cannot drift out of step with what the box shows.

- **Three in the fuel figures.** Adding or removing a drop tank did not move the total;
  the estimate took no account of the altitude flown; and it charged the join and split
  legs at the combat rate, which put a strike's eighty-mile egress at over twice its
  real cost. ([#192](https://github.com/juanjux/dcs-retribution/pull/192))
- **Take Off crashed on any flight with a racetrack.** The EW jamming plugin was
  dropped, but five places still read its options, and the check for whether it was
  there sat after the read. Any campaign started since then died on its first BARCAP,
  AEW&C or tanker. ([#194](https://github.com/juanjux/dcs-retribution/pull/194))

- **"Apply to all" skipped every AGL waypoint**, which froze a helicopter's whole flight
  plan -- an Apache cruises AGL, so there was nothing left for it to set -- and most of a
  low-level one. It goes by waypoint type now; the points tied to the ground were already
  in that list. ([#193](https://github.com/juanjux/dcs-retribution/pull/193))

- **Factions with no early-warning radar fielded a SAM's acquisition radar as one.** An
  EWR marker falls back to a search radar when the faction owns no EWR, so Ukraine,
  Georgia, Morocco, France, Argentina, Peru and Iran were putting up a Patriot STR or a
  Hawk SR where a national radar belonged.
  ([#187](https://github.com/juanjux/dcs-retribution/pull/187))

- **A GPS jamming site drew the wrong circle.** The map showed the couple of miles its
  point defence reaches instead of the jamming bubble, and drew it solid. The bubble is
  its own dashed ring now. ([#185](https://github.com/juanjux/dcs-retribution/pull/185))

- **A campaign's `ground_forces` pin was ignored on early-warning radar markers.** The
  override was read, matched the marker's band and passed the faction gate, and was then
  dropped without a line in the log, because that one band went straight to the random
  roll. Every GPS jamming site any campaign had ever declared was silently an ordinary
  radar. ([#183](https://github.com/juanjux/dcs-retribution/pull/183))
- **A pinned site generated without its point defence.** The fill searched artillery,
  frontline and logistics units while air defence lives in its own list. ([#183](https://github.com/juanjux/dcs-retribution/pull/183))
- **The search box stretched the settings page list across the dialog**, a section name
  returned one row per setting inside it, and four letters were short enough to match
  almost anything. ([#182](https://github.com/juanjux/dcs-retribution/pull/182))
- **Player pilots were playing the morale game.** The debriefing told you how you felt
  about your own turn, and the same figure moved the skill you flew at, your XP and
  your survival roll. Morale is for the AI pilots. ([#173](https://github.com/juanjux/dcs-retribution/pull/173))
- **Three Splash Damage options had never done anything.** The parked-aircraft boost
  and the anti-radiation ship-radar kill called a `getAGL()` that is defined nowhere,
  so they raised on every blast wave; the cluster bomblet reduction was written to a
  key spelled differently from the one the script reads. All three came in with
  upstream's own 3.4.2 update. ([#177](https://github.com/juanjux/dcs-retribution/pull/177))
- **Turning Live Pilots off and back on left its settings dead.** The master switch
  only ever disabled, and it could not reach the pages it did not own.
  ([#174](https://github.com/juanjux/dcs-retribution/pull/174), [#179](https://github.com/juanjux/dcs-retribution/pull/179))

- **A pilot on leave held no place, so squadrons grew past their own limit.** The count
  of free slots looked at the active and the wounded and forgot leave, so every absence
  was backfilled and the squadron was over strength the day the man came back. On an
  Iraq save at turn 11 nine squadrons limited to sixteen sat at seventeen, and one with
  twelve men resting had reached twenty-four -- and still read four free places. A slot
  is now held by anyone still on the books; only the dead, the deserted and the
  discharged free one. A squadron already over its limit recruits nobody and comes back
  down as men are lost, rather than having anyone taken off it.
- **Transferring an army mid-turn made it vanish from the ground war.** Two faults, one
  symptom: 26 blue groups holding the line on the map, no armor recorded anywhere in the
  theater, and a defeat handed to a red base with two vehicles. The ground war was planned
  once at the start of the turn and cached on the `Game`, so anything moved afterwards was
  still deployed from the stale plan while the battle was resolved from the books; the
  cache had one reader, so it plans at mission generation now. And units waiting for a lift
  that did not exist were debited on order and therefore absent from the ground war --
  thirty-two vehicles sat under "No transports available" for a whole turn while their
  front was resolved as undefended. They are debited **on departure** now, and until then
  they are simply at their base: deployable, defending, counted. Cancel, disband and
  arrival check the same flag so nothing is handed back that never left. The base dialog
  spells it out (`25 pending transfer, 12 transferring this turn`) and so does the LLM's
  control point view. ([#133](https://github.com/juanjux/dcs-retribution/pull/133))
- **The settings dialog took a couple of seconds and flashed white windows first.** Two
  faults. The page refreshed visibility while its layout was still being built, and a
  group box added to a layout that is not yet installed on a widget has no parent -- in
  Qt, showing a parentless widget makes it a top-level window, so every section briefly
  became its own frame on top of the map. And the dialog, rebuilt from scratch on every
  open, raised all seven pages -- 192 settings, some six hundred widgets -- to show one.
  Pages are now built the first time they are selected: opening the dialog raises
  Difficulty's thirteen settings instead of all 192.
  ([#129](https://github.com/juanjux/dcs-retribution/pull/129))
- **A dry run grounded a squadron for the turn.** `plan_mission` claims aircraft flight
  by flight and releases them when it scrubs a mission for missing types, but anything
  that *raises* in between walked out with the claims standing: the squadron read as
  fully committed to a package that never reached the ATO. The agent's
  `/packages/evaluate` hit it reliably -- probing a task the target does not accept is
  exactly the failure that raises -- leaving an H-6J wing reporting "all 1 already
  tasked" with an empty package list and nothing for `DELETE /packages` to clear. Fixed
  at the claim rather than the endpoint, so planning is atomic for every caller.
  ([#131](https://github.com/juanjux/dcs-retribution/pull/131))
- **The Su-25 flew DEAD carrying only weapons it cannot guide.** All six attack pylons
  were Kh-25ML and Kh-29L, both semi-active laser, and the plain Frogfoot has no
  designator -- so `replace_lgbs_if_no_tgp` strips them, and where it finds no fallback
  it deletes the pylon outright. The aircraft flew the mission unarmed. RBK-250 with
  PTAB-2.5M instead. ([#130](https://github.com/juanjux/dcs-retribution/pull/130))
- **Scud and ATACMS sites cratered empty fields.** A missile site fired at the enemy
  control point's `position` -- a campaign-map coordinate with nothing standing on it --
  displaced by up to 2500 m in a random direction, so every salvo landed in open country
  a few hundred metres off the runway. Measured over one turn: 48 ATACMS rounds, zero
  hits, target airfield untouched. They now aim at live, immobile ground objects at the
  target base, fall back to the map coordinate only for a base that has none, and range
  is measured to the aimpoint rather than to the base. Kirkuk went from one abstract
  point to eleven real ones. The salvo is aimed at the objective itself, with
  nothing added. A crater trail settled that: a site holds three launchers all tasked
  at one point, and DCS walks the rounds along the firing line for about a kilometre
  by itself, so there was never any dispersion left to model -- displacing the aimpoint
  by a published CEP only moved the whole trail off the target. Measured before the
  change: 7, 17 and 43 m off for the ATACMS sites and 181 to 793 m for the Scud ones. Naming the enemy *group* instead of a
  coordinate was tried next and measured: of seven sites in one mission, the six given
  an `AttackGroup` fired nothing at all and the one that fell back to a point fired
  three Scuds. DCS ground AI does not honour the task, so it is back to firing at a
  point. Minimum ranges are respected as well -- the ATACMS and Iskander cannot engage
  inside 75 km, the DF-21D inside 300, and pydcs carries no such field so the values
  come from the launchers' own mod files -- and so is the top of the envelope: an
  ATACMS tasked at 296 of its nominal 300 km overflew the aimpoint by 18 km, because
  the mod gates its terminal manoeuvre on a seeker lock the engine will not give it
  when it is aimed at a coordinate. The last fifteen per cent is off limits, and a
  launcher with nothing worth shooting holds its fire.
  ([#128](https://github.com/juanjux/dcs-retribution/pull/128))
- **Su-25s flew close air support with weapons they cannot guide.** A flight took off
  with eight S-25L each and attacked nothing while the Su-34s beside them worked
  normally: the S-25L is a laser-guided rocket and the plain Su-25 has no designator, so
  it can carry them and never fire them. The strip that exists for exactly this
  (`replace_lgbs_if_no_tgp`) checks `WeaponType.LGB`, and the whole Soviet laser family
  was typed `UNKNOWN`. `LGB` here means "needs a designator" — the laser Maverick, a
  missile, was already typed that way — so S-25L, Kh-25ML, Kh-29L and the laser KABs now
  match. Dual GPS/laser weapons are deliberately left alone: they work without one. The
  Su-25T gains its Klen-PS, so it keeps what the plain Su-25 loses. ([#125](https://github.com/juanjux/dcs-retribution/pull/125))
- **A Patriot battery reported no threat at all.** Two AN/MPQ-53 radars and eight PAC-3
  launchers drew no ring on the campaign map while shooting perfectly well in the
  mission. A launcher only counts when one of its paired trackers is alive, and the CH
  launchers were paired with the MPQ-65 and LTAMDS but not with the MPQ-53 — the original
  Patriot array, the radar the system is named after — which was missing from
  `TRACK_RADARS` entirely. ([#126](https://github.com/juanjux/dcs-retribution/pull/126))
- **`/prev_turns?n=1` answered with the turn you are sitting in.** The turn being planned
  gets a stats entry the moment it starts, so the last *n* always included it and the
  debrief of the turn actually flown sat one place further back. An LLM asking for its
  own results got totals with no losses and concluded the endpoint was broken.
  ([#127](https://github.com/juanjux/dcs-retribution/pull/127))
- **The pilot roster went missing whenever a second campaign was started.** Every Mission
  Log message named an aircraft with nobody flying it. The script is injected when the
  plugin manager says the plugin is on; the roster was seeded when `game.settings` said
  so. The manager is a class-level singleton holding whatever settings it was last loaded
  with, so a second campaign left it answering for the first — script in, roster out.
  ([#124](https://github.com/juanjux/dcs-retribution/pull/124))
- **The Mission Log never showed our own launches, and claimed interceptions that were
  not happening.** A launch was only reported to the side being shot at, so blue fighters
  firing AMRAAMs put nothing on the blue player's screen; it now also reports as
  "engaging" to the shooter. And a BARCAP handed a contact by datalink at 78 nm does not
  leave its racetrack, so beyond 40 nm the message reads "holds" rather than "is moving
  to intercept". ([#123](https://github.com/juanjux/dcs-retribution/pull/123))
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

## Removed from upstream

- **Fast forward.** It never worked well enough to be worth the machinery: a loop
  timer, sim-speed controls, per-state halt conditions and a pre-launch dialog for
  when the stop condition could not be reached. Take Off hands DCS the mission at the
  time it was planned for. ([#176](https://github.com/juanjux/dcs-retribution/pull/176))
- **Four plugins.** EWRS is the 2016 script BigEye EWR was rewritten from; Mbot's Call
  Artillery only ever answered a player flying Armed Recon, while Carsten's answers
  anyone in range; the C-130 cargo script is for a mod we do not support; and the EW
  Jammer script cannot model jamming honestly without engine support. ([#175](https://github.com/juanjux/dcs-retribution/pull/175))

- **DCS: Pretense support.** Upstream can export the running campaign as a
  [Pretense](https://github.com/Dzsek/pretense) mission — a self-contained Lua campaign
  where zones earn resources, buy their own defences and frag their own AI missions. That
  is a second, parallel game: nothing that happens in it ever comes back to the
  Retribution campaign, the export is one-way, and it is why the generator pickled a
  backup of the save before running. The upstream project has stopped maintaining it and
  Pretense itself is abandoned, so it was ~5,400 lines of Python plus 590 KB of
  third-party Lua (`pretense_compiled.lua`, 15,862 lines) that nobody here can debug,
  carried through every upstream sync — and it reached into the engine, adding a
  `FlightType` member, a flight plan, a settings page and a contract test of its own.
  Gone: `game/pretense/`, the Pretense plugin resources, the toolbar actions, the
  settings page, `FlightType.PRETENSE_CARGO`, and the four `*_full` campaigns that were
  tuned for Pretense generation (their own descriptions warn they play unbalanced as
  ordinary campaigns).

  **Saves still load.** A campaign that had generated a Pretense mission kept its cargo
  flights in the save, so `FlightType` maps the old `"Cargo Transport"` value onto
  `TRANSPORT` on load instead of failing.

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
the archived `.miz`. Built and working, and **parked after reading one**: with fixed
templates it comes out repetitive — the same handful of sentences whichever way the
mission went — and the Mission Log already tells you everything it does without the
literary pretension. **The code has since been taken back out** -- it was still shipping
in every build for a feature nobody was going to open. The event recording it fed on is
untouched and still lands in `state.json`, so reviving it means writing a better renderer
against that timeline, or handing it to an LLM and letting it write the thing properly.
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
