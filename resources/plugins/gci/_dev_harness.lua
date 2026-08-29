-- DEV ONLY. Not shipped into the mission: plugin.json lists gci.lua alone in
-- scriptsWorkOrders, so this file is never injected. Run it against the plugin with
--   "<DCS>/bin/luae.exe" _dev_harness.lua gci.lua
-- It fakes enough of the DCS scripting API to exercise one cycle offline.

-- Offline harness for the GCI plugin: fakes just enough of the DCS scripting API to
-- run one cycle and assert who gets vectored. Catches name-matching / IADS-parsing /
-- range-gating mistakes without burning a sortie.

local NM = 1852
local T = 100
local scheduled = nil
local out = {}

env = { info = function(s) print("  [env] " .. s) end }
trigger = { action = { outText = function(t, d) table.insert(out, t); print("  [msg] " .. t) end } }
timer = {
    getTime = function() return T end,
    scheduleFunction = function(f, a, t) scheduled = f end,
}
Group = { Category = { AIRPLANE = 0, HELICOPTER = 1, GROUND = 2, SHIP = 3 } }
Object = { Category = { UNIT = 1 }, getCategory = function(o) return o._cat or 1 end }
coalition = { side = { RED = 1, BLUE = 2 } }
Controller = { Detection = { VISUAL = 1, OPTIC = 2, RADAR = 4, IRST = 8,
                             RWR = 16, DLINK = 32 } }

local byName, allGroups = {}, {}

function Group.getByName(n) return byName[n] end
function coalition.getGroups(sideId, cat)
    local r = {}
    for _, g in ipairs(allGroups) do
        if g.coalitionId == sideId and g.cat == cat then table.insert(r, g) end
    end
    return r
end

local function mkGroup(name, cat, coalitionId, id)
    local g = { name = name, cat = cat, coalitionId = coalitionId, id = id,
                units = {}, pushed = {}, detected = {} }
    g.controller = {
        -- Records the filter so the harness can prove the plugin asks for RADAR only.
        getDetectedTargets = function(_, filter) g.lastFilter = filter; return g.detected end,
        pushTask = function(_, t) table.insert(g.pushed, t) end,
    }
    g.isExist = function() return true end
    g.getName = function() return name end
    g.getUnits = function() return g.units end
    g.getCategory = function() return cat end
    g.getID = function() return id end
    g.getController = function() return g.controller end
    byName[name] = g
    table.insert(allGroups, g)
    return g
end

local function addUnit(g, x, inAir, player)
    local u = {
        _cat = 1,
        isExist = function() return true end,
        getPoint = function() return { x = x, y = 0, z = 0 } end,
        inAir = function() return inAir end,
        getPlayerName = function() return player end,
        getGroup = function() return g end,
        getCoalition = function() return g.coalitionId end,
        getController = function() return g.controller end,
    }
    table.insert(g.units, u)
    return u
end

-- Scenario -----------------------------------------------------------------------
local ewr    = mkGroup("Zone A EWR",                        Group.Category.GROUND,   1, 10)
local capA   = mkGroup("Zone A EWR BARCAP|0|1|MiG-23MLD|",  Group.Category.AIRPLANE, 1, 11)
local capB   = mkGroup("Zone B NoEWR BARCAP|0|2|MiG-23MLD|",Group.Category.AIRPLANE, 1, 12)
local strike = mkGroup("Somewhere STRIKE|0|3|Su-24M|",      Group.Category.AIRPLANE, 1, 13)
local manned = mkGroup("Manned TARCAP|0|4|MiG-23MLD|",      Group.Category.AIRPLANE, 1, 14)
local blue   = mkGroup("Intruder ALPHA into Zone A",        Group.Category.AIRPLANE, 2, 20)

addUnit(ewr, 0, false, nil)
addUnit(capA, 0, true, nil)                    -- over the EWR
addUnit(capB, 228 * NM, true, nil)             -- 228 NM away, the control group
addUnit(strike, 0, true, nil)                  -- co-located, must NOT be diverted
addUnit(manned, 0, true, "Juanjo")             -- player-crewed, must NOT be tasked
local blueUnit = addUnit(blue, 80 * NM, true, nil)

ewr.detected = { { object = blueUnit, visible = true } }

dcsRetribution = {
    plugins = { gci = { DEBUG = true, extraRangeCapNM = 0, divertRangeNM = 90,
                        interceptDuration = 600, updateInterval = 10 } },
    IADS = { RED = { Ewr = { { dcsGroupName = "Zone A EWR" } } }, BLUE = {} },
}

-- Run ------------------------------------------------------------------------------
print("--- loading plugin ---")
local chunk = assert(loadfile(arg[1]))
chunk()
print("--- running one cycle ---")
assert(scheduled, "plugin never scheduled a cycle")
scheduled()

-- Assertions -----------------------------------------------------------------------
local function check(label, ok)
    print(string.format("  [%s] %s", ok and "PASS" or "FAIL", label))
    return ok
end

print("--- results ---")
local allOk = true
allOk = check("EWR was polled with the RADAR detection filter",
    ewr.lastFilter == Controller.Detection.RADAR) and allOk
allOk = check("CAP A (has EWR cover) was vectored", #capA.pushed == 1) and allOk
allOk = check("CAP B (no EWR, 228 NM) was NOT vectored", #capB.pushed == 0) and allOk
allOk = check("STRIKE flight was NOT diverted", #strike.pushed == 0) and allOk
allOk = check("player-crewed TARCAP was NOT tasked", #manned.pushed == 0) and allOk

if #capA.pushed == 1 then
    local t = capA.pushed[1]
    allOk = check("task is a ControlledTask wrapper", t.id == "ControlledTask") and allOk
    allOk = check("inner task is EngageGroup", t.params.task.id == "EngageGroup") and allOk
    allOk = check("targets the blue group id", t.params.task.params.groupId == 20) and allOk
    allOk = check("has a duration stop condition",
        t.params.stopCondition and t.params.stopCondition.duration == 600) and allOk
end

-- Second cycle: must not re-task an already-committed flight.
scheduled()
allOk = check("no duplicate tasking on the next cycle", #capA.pushed == 1) and allOk

-- After the intercept duration elapses the flight is released again.
T = T + 601
scheduled()
allOk = check("assignment expires and frees the flight",
    #capA.pushed == 2) and allOk

print(allOk and "\nALL CHECKS PASSED" or "\nSOME CHECKS FAILED")
os.exit(allOk and 0 or 1)
