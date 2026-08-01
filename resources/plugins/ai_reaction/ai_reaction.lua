-- Smart Threat Reaction (DCS Retribution — prototype) -----------------------------
--
-- Problem: with DCS' default "Evade Fire", a single SAM launch makes EVERY aircraft
-- that merely *perceives* the threat break defensive. One Type-055 (HHQ-9) salvo
-- sends dozens of aircraft from unrelated packages scattering, even the ~43 that
-- have no missile guiding on them.
--
-- This keeps every aircraft at "Passive Defense" (fly the route, use chaff/flares,
-- do NOT break formation) as a baseline, and switches ONLY the flight a missile is
-- actually guiding on to "Evade Fire" until that missile is gone. The target is read
-- straight from the engine via the native weapon:getTarget() — no geometry guessing.
--
-- Granularity note: the reaction option is per-GROUP, so the *flight* the missile
-- targets (~2-4 jets) evades, not the single jet — still a huge cut from ~45.
--
-- Perf (2026-07-15): kept cheap during a naval battle's missile storm, which was
-- stalling the sim. (1) The baseline sweep only touches groups whose passive state
-- actually needs (re)setting — not a setOption on every airplane every pass; a full
-- re-assert runs only every REASSERT_EVERY-th sweep. (2) Ship/ground-targeting shots
-- (anti-ship, naval SAM at a point) are dropped at the SHOT event with no re-check.
-- (3) Per-event logging is DEBUG-only, so a salvo can't flood the log.
-----------------------------------------------------------------------------------

local DEBUG = false
if dcsRetribution and dcsRetribution.plugins and dcsRetribution.plugins.ai_reaction then
    DEBUG = dcsRetribution.plugins.ai_reaction.DEBUG == true
end

local OPT   = AI.Option.Air.id.REACTION_ON_THREAT
local PASS  = 1  -- PASSIVE_DEFENCE
local EVADE = 2  -- EVADE_FIRE

-- Baseline sweep cadence. Because only state transitions cost a setOption (see the
-- `passive` set), a sweep is nearly free, so it can be relaxed; every REASSERT_EVERY-th
-- sweep re-applies to ALL groups to catch any the engine reset to Evade Fire on
-- activation and to prune destroyed groups. 10 s * 6 = a full re-assert about once a
-- minute (was: a full setOption over every airplane every 5 s).
local BASELINE_INTERVAL = 10
local REASSERT_EVERY    = 6

local threatCount = {}  -- [groupName] -> number of live missiles guiding on it
local live        = {}  -- [weapon userdata] -> groupName it is guiding on
local passive     = {}  -- [groupName] -> true once parked at Passive (and no missile since)

local function dbg(msg)
    if not DEBUG then return end
    env.info("AIReaction| " .. msg)
    trigger.action.outText("AIReaction: " .. msg, 8)
end

-- Log-only (no on-screen text); DEBUG-gated so a naval salvo doesn't flood the log.
local function info(msg)
    if DEBUG then env.info("AIReaction| " .. msg) end
end

local function wname(w)
    local ok, n = pcall(function() return w:getTypeName() end)
    return (ok and n) or "?"
end

-- How many distinct flights are currently evading at least one missile.
local function evadingCount()
    local n = 0
    for _, c in pairs(threatCount) do if (c or 0) > 0 then n = n + 1 end end
    return n
end

local function setOpt(grp, val)
    pcall(function()
        local c = grp:getController()
        if c then c:setOption(OPT, val) end
    end)
end

-- Tag the flight a weapon is guiding on -> Evade Fire.
-- Returns a status: "evade" (tagged), "notarget" (getTarget gave no unit — e.g. a
-- JDAM/GPS weapon aimed at a point, or a lock not resolved yet), or "notair" (target
-- resolved but not an airplane — a ship/ground unit).
local function tryTag(w)
    local ok, tgt = pcall(function() return w:getTarget() end)
    if not ok or not tgt then return "notarget" end
    local okg, grp = pcall(function() return tgt:getGroup() end)
    if not okg or not grp then return "notarget" end
    local okc, cat = pcall(function() return grp:getCategory() end)
    if not okc or cat ~= Group.Category.AIRPLANE then return "notair" end
    local gname = grp:getName()
    setOpt(grp, EVADE)
    threatCount[gname] = (threatCount[gname] or 0) + 1
    live[w] = gname
    passive[gname] = nil  -- evading now; baseline must re-park it at Passive once clear
    dbg("SHOT " .. wname(w) .. " -> EVADE " .. gname .. "  [" .. evadingCount() .. " flights evading]")
    return "evade"
end

-- Baseline: every airplane not currently dodging a missile -> Passive Defense. Only
-- groups not already parked at Passive are touched, so a normal sweep is nearly free;
-- every REASSERT_EVERY-th sweep forgets `passive` and re-applies to all (catches engine
-- resets on activation, prunes destroyed groups).
local passSweep = 0
local function baseline(_, time)
    passSweep = passSweep + 1
    if passSweep % REASSERT_EVERY == 0 then
        passive = {}
    end
    for _, side in pairs({ coalition.side.RED, coalition.side.BLUE }) do
        local ok, groups = pcall(coalition.getGroups, side, Group.Category.AIRPLANE)
        if ok and groups then
            for _, grp in pairs(groups) do
                local okn, gname = pcall(function() return grp:getName() end)
                if okn and gname and not passive[gname] and (threatCount[gname] or 0) == 0 then
                    setOpt(grp, PASS)
                    passive[gname] = true
                end
            end
        end
    end
    return time + BASELINE_INTERVAL
end

-- When a tracked missile no longer exists, release its target (the next baseline pass
-- returns it to Passive Defense once no missiles remain on it).
local function watch(_, time)
    for w, gname in pairs(live) do
        local ok, ex = pcall(function() return w:isExist() end)
        if not (ok and ex) then
            live[w] = nil
            threatCount[gname] = math.max(0, (threatCount[gname] or 1) - 1)
            if (threatCount[gname] or 0) == 0 then
                dbg(gname .. " clear -> Passive  [" .. evadingCount() .. " flights evading]")
            end
        end
    end
    return time + 1
end

local handler = {}
function handler:onEvent(event)
    if not event or event.id ~= world.event.S_EVENT_SHOT or not event.weapon then return end
    local w = event.weapon
    local status = tryTag(w)
    if status == "evade" then return end
    if status == "notair" then
        -- Resolved to a ship/ground target: it can never guide on an airplane, so drop
        -- it here — no 1 s re-check, no log. This is the anti-ship / naval-SAM salvo
        -- storm that was stalling the sim during the Chinese naval attack.
        return
    end
    -- "notarget": the lock may simply not be resolved at the instant of launch (a real
    -- A2A shot whose target appears a beat later), or it's a JDAM/GPS aimed at a point.
    -- Re-check ONCE after 1 s, then log the definitive outcome (DEBUG only).
    timer.scheduleFunction(function()
        local ok, ex = pcall(function() return w:isExist() end)
        if not (ok and ex) then
            info("SHOT " .. wname(w) .. " -> gone before a target resolved")
        elseif not live[w] then
            if tryTag(w) == "notarget" then
                info("SHOT " .. wname(w) .. " -> not tagged: no unit target (JDAM/GPS to a point)")
            end
            -- "notair" now: a ship/ground target resolved late -> ignore silently.
        end
        return nil
    end, nil, timer.getTime() + 1)
end

world.addEventHandler(handler)
timer.scheduleFunction(baseline, nil, timer.getTime() + 2)
timer.scheduleFunction(watch, nil, timer.getTime() + 3)
env.info("AIReaction| Smart Threat Reaction loaded (DEBUG=" .. tostring(DEBUG) .. ")")
if DEBUG then trigger.action.outText("AIReaction: Smart Threat Reaction active", 15) end
