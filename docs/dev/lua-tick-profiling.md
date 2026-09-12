# Profiling a plugin's tick inside DCS

For a plugin that runs work on `timer.scheduleFunction`, the question is what one
tick costs and whether it is what a mission's stutter is made of. Frame-time
capture answers neither: it cannot separate this plugin from the rest of the
mission.

## What DCS actually offers

Checked against a stock install rather than assumed:

- **Not LuaJIT.** `bin/lua.dll` is plain Lua 5.1, so `jit.profile` does not exist.
- **`debug` is not sanitised.** `Scripts/MissionScripting.lua` removes `os`, `io`,
  `lfs`, `require` and `package` — and nothing else. `debug.sethook`,
  `debug.getinfo` and `collectgarbage` are there in a stock DCS.
- **`os.clock` is conditional.** It exists only while something has desanitised
  MissionScripting.lua, which Retribution does while it is running and undoes when
  it closes. On Windows its resolution is about a millisecond, far coarser than
  one tick, so it is only meaningful accumulated over a window.

## What this measures

| field | from | what it is for |
| --- | --- | --- |
| `vm_p50` / `vm_p99` / `vm_max` | `debug.sethook` | VM instructions in a tick. Linear in the work done, fine enough to see one tick, and comparable between two builds. |
| `cpu_ms_per_second`, `cpu_share` | `os.clock` | The share of real time the tick takes. This is the one that says whether it costs frames. Absent, and said to be absent, when `os` is sanitised. |
| `kb_per_tick` | `collectgarbage` | A Lua tick that stutters a mission usually does it by allocating, not by counting. |

A line per window, on `env.info`:

```
realisticcas.tick|ticks=41|vm_p50=120000|vm_p99=120000|vm_max=120000|kb_per_tick=12.30|cpu_ms_per_second=3.400|cpu_share=0.0034
```

## Where it lives

Its own plugin, `resources/plugins/tickprofile/`, **off by default**: the count hook
costs a Lua callback per thousand instructions, so it is switched on for a
measurement run rather than left in a campaign. It loads immediately after `base`,
before any plugin that might measure itself.

Because it is off by default, a caller cannot assume `LuaTickProfile` is there.

## Wiring it in

Wherever the tick is already scheduled, guarded on the plugin being on. In the
Realistic CAS plugin (`resources/plugins/realisticcas/detectors-dcs.lua`) that is
the `pcall` inside `timer.scheduleFunction`:

```lua
local profiler = rawget(_G, "LuaTickProfile")
local profile = profiler and profiler.new("realisticcas.tick",
  function(line) env.info("PROFILE|" .. line) end)
...
local ok, err
if profile then
  ok, err = profile:wrap(now, function() engine:tick() end)
else
  ok, err = pcall(function() engine:tick() end)
end
```

The reporting window comes from the plugin's own *Seconds between reports* option
when the caller does not give one.

## The cost of measuring

The count hook is one Lua callback per 1000 instructions, so it is not free: this
is for a measurement run, not for leaving on. `os.clock` and `collectgarbage` are
cheap enough to ignore.
