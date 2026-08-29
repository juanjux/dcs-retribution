-- GCI / Ground Controlled Intercept (DCS Retribution - prototype) ------------------
--
-- Problem: Retribution's EWR sites get the DCS "EWR" enroute task and emit, but
-- nothing ever acts on what they see. There is no GCI in the generated mission:
-- the native ActivateGCI command needs the dedicated GCI_station unit (a MiG-29
-- datalink truck with 10 m detection range) and pydcs does not implement it, and no
-- bundled script vectors fighters. A red CAP flies its planned racetrack whether or
-- not an EWR 200 km away is painting the inbound strike.
--
-- This closes that loop the cheap way: every cycle each living EWR is asked what it
-- detects (the same Controller:getDetectedTargets() call Skynet uses), and any
-- friendly fighter flight loitering within reach is handed a bounded intercept task
-- against the nearest contact.
--
-- SYMMETRY IS THE POINT. This runs for BOTH coalitions off the same data and the
-- same thresholds. A one-sided version would just be a difficulty knob; making both
-- GCI networks react is what keeps a campaign balanced for a player who rarely gives
-- in-mission orders and simply flies.
--
-- Design constraints (learned the hard way elsewhere in this fork):
--   * NEVER spawn aircraft. MOOSE's AI_A2A_DISPATCHER would do GCI out of the box
--     but it owns spawning, which would hand out free jets outside the campaign
--     inventory and create units absent from Retribution's unit_map, so their deaths
--     would never be scored. Only already-planned flights are re-tasked.
--   * Only fighter flights are eligible (BARCAP / TARCAP / Fighter sweep). Diverting
--     a strike or SEAD package would wreck its TOT and its objective.
--   * pushTask, never setTask: setTask would erase the flight's planned route.
--   * The pushed task is wrapped in a ControlledTask with a duration stop condition
--     so it expires and unwinds itself. Nothing here calls popTask, because if the
--     AI already finished and popped the intercept, our pop would eat the ROUTE task
--     underneath and strand the flight.
--   * Player-crewed flights are never tasked.
-----------------------------------------------------------------------------------

local DEBUG              = true
local DETECTION_RANGE_NM = 150
local DIVERT_RANGE_NM    = 60
local INTERCEPT_DURATION = 300
local UPDATE_INTERVAL    = 15

if dcsRetribution and dcsRetribution.plugins and dcsRetribution.plugins.gci then
    local o = dcsRetribution.plugins.gci
    if o.DEBUG ~= nil then DEBUG = o.DEBUG == true end
    DETECTION_RANGE_NM = tonumber(o.detectionRangeNM)  or DETECTION_RANGE_NM
    DIVERT_RANGE_NM    = tonumber(o.divertRangeNM)     or DIVERT_RANGE_NM
    INTERCEPT_DURATION = tonumber(o.interceptDuration) or INTERCEPT_DURATION
    UPDATE_INTERVAL    = tonumber(o.updateInterval)    or UPDATE_INTERVAL
end

local NM = 1852
local DETECTION_RANGE = DETECTION_RANGE_NM * NM
local DIVERT_RANGE    = DIVERT_RANGE_NM * NM

-- Flight types allowed to be vectored. These strings come from Retribution's group
-- naming scheme, "<target> <flight type>|<country>|<n>|<variant>|" (game/naming.py),
-- so the mission role is readable straight off the DCS group name with no extra data
-- injected from Python. NOTE: a flight the player renamed (custom_name) loses its
-- type from the name and is simply never cued -- acceptable for a prototype.
local INTERCEPTOR_TAGS = { " BARCAP|", " TARCAP|", " Fighter sweep|" }

local SIDES = {
    { key = "RED",  id = coalition.side.RED },
    { key = "BLUE", id = coalition.side.BLUE },
}

-- [groupName] = { target = <name>, expires = <time> }
local assigned = {}

local function log(msg)
    env.info("GCI| " .. msg)
end

local function announce(msg)
    log(msg)
    if DEBUG then
        trigger.action.outText("GCI: " .. msg, 15)
    end
end

local function dist3(a, b)
    local dx, dy, dz = a.x - b.x, a.y - b.y, a.z - b.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)
end

local function nmText(meters)
    return string.format("%.0f", meters / NM)
end

local function isInterceptorName(name)
    for _, tag in ipairs(INTERCEPTOR_TAGS) do
        if string.find(name, tag, 1, true) then return true end
    end
    return false
end

-- Retribution always emits dcsRetribution.IADS (luagenerator.py builds it from the
-- theater IADS network, which is created in begin_turn_0), so the EWR roster is
-- available even when the Skynet IADS plugin is switched off.
local function ewrGroupNames(sideKey)
    local names = {}
    if not (dcsRetribution and dcsRetribution.IADS) then return names end
    local side = dcsRetribution.IADS[sideKey]
    if not side then return names end
    for _, role in ipairs({ "Ewr", "SamAsEwr" }) do
        if side[role] then
            for _, entry in pairs(side[role]) do
                if entry and entry.dcsGroupName then
                    table.insert(names, entry.dcsGroupName)
                end
            end
        end
    end
    return names
end

-- Every air contact this side's EWRs can currently see, keyed by target group name
-- so several radars painting the same formation collapse into one entry.
local function detectedContacts(sideKey, sideId)
    local contacts = {}
    for _, gname in ipairs(ewrGroupNames(sideKey)) do
        local okg, group = pcall(Group.getByName, gname)
        if okg and group and group:isExist() then
            local ewrPos
            for _, unit in ipairs(group:getUnits() or {}) do
                if unit and unit:isExist() then
                    ewrPos = ewrPos or unit:getPoint()
                    local okc, controller = pcall(function() return unit:getController() end)
                    if okc and controller then
                        local okd, targets = pcall(function()
                            return controller:getDetectedTargets()
                        end)
                        if okd and targets then
                            for _, det in ipairs(targets) do
                                local obj = det.object
                                if obj and obj:isExist()
                                        and Object.getCategory(obj) == Object.Category.UNIT
                                        and obj:getCoalition() ~= sideId then
                                    local okt, tgroup = pcall(function() return obj:getGroup() end)
                                    if okt and tgroup and tgroup:isExist() then
                                        local cat = tgroup:getCategory()
                                        if cat == Group.Category.AIRPLANE
                                                or cat == Group.Category.HELICOPTER then
                                            local tname = tgroup:getName()
                                            local tpos = obj:getPoint()
                                            if not contacts[tname] and ewrPos
                                                    and dist3(ewrPos, tpos) <= DETECTION_RANGE then
                                                contacts[tname] = {
                                                    id = tgroup:getID(),
                                                    pos = tpos,
                                                    ewr = gname,
                                                }
                                            end
                                        end
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end
    end
    return contacts
end

-- Airborne, AI-crewed fighter flights of this side that are not already intercepting.
local function availableInterceptors(sideId)
    local flights = {}
    local okg, groups = pcall(coalition.getGroups, sideId, Group.Category.AIRPLANE)
    if not okg or not groups then return flights end
    for _, group in ipairs(groups) do
        if group and group:isExist() then
            local name = group:getName()
            if isInterceptorName(name) and not assigned[name] then
                local lead, hasPlayer = nil, false
                for _, unit in ipairs(group:getUnits() or {}) do
                    if unit and unit:isExist() then
                        if unit:getPlayerName() then hasPlayer = true end
                        if not lead and unit:inAir() then lead = unit end
                    end
                end
                if lead and not hasPlayer then
                    table.insert(flights, { group = group, name = name, pos = lead:getPoint() })
                end
            end
        end
    end
    return flights
end

local function vector(flight, contact, contactName)
    local okc, controller = pcall(function() return flight.group:getController() end)
    if not okc or not controller then
        log("could not get controller for " .. flight.name)
        return
    end
    local task = {
        id = "ControlledTask",
        params = {
            task = {
                id = "EngageGroup",
                params = { groupId = contact.id, priority = 0 },
            },
            -- Self-unwinding: when the duration elapses the intercept is dropped and
            -- the flight resumes the route underneath it. See the header note on why
            -- this is a stop condition instead of a popTask.
            stopCondition = { duration = INTERCEPT_DURATION },
        },
    }
    local okp = pcall(function() controller:pushTask(task) end)
    if not okp then
        log("pushTask FAILED for " .. flight.name)
        return
    end
    assigned[flight.name] = {
        target = contactName,
        expires = timer.getTime() + INTERCEPT_DURATION,
    }
    announce(string.format("%s cued by EWR %s -> intercepting %s (%s NM)",
        flight.name, contact.ewr, contactName, nmText(dist3(flight.pos, contact.pos))))
end

local function expireAssignments()
    local now = timer.getTime()
    for gname, a in pairs(assigned) do
        if now >= a.expires then
            assigned[gname] = nil
            announce(string.format("%s intercept of %s expired -> back on planned route",
                gname, a.target))
        end
    end
end

local function runCycle()
    expireAssignments()

    for _, side in ipairs(SIDES) do
        local contacts = detectedContacts(side.key, side.id)
        local nContacts = 0
        for _ in pairs(contacts) do nContacts = nContacts + 1 end
        if nContacts > 0 then
            local flights = availableInterceptors(side.id)
            if DEBUG and #flights == 0 then
                log(string.format("%s: %d contact(s) held, no free fighter flight available",
                    side.key, nContacts))
            end
            for _, flight in ipairs(flights) do
                -- Nearest contact this flight is willing to divert to.
                local best, bestName, bestDist = nil, nil, DIVERT_RANGE
                for cname, contact in pairs(contacts) do
                    local d = dist3(flight.pos, contact.pos)
                    if d <= bestDist then
                        best, bestName, bestDist = contact, cname, d
                    end
                end
                if best then
                    vector(flight, best, bestName)
                end
            end
        end
    end
    return timer.getTime() + UPDATE_INTERVAL
end

log(string.format(
    "started | detection %d NM | divert %d NM | intercept %ds | tick %ds | DEBUG=%s",
    DETECTION_RANGE_NM, DIVERT_RANGE_NM, INTERCEPT_DURATION, UPDATE_INTERVAL,
    tostring(DEBUG)))

for _, side in ipairs(SIDES) do
    log(string.format("%s EWR sites known: %d", side.key, #ewrGroupNames(side.key)))
end

timer.scheduleFunction(runCycle, nil, timer.getTime() + UPDATE_INTERVAL)
