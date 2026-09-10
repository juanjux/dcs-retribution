# Realistic CAS: first combat comparison, 9 September 2026

## Evidence and limits

Logs archived outside Missions in `realistic-cas-test-results/combat-38/`:
`dcs-first-pair.log` contains A, B and part of the repeated B;
`dcs-with-repeat.log` contains the completed repeat too.

All three runs completed at 1800 simulated seconds, zero script errors and zero
instrumentation inconclusives. That is NOT confirmation of balanced gameplay.

| Run | Red survivors / 24 | Native credited CAS kills | Native credited ground kills | Unattributed red deaths |
| --- | ---: | ---: | ---: | ---: |
| 38A OFF | 0 | 16 | 1 | 7 |
| 38B ON first | 7 | 13 | 0 | 4 |
| 38B ON repeated | 7 | 12 | 1 | 4 |

Each run ended with 11/12 blue ground units and 1/2 A-10s. Native KILL credited
the lost A-10 to RED_03-2 (OFF, 1044.0s), and RED_09-2 (ON first, 451.4s;
ON repeat, 1216.7s). Both named units are BMP-2s. The user observed the A-10 crash;
the native attribution means it must not be treated as a proven unopposed accident.
Different aircraft loss times confound sustained CAS output.

The user correctly identified two design problems: most ground groups were packed
within ground detection range, and the inherited A-10 orbit was confined to the
blue side. Those scenarios cannot establish the intended front-search behavior.
Do not interpret seven surviving tanks as the calibrated effectiveness of the plugin.

An additional instrumentation issue was found in the log: a late native KILL
with an unavailable initiator can follow an already credited KILL for the same
wreck. Version 38 overwrote that attribution. The table above is the original
reported data, not a repaired count. Version 39 preserves known native credit;
HIT remains unconfirmed and is never upgraded to a kill merely by temporal proximity.

## What the campaign code actually generates

- `game/ground_forces/ai_ground_planner.py`, `DISTANCE_FROM_FRONTLINE`:
  tanks 2200–3200m; IFV/APC 2700–3700m **on their own side**. Other roles have
  different depth bands (e.g. SHORAD 5000–8000m). These are spawn depths, not an
  invariant spacing after movement.
- `FlotGenerator.get_valid_position_for_group` chooses a lateral position along
  the front, then steps perpendicular into that side, retaining the last valid
  land position if the desired depth leaves the playable area.
- `max_frontline_width` defaults to 80km, bounded/clipped by theater and settings.
- `FlotGenerator._generate_group` uses pydcs's default Line formation; adjacent
  members have a 20m spacing in that formation. Group spacing is a separate concept.
- `CasFlightPlan.Builder.layout` takes the front's bounds as FLOT START/END,
  with ingress followed by those two ordinary waypoints and egress. CAS does
  **not** use OrbitAction, unlike CAP.
- `CasIngressBuilder` installs EngageTargetsInZone centered on the patrol segment;
  the engagement radius setting defaults to 10NM. Targets are Ground vehicles,
  AAA, Infantry, using exact pydcs identifiers.

## Replacement 39 (generated; engine result pending)

`Missions/39A_Realistic_CAS_battle_OFF.miz` and `39B_Realistic_CAS_battle_ON.miz`.
Configuration/hash evidence in `realistic-cas-test-results/combat-39-final/`.
The earlier unpublished draft is archived in `combat-39/`, not in Missions.

- Same 24 red / 12 blue ground units, two AI A-10C II, six AGM-65D per aircraft,
  pod, cannon, Average, clear midday, vulnerable units, and 1800s observation.
- Deterministic positions inside the campaign's tank/IFV depth bands; lateral
  spread across a 24km test segment, not a claim that every campaign front is 24km.
- Closest opposing ground units exceed 4500m initially; no initial ground sensor
  blanket is possible under the modeled ranges. Terrain may further limit LOS.
- CAS travels through ingress, central FLOT START/END (30km), then exits. No orbit
  or repeat-task command is inserted to force attacks/reacquisition.
- All targets lie inside the native 10NM search zone. No aircraft immortality,
  ammunition changes between variants, or artificial kill quotas.
- Logging includes north/center/south sectors and native crash events with prior
  hit/kill context. The raw log can distinguish loss timing and interrupted CAS.
- Run with the same acceleration; only the log is required. No additional run
  should be requested merely because the user did not watch visually.

## Parallel implementation progress

The exported mission bootstrap, serialization and rollback/mission-end lifecycle
are implemented and Lua-tested without DCS. They are not injected into campaigns
yet; environment export, JTAC/TIC adapters and UI integration remain separate work.

## Results 39 and isolation revision 40

Completed 39 log archived as `combat-39-final/dcs-results.log` (also contains
earlier runs; identify 39 by scenario hash
`76580c78b65bebb3f64c38a7fefac0faa3270bd9bcdcc3e6cf3b873939a9bb47`).
Both 39 runs completed at 1800s without script errors or instrumentation
inconclusives. OFF retained 9/24 red ground units, versus 16/24 ON. Credited CAS
kills were 12 OFF and 5 ON, with three additional unattributed red deaths in
each. Blue ground retained all 12 in each; OFF retained both A-10s (one damaged),
ON retained one damaged A-10, the other natively credited to ground fire.

The user identified two remaining confounds: a limited Maverick load and enemy
ground fire removing a CAS aircraft. Neither difference proves the intended
detection balance. Revision 40 keeps the exact 39 routes and ground geometry,
but isolates CAS perception using HOLD FIRE for every ground group throughout.
Ground observers remain active; ROE is not a sensor-disable switch. Any ground
SHOT/SHOOTING_START event is logged as an error and makes that comparison
inconclusive. It also prevents firing from automatically revealing those targets.

Both 40 variants set native `forcedOptions.unlimitedWeapons=true`, a mission
option present in the installed DCS MissionOptionsView. Its applicability to AI
has NOT been established; do not describe the aircraft as proven inexhaustible.
Initial native ammo counts and per-aircraft/type SHOT events are compared.
`AMMO_EXCEEDED_INITIAL` requires more launches than the initial count for that
matching type. This can demonstrate extra stores for that type, not every weapon;
absence of the event is not proof that the option failed if too few shots occurred.

As the user's explicitly offered alternative, both A-10s also receive a larger
ordinary load: six AGM-65D, six Mk-82 (triple racks on stations 4/8), two GBU-12
(stations 5/7), seven Hydra HEAT (station 2), targeting pod and full cannon.
Stores are checked against installed pydcs station compatibility. No visibility,
route, skill or weapon-count difference is introduced BETWEEN 40A and 40B.
These are test-only settings, not campaign plugin changes.

Files are directly under Missions: `40A_Realistic_CAS_battle_OFF.miz` and
`40B_Realistic_CAS_battle_ON.miz`; hashes/configuration in `combat-40/` outside
Missions. Engine results pending. Automated suite: 79 passing tests, including
HOLD FIRE never transitioning to OPEN FIRE and ammo claims requiring evidence.

## Completed 40: one OFF and two ON runs

Full log archived in `combat-40/dcs-results.log`. Identify these runs by hash
`519218aa80b8a98dd06d6e5da811aabebb64ffde29bb6259a1bdfa214d118cec`:
OFF 20:04:03–20:09:48 (log timestamps), ON 20:10:11–20:10:47,
ON repeat 20:11:08–20:11:57. Each reached 1800 simulated seconds.

| Run | Red alive | Damaged survivors | Red dead | Native CAS credit | Unattributed deaths |
| --- | ---: | ---: | ---: | ---: | ---: |
| OFF | 1 | 1 | 23 | 19 | 4 |
| ON first | 10 | 4 | 14 | 13 | 1 |
| ON repeat | 3 | 3 | 21 | 16 | 5 |

All three: two living undamaged A-10s, all 12 blue ground units alive,
zero ground firing events, zero script errors and zero instrumentation
inconclusives. These controls remove the aircraft-loss and ground-fire confounds
of the previous test. Total red deaths are not silently reclassified as confirmed
CAS credits when the native KILL event lacks an identifiable initiator.

Each aircraft in EVERY run launched its complete original external load:
6 AGM-65D, 6 Mk-82, 2 GBU-12, 7 Hydra HEAT. No
AMMO_EXCEEDED_INITIAL event occurred. At the final native ammo sample only cannon
ammunition remained (OFF 508/1035, first ON 324/236, repeat ON 515/743).
The unlimitedWeapons option therefore did not produce replenished external
stores in these AI trials. Do not use it as a demonstrated infinite-AI-ammo mechanism.
The comparison used the same generous FINITE load, fully expended in each run.

Both ON runs show 12 completed acquisitions (all red groups), exclusively
aircraft EO in the recorded first-reveal samples; no blanket ground discovery.
In the first ON, SEARCH_COMPLETE progresses from mission-time126.051s to781.551s;
the repeat also starts at126.051s and reaches its last group around810s.
Do not treat FIRST_REVEAL's `observedAt` as the exact original acquisition time:
that 30s snapshot can contain a later renewal; use SEARCH_COMPLETE/REVEAL instead.
The first CAS weapon was fired at elapsed131.4s OFF, 147.4s first ON and149.6s repeat.
Final sensor errors were zero in both ON runs; completed searches12/12, resets15/23,
LOS checks2066/1361, scheduler work81068/71315. These counts are not DCS FPS measurements.

Interpretation: controlled evidence that gradual discovery operates during native
CAS without preventing normal attacks or requiring fewer weapons to be released.
The ON outcome is highly variable (14 versus21 deaths), so it does NOT establish
a reproducible casualty-reduction percentage or certify the 20s/600s tuning as
final. All groups eventually being found also means this is delayed knowledge,
not a permanent immunity mask. Real wall-clock durations differ greatly; do not
infer plugin performance or assume identical time acceleration from these logs.

## Next controlled load: 41 APKWS (engine results pending)

At the user's request, revision41 adds APKWS. Each A-10 carries49 AGR-20A
(two triple seven-round LAU-131 racks on stations4/8 and one seven-round pod on2),
six AGM-65D, two GBU-12, targeting pod and cannon. These replace40's six Mk-82
and seven unguided Hydra rounds; station compatibility is checked against pydcs.
No additional JTAC is supplied. Native AI use/self-designation is to be observed
through the existing weapon and damage logs, not assumed from payload validity.

UnlimitedWeapons is explicitly false after the40 result. Comparing parsed41A to
40A, removing only payloads and normalizing that option yields identical mission
data outside the instrumentation triggers. 41A and41B are identical outside those
triggers. Both retain HOLD FIRE on all vehicles, the24km ground spread and the
central FLOT START/END route; no new spacing or sensor tuning is mixed into this
load comparison. The user considers campaign fronts generally more dispersed,
so these tests should not be presented as a full campaign geometry sample.

Generated in Missions root: `41A_Realistic_CAS_battle_OFF.miz` and
`41B_Realistic_CAS_battle_ON.miz`. Evidence/config/hashes in `combat-41/` outside
Missions. Same instructions: log only, equal acceleration,1800 simulated seconds,
without restarting DCS between runs. Python/Lua suite remains79 passing tests.

## Revision42: four A-10s and small JDAMs

The user reports APKWS performing poorly against the T-72s preferred by native
CAS, and requests small JDAMs plus four aircraft. That observation is not a
general weapons-effectiveness calibration. A copy of the available log was
preserved as `combat-41/dcs-observation.log` before the next tests.

Generated `42A_Realistic_CAS_battle_OFF.miz` and
`42B_Realistic_CAS_battle_ON.miz` in Missions root. Each contains one four-ship
Average AI A-10C II flight, each aircraft carrying six AGM-65D, four GBU-38 500lb
JDAMs, pod and cannon. APKWS are removed completely; the two GBU-12 positions
also become GBU-38, giving four JDAM stations (4/5/7/8) while preserving Maverick
racks on3/9. Station2 is empty because it has no GBU-38 capability in pydcs.
Total flight stores:24 Mavericks and16 JDAMs. No change to target geometry,
central CAS route, visibility parameters, finite ammo or permanent ground HOLD
FIRE. The fourth and third aircraft are exported as observers and logged normally.

Validation:79 unit tests passing; Lua/MIZ and pydcs parsing; four AI aircraft,
four compatible JDAM stations each, no APKWS; identical A/B mission data outside
instrumentation triggers. Metadata/hash evidence in `combat-42/` outside Missions.
Native engine results pending. Same log-only instructions as41.

## Revision43: return to two A-10s, retaining JDAMs

The user completed42 and reports excessive CAS effectiveness, requesting only
the flight size reduction back to two. Its available log was preserved in
`combat-42/dcs-results.log`; detailed attribution analysis is not asserted here.

Generated43A OFF /43B ON in Missions root, metadata in `combat-43/`. Each has two
Average AI A-10C II, each retaining six AGM-65D, four GBU-38, targeting pod and
cannon (flight total12 Mavericks and8 JDAMs). All ground units retain HOLD FIRE.
Parsed mission comparison against42, after removing aircraft3/4 and excluding
instrumentation triggers, is exactly equal: no payload, route, geometry, target,
weather or option changes. Both43 variants are also exactly equal outside those
triggers. Lua/pydcs parsing, hashes and79 automated tests pass. Engine results
pending; log only through1800 simulated seconds at equal acceleration.

## Revision43 results and closure of the isolated combat trial

Evidence archived in `realistic-cas-test-results/combat-43/dcs-results.log`.
Select scenario hash
`879343edad39a5cb9e8843085edd57b54b127c9a60b4b0d592c2a16a5515254f`;
the same log also contains earlier revisions. OFF ran at log timestamps
21:08:09–21:08:27, ON at21:08:45–21:09:10, both1800 simulated seconds.

| Run | Red alive /24 | Red dead | Native CAS credit | Unattributed deaths | A-10 alive /2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| OFF | 0 | 24 | 17 | 7 | 2 |
| ON | 11 | 13 | 10 | 3 | 1 |

ON survivors: one south (damaged), two center, all eight north. Both runs retain
all12 blue ground units undamaged, zero ground firing, zero script errors and
zero harness inconclusives. OFF expends12 Mavericks and8 GBU-38; ON expends10
Mavericks and4 GBU-38. The ON survivor expends its full external load.

IMPORTANT CONFOUND: ON BLUE_CAS-1 crashes at elapsed520.0s (8m40s), previousHits=0,
nativeKiller=nil, after firing four Mavericks and no JDAMs. It had been flying
low, with MSL samples around300–420m; these are NOT AGL measurements. This log
does not establish the cause of the crash. The large casualty difference cannot
be attributed entirely to fog: ON loses an aircraft with two Mavericks and four
JDAMs unspent. The harness's inconclusive=0 only certifies its limited automatic
checks, not a confound-free balance experiment.

ON still completes all12 group acquisitions,19 search resets,723 LOS checks,
72048 scheduler work items, zero sensor errors. Last SEARCH_COMPLETE is at mission
time1117.801s. First-reveal snapshots report aircraft EO, not blanket ground
discovery. All groups are eventually discovered; survival does not imply permanent
invisibility. No FPS or precise casualty-reduction percentage is inferred.

The user accepts closure of this isolated combat test series. Taken together with
the clean revision40 trials and prior mechanism tests, native CAS attacks after
gradual discovery and the prototype is ready to proceed toward campaign integration.
Do not generate another balance MIZ merely to chase a preferred casualty ratio.
Final tuning and campaign-scale validation remain separate;43 alone is not a clean
quantitative efficacy measurement because of the crash.
