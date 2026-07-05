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
-----------------------------------------------------------------------------------

local DEBUG = false
if dcsRetribution and dcsRetribution.plugins and dcsRetribution.plugins.ai_reaction then
    DEBUG = dcsRetribution.plugins.ai_reaction.DEBUG == true
end

local OPT   = AI.Option.Air.id.REACTION_ON_THREAT
local PASS  = 1  -- PASSIVE_DEFENCE
local EVADE = 2  -- EVADE_FIRE

local threatCount = {}  -- [groupName] -> number of live missiles guiding on it
local live        = {}  -- [weapon userdata] -> groupName it is guiding on

local function dbg(msg)
    env.info("AIReaction| " .. msg)
    if DEBUG then trigger.action.outText("AIReaction: " .. msg, 8) end
end

local function setOpt(grp, val)
    pcall(function()
        local c = grp:getController()
        if c then c:setOption(OPT, val) end
    end)
end

-- Tag the flight a weapon is guiding on -> Evade Fire. Returns true if tagged.
local function tryTag(w)
    local ok, tgt = pcall(function() return w:getTarget() end)
    if not ok or not tgt then return false end
    local okg, grp = pcall(function() return tgt:getGroup() end)
    if not okg or not grp then return false end
    local okc, cat = pcall(function() return grp:getCategory() end)
    if not okc or cat ~= Group.Category.AIRPLANE then return false end
    local gname = grp:getName()
    setOpt(grp, EVADE)
    threatCount[gname] = (threatCount[gname] or 0) + 1
    live[w] = gname
    dbg("missile -> " .. gname .. " : EVADE")
    return true
end

-- Baseline: every airplane not currently dodging a missile -> Passive Defense.
-- Runs periodically so late-spawning flights (and any that the engine reset to
-- Evade Fire on activation) are brought back to the passive baseline.
local function baseline(_, time)
    for _, side in pairs({ coalition.side.RED, coalition.side.BLUE }) do
        local ok, groups = pcall(coalition.getGroups, side, Group.Category.AIRPLANE)
        if ok and groups then
            for _, grp in pairs(groups) do
                local okn, gname = pcall(function() return grp:getName() end)
                if okn and gname and (threatCount[gname] or 0) == 0 then
                    setOpt(grp, PASS)
                end
            end
        end
    end
    return time + 5
end

-- When a tracked missile no longer exists, release its target (the next baseline
-- pass returns it to Passive Defense once no missiles remain on it).
local function watch(_, time)
    for w, gname in pairs(live) do
        local ok, ex = pcall(function() return w:isExist() end)
        if not (ok and ex) then
            live[w] = nil
            threatCount[gname] = math.max(0, (threatCount[gname] or 1) - 1)
            if (threatCount[gname] or 0) == 0 then dbg(gname .. " clear -> Passive") end
        end
    end
    return time + 1
end

local handler = {}
function handler:onEvent(event)
    if not event or event.id ~= world.event.S_EVENT_SHOT or not event.weapon then return end
    local w = event.weapon
    if not tryTag(w) then
        -- Target may not be resolved at the instant of launch; re-check once.
        timer.scheduleFunction(function()
            local ok, ex = pcall(function() return w:isExist() end)
            if ok and ex and not live[w] then tryTag(w) end
            return nil
        end, nil, timer.getTime() + 1)
    end
end

world.addEventHandler(handler)
timer.scheduleFunction(baseline, nil, timer.getTime() + 2)
timer.scheduleFunction(watch, nil, timer.getTime() + 3)
env.info("AIReaction| Smart Threat Reaction loaded (DEBUG=" .. tostring(DEBUG) .. ")")
if DEBUG then trigger.action.outText("AIReaction: Smart Threat Reaction active", 15) end
