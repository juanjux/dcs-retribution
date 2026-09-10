"""The tick profiler runs in the Lua DCS actually gives a mission.

DCS ships plain Lua 5.1, not LuaJIT, and MissionScripting.lua removes os/io/lfs and
leaves `debug` alone. So the instrument has to work with `os` missing, and the one
that is always there -- the count hook -- has to be sensitive enough to tell two
loads apart.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lupa.lua51 import LuaRuntime

PROFILER = (
    Path(__file__).resolve().parent.parent / "tools/lua_profiling/profile.lua"
).read_text(encoding="utf-8")

DRIVER = """
lines = {}
local p = LuaTickProfile.new("tick", function(s) lines[#lines+1] = s end, 5)
local function busy(n)
  local t, x = {}, 0
  for i = 1, n do x = x + i %% 7; t[#t+1] = i end
  return x
end
local now = 0
for i = 1, 40 do now = i * 0.25; p:wrap(now, busy, %d) end
"""


def _run(load: int, sanitised: bool) -> str:
    lua = LuaRuntime()
    if sanitised:
        lua.execute("os = nil")  # what DCS does to a stock mission environment
    lua.execute(PROFILER)
    lua.execute(DRIVER % load)
    lines = lua.globals().lines
    assert len(lines) >= 1, "no report inside the window"
    return str(lines[1])


def _field(line: str, name: str) -> float:
    for part in line.split("|"):
        key, _, value = part.partition("=")
        if key == name:
            return float(value)
    raise AssertionError(f"{name} missing from {line}")


@pytest.mark.parametrize("sanitised", [False, True])
def test_it_reports_in_either_environment(sanitised: bool) -> None:
    line = _run(20000, sanitised)
    assert _field(line, "vm_p50") > 0
    assert _field(line, "ticks") > 0
    if sanitised:
        assert "cpu=unavailable" in line, "it must say so, not report a zero"
    else:
        assert _field(line, "cpu_share") >= 0


def test_the_instruction_count_tracks_the_work_done() -> None:
    """A profiler that cannot tell 10x apart is not measuring anything."""
    light = _field(_run(20000, sanitised=True), "vm_p50")
    heavy = _field(_run(200000, sanitised=True), "vm_p50")
    assert heavy > light * 5, f"{light} -> {heavy}"


def test_allocation_is_reported_separately_from_time() -> None:
    """GC pressure is the usual way a Lua tick costs frames."""
    assert _field(_run(20000, sanitised=True), "kb_per_tick") > 0
