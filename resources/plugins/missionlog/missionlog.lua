-- Mission Log: a running commentary of what happens to your side.
--
-- DCS already knows everything that happens; what it will not tell you is who
-- it happened to. A kill event names a unit "STAG BARCAP|2|14|F-15C Eagle| Pilot
-- #2", which is unreadable mid-flight, and says nothing about the pilot flying
-- it. Retribution knows the pilot, so the mission generator seeds
-- RETRIBUTION_PILOTS with the name behind every unit and this script turns the
-- raw events into sentences.
--
-- Every message goes to one coalition only: the side it is news for. A kill is
-- news for the shooter's side, the same kill is a loss for the other, and each
-- side can switch its own categories off.

MISSION_LOG_DEFAULTS = {
    airkills = true,
    groundkills = true,
    damage = false,
    losses = true,
    crashes = true,
    flightstatus = false,
    intercepts = true,
    duration = 20,
}

local function option(name)
    local fallback = MISSION_LOG_DEFAULTS[name]
    if dcsRetribution == nil or dcsRetribution.plugins == nil then
        return fallback
    end
    local plugin = dcsRetribution.plugins.missionlog
    if plugin == nil or plugin[name] == nil then
        return fallback
    end
    return plugin[name]
end

local DURATION = tonumber(option("duration")) or MISSION_LOG_DEFAULTS.duration

local logger = mist and mist.Logger:new("MissionLog", "info") or nil

local function announce(side, category, text)
    if not option(category) then
        return
    end
    trigger.action.outTextForCoalition(side, text, DURATION, false)
    if logger then
        logger:info(string.format("[%s] %s", category, text))
    end
end

-- Retribution names a flight's units "<target> <task>|<country>|<n>|<aircraft>|
-- Pilot #<n>", so the aircraft the player recognises is already in the name --
-- no unit-type lookup table needed, and mod aircraft come out right too.
local function fields_of(name)
    local fields = {}
    for field in string.gmatch(tostring(name) .. "|", "([^|]*)|") do
        fields[#fields + 1] = field
    end
    return fields
end

local function pilot_of(unit, name)
    if type(RETRIBUTION_PILOTS) == "table" and RETRIBUTION_PILOTS[name] then
        return RETRIBUTION_PILOTS[name]
    end
    -- A human in the seat outranks the roster: the slot may be flown by anyone.
    local player
    if pcall(function() player = unit:getPlayerName() end) and player then
        return player
    end
    return nil
end

-- What to call something in a sentence. Aircraft get their pilot, ground units
-- get the readable half of their name ("0379 | SAM SA-8 Osa 'Gecko' TEL"), and
-- anything unrecognised falls back to its DCS type.
local function describe(unit)
    if unit == nil then
        return "something"
    end
    local name, kind
    if not pcall(function() name = unit:getName() end) or name == nil then
        return "something"
    end
    pcall(function() kind = unit:getTypeName() end)
    name = tostring(name)

    local readable = string.match(name, "^%d+%s*|%s*(.+)$")
    if readable then
        return "the " .. readable
    end

    local fields = fields_of(name)
    local aircraft = fields[4]
    if aircraft == nil or aircraft == "" then
        aircraft = kind or "aircraft"
    end
    local pilot = pilot_of(unit, name)
    if pilot then
        return string.format("%s flown by %s", aircraft, pilot)
    end
    return "the " .. aircraft
end

local function side_of(unit)
    local side
    if pcall(function() side = unit:getCoalition() end) then
        return side
    end
    return nil
end

local function is_aircraft(unit)
    local category
    if not pcall(function() category = unit:getDesc().category end) then
        return false
    end
    return category == Unit.Category.AIRPLANE or category == Unit.Category.HELICOPTER
end

local function weapon_name(event)
    local name
    if event.weapon ~= nil and pcall(function() name = event.weapon:getTypeName() end) then
        return name
    end
    -- A gun kill carries no weapon object.
    return nil
end

local function with_weapon(text, event)
    local weapon = weapon_name(event)
    if weapon then
        return text .. " with a " .. weapon
    end
    return text .. " with cannon fire"
end

local function place_name(event)
    local name
    if event.place ~= nil and pcall(function() name = event.place:getName() end) then
        return tostring(name)
    end
    return nil
end

-- A shot-down aircraft fires S_EVENT_KILL and then S_EVENT_CRASH. Without this
-- the crash would be reported a second time as if nobody had shot it.
local killed = {}

local function remember_killed(unit)
    local name
    if pcall(function() name = unit:getName() end) and name then
        killed[tostring(name)] = true
    end
end

local function was_killed(unit)
    local name
    if pcall(function() name = unit:getName() end) and name then
        return killed[tostring(name)] == true
    end
    return false
end

local handler = {}

function handler:onEvent(event)
    local id = event.id
    local e = world.event

    if id == e.S_EVENT_KILL and event.initiator and event.target then
        local shooter, victim = side_of(event.initiator), side_of(event.target)
        local killer_text = describe(event.initiator)
        local victim_text = describe(event.target)
        if is_aircraft(event.target) then
            remember_killed(event.target)
            if shooter then
                announce(shooter, "airkills",
                    with_weapon(string.format("%s shot down %s", killer_text, victim_text), event))
            end
            if victim then
                announce(victim, "losses",
                    with_weapon(string.format("%s was shot down by %s", victim_text, killer_text), event))
            end
        elseif shooter then
            announce(shooter, "groundkills",
                with_weapon(string.format("%s destroyed %s", killer_text, victim_text), event))
        end
        return
    end

    if id == e.S_EVENT_HIT and event.initiator and event.target then
        local shooter = side_of(event.initiator)
        if shooter and not is_aircraft(event.target) then
            announce(shooter, "damage",
                with_weapon(string.format("%s hit %s", describe(event.initiator),
                    describe(event.target)), event))
        end
        return
    end

    if id == e.S_EVENT_EJECTION and event.initiator then
        local side = side_of(event.initiator)
        if side then
            announce(side, "losses", string.format("%s ejected", describe(event.initiator)))
        end
        return
    end

    if id == e.S_EVENT_CRASH and event.initiator then
        if was_killed(event.initiator) then
            return
        end
        local side = side_of(event.initiator)
        if side then
            announce(side, "crashes", string.format("%s crashed", describe(event.initiator)))
        end
        return
    end

    if id == e.S_EVENT_TAKEOFF and event.initiator then
        local side = side_of(event.initiator)
        if side then
            local place = place_name(event)
            local text = string.format("%s took off", describe(event.initiator))
            if place then
                text = text .. " from " .. place
            end
            announce(side, "flightstatus", text)
        end
        return
    end

    if id == e.S_EVENT_LAND and event.initiator then
        local side = side_of(event.initiator)
        if side then
            local place = place_name(event)
            local text = string.format("%s landed", describe(event.initiator))
            if place then
                text = text .. " at " .. place
            end
            announce(side, "flightstatus", text)
        end
        return
    end
end

world.addEventHandler(handler)

-- Interceptions.
--
-- DCS fires no event for "I have seen him and I am going after him", so this is
-- polled: every fighter group is asked what its radar holds and what the
-- datalink handed it, which is the same getDetectedTargets call the EWRS plugin
-- has been using all along. A contact is announced once, and only the first
-- time, so a long tail chase does not repeat itself every sweep.
INTERCEPT_POLL_SECONDS = 20
INTERCEPT_MAX_RANGE_M = 148160 -- 80 nm: past this it is a blip, not an intercept

local announced_contacts = {}

local function detected_names(controller, method)
    local seen = {}
    local contacts
    if not pcall(function() contacts = controller:getDetectedTargets(method) end) then
        return seen
    end
    for _, contact in pairs(contacts or {}) do
        local name
        if contact.object ~= nil and pcall(function() name = contact.object:getName() end) then
            if name ~= nil then
                seen[tostring(name)] = contact.object
            end
        end
    end
    return seen
end

local function is_fighter(unit)
    local fighter = false
    pcall(function()
        fighter = unit:hasAttribute("Fighters") or unit:hasAttribute("Interceptors")
    end)
    return fighter
end

local function range_between(a, b)
    local pa, pb
    if not pcall(function() pa, pb = a:getPoint(), b:getPoint() end) then
        return nil
    end
    if pa == nil or pb == nil then
        return nil
    end
    local dx, dy, dz = pa.x - pb.x, pa.y - pb.y, pa.z - pb.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)
end

local function report_contacts(hunter, targets, source)
    local hunter_name
    if not pcall(function() hunter_name = hunter:getName() end) or hunter_name == nil then
        return
    end
    local side = side_of(hunter)
    if side == nil then
        return
    end
    for name, target in pairs(targets) do
        local key = tostring(hunter_name) .. "->" .. name
        if not announced_contacts[key] then
            local target_side = side_of(target)
            local range = range_between(hunter, target)
            if target_side ~= nil and target_side ~= side and is_aircraft(target)
                    and range ~= nil and range <= INTERCEPT_MAX_RANGE_M then
                announced_contacts[key] = true
                announce(side, "intercepts", string.format(
                    "%s is moving to intercept %s at %.0f nm, %s",
                    describe(hunter), describe(target), range / 1852, source))
            end
        end
    end
end

local function poll_intercepts()
    if not option("intercepts") then
        return
    end
    for _, side in pairs({coalition.side.BLUE, coalition.side.RED}) do
        local groups
        if not pcall(function()
            groups = coalition.getGroups(side, Group.Category.AIRPLANE)
        end) then
            groups = nil
        end
        for _, group in pairs(groups or {}) do
            local unit
            if pcall(function() unit = group:getUnit(1) end) and unit ~= nil
                    and is_fighter(unit) then
                local controller
                if pcall(function() controller = group:getController() end)
                        and controller ~= nil then
                    -- Own radar wins the credit: a target held on both was not
                    -- "handed over", it was found.
                    local radar = detected_names(controller, Controller.Detection.RADAR)
                    report_contacts(unit, radar, "found on its own radar")
                    local shared = detected_names(controller, Controller.Detection.DLINK)
                    for name in pairs(radar) do
                        shared[name] = nil
                    end
                    report_contacts(unit, shared, "handed over by shared awareness")
                end
            end
        end
    end
end

timer.scheduleFunction(function(_, time)
    pcall(poll_intercepts)
    return time + INTERCEPT_POLL_SECONDS
end, nil, timer.getTime() + INTERCEPT_POLL_SECONDS)

if logger then
    -- RETRIBUTION_PILOTS is keyed by unit name, so # would report 0.
    local roster = 0
    if type(RETRIBUTION_PILOTS) == "table" then
        for _ in pairs(RETRIBUTION_PILOTS) do
            roster = roster + 1
        end
    end
    logger:info(string.format(
        "Mission Log armed: roster of %d pilots, messages last %ds", roster, DURATION))
end
