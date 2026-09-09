# Realistic CAS: first experimental campaign integration

## Scope decision

After closing combat trial43, the user explicitly deferred replacement JTACs:
legacy plugin JTACs / native JTAC generation may be disabled for now. This removes
the need to hold campaign wiring hostage to a complete JTAC adapter.

The implementation exposes Realistic CAS as experimental, default false. It
suppresses only the generated legacy JTAC path while enabled; no faction/settings
mutation. The existing frontline metadata append remains outside that suppression.
CTLD, TIC and Moose Autolase cause a clear generation error when enabled alongside
Realistic CAS. CTLD is restricted as a whole because its runtime-created infantry,
vehicles and omniscient assault helpers also need an ownership/detection adapter;
turning its autolase option off alone does not solve that.

## Wiring

- `LuaGenerator.generate` preflights config using the same plugin-manager state as
  ordinary injection; disabled returns before reading registry/environment data.
- Read-only registry identifies fixed SAM objectives by UnitMap membership, not
  unit type. Frontline SAMs are not exempt. Native routes, ROE and payload unchanged.
- Reads final pydcs date/weather after ordinary/live-weather generation. Supplies
  the campaign reference coordinates/timezone to the existing solar calculator.
- Three daily schedules support midnight. Polar illumination is a declared
  constant-day/night approximation; a daily schedule beyond the horizon repeats.
- Cloud presets often have numeric density/thickness zero. Use authored descriptive
  text for an explicit approximate slab, not reusable PresetNN identifiers. Unknown
  descriptions use a logged fallback, never silently clear weather. Optical and IR
  attenuation remain independent. Ordinary numeric weather retains its cloud base
  and thickness; unsupported zero thickness with nonzero density warns/falls back.
- Reads final visibility and dust. Inactive default fog visibility25 is ignored;
  manual fog is a declared uniform visibility limit. Automatic native fog has no
  density estimate here and logs that limitation rather than fabricating one.
- Biome is explicit, homogeneous approximation selected by theater/manual option;
  no town/forest classifier inferred from terrain surface type or objective names.
- Seven source files loaded in dependency order followed by typed startup action.
  Missing file preflight rejects partial plugin injection. Startup retains existing
  rollback and visibility-restoration behavior. Environment limitations appear in
  Python generation logs and Lua startup warnings even with debug off.

## Verification

97 automated tests pass (no duplicated imported test classes). Newly exercised:

- Final pydcs weather/date export, awareness/timezone conversion, next-day schedule,
  polar days/nights, wrapped solar days and midnight twilight.
- Preset zero density, same preset key/different description, unknown preset fallback,
  cloud numeric bounds, independent IR, inactive/manual/automatic fog and dust.
- Actual plugin JSON loader: options and default disabled state.
- Actual LuaGenerator hook/injector with pydcs fixture; real campaign solar calculator.
- Disabled path without accessible mission objects; option source; incompatibility
  rejection; explicit legacy JTAC rejection; missing-file preflight.
- Save/reload temporary MIZ, source-file order, compile every Lua source, whole
  mission Lua and embedded trigger action strings with Lua5.1.
- Structural regression: suppressing JTAC does not suppress frontline metadata.

This is NOT native acceptance of a full generated campaign. The pydcs fixture is
small, unrelated Lua generators are isolated in the hook test, and the FLOT guard
has a structural test rather than a full campaign fixture. No new native test
mission was delivered for purely serializing/configuring this boundary.

## Remaining acceptance and implementation

Next: full campaign generation smoke, enabled/disabled comparison (including
legacy JTAC suppression), native large-front test and cost/latency measurements.
Do not interpret the existing isolated combat kill ratios as an FPS or performance
benchmark. Unknown third-party dynamic/visibility scripts are not certified.

Replacement vulnerable JTACs, coordinated MOOSE/TIC/CTLD adapters, spatial cover,
capability-table expansion, lifecycle/performance tuning and final README/API/
howtoplay documentation remain work before calling the full feature complete.
The original Claude checkout and the running campaign are untouched; all changes
remain in the Realistic CAS worktree, not built/merged/deployed.
