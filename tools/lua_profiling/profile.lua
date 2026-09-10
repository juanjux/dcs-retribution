-- Cost of one repeating Lua tick, measured inside the mission environment.
--
-- Two instruments, because neither answers alone:
--   * debug.sethook counts VM instructions. DCS never sanitises `debug`, the
--     resolution is fine enough to see a tick, and it is linear in the work the
--     budgets meter -- so it is the one to compare two builds with. It is not
--     free: one Lua callback per 1000 instructions, which is why this is a
--     profiling run and not something to leave on.
--   * os.clock gives real CPU seconds, which is what a frame time is made of,
--     but DCS removes `os` unless something desanitised MissionScripting.lua,
--     and on Windows its resolution is about a millisecond -- far coarser than
--     one tick. So it is accumulated over the whole window and reported as
--     milliseconds per second, never per tick.
-- collectgarbage("count") is free and worth reading: a Lua tick that stutters a
-- mission usually does it by allocating, not by counting.
LuaTickProfile = LuaTickProfile or {}

function LuaTickProfile.new(name, report, every)
  every = every or 60
  local clock = rawget(_G, "os") and os.clock or nil
  local counted = 0
  local hook = function() counted = counted + 1000 end
  local samples, ticks, allocated, seconds = {}, 0, 0, 0
  local windowStart, nextReport

  local function percentile(sorted, p)
    if #sorted == 0 then return 0 end
    return sorted[math.max(1, math.ceil(#sorted * p))]
  end

  local api = {}

  function api:wrap(now, fn, ...)
    if not nextReport then windowStart, nextReport = now, now + every end
    local kb = collectgarbage("count")
    local t0 = clock and clock() or nil
    counted = 0
    debug.sethook(hook, "", 1000)
    local ok, err = pcall(fn, ...)
    debug.sethook()
    if t0 then seconds = seconds + (clock() - t0) end
    allocated = allocated + math.max(0, collectgarbage("count") - kb)
    ticks = ticks + 1
    samples[#samples + 1] = counted

    if now >= nextReport then
      table.sort(samples)
      local elapsed = math.max(0.001, now - windowStart)
      local line = string.format(
        "%s|ticks=%d|vm_p50=%d|vm_p99=%d|vm_max=%d|kb_per_tick=%.2f",
        name, ticks, percentile(samples, 0.50), percentile(samples, 0.99),
        percentile(samples, 1.0), allocated / math.max(1, ticks))
      if clock then
        line = line .. string.format("|cpu_ms_per_second=%.3f|cpu_share=%.4f",
          seconds * 1000 / elapsed, seconds / elapsed)
      else
        line = line .. "|cpu=unavailable(os sanitised)"
      end
      report(line)
      samples, ticks, allocated, seconds = {}, 0, 0, 0
      windowStart, nextReport = now, now + every
    end
    return ok, err
  end

  return api
end
