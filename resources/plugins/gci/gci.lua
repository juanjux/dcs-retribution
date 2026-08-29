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
local EXTRA_RANGE_CAP_NM = 0     -- 0 = trust the radar's own envelope, see below
local DIVERT_RANGE_NM    = 60
local INTERCEPT_DURATION = 300
local UPDATE_INTERVAL    = 15

if dcsRetribution and dcsRetribution.plugins and dcsRetribution.plugins.gci then
    local o = dcsRetribution.plugins.gci
    if o.DEBUG ~= nil then DEBUG = o.DEBUG == true end
    EXTRA_RANGE_CAP_NM = tonumber(o.extraRangeCapNM)   or EXTRA_RANGE_CAP_NM
    DIVERT_RANGE_NM    = tonumber(o.divertRangeNM)     or DIVERT_RANGE_NM
    INTERCEPT_DURATION = tonumber(o.interceptDuration) or INTERCEPT_DURATION
    UPDATE_INTERVAL    = tonumber(o.updateInterval)    or UPDATE_INTERVAL
end

local NM = 1852
local EXTRA_RANGE_CAP = EXTRA_RANGE_CAP_NM * NM
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

-- Every air contact this side's EWRs currently hold, keyed by target group name so
-- several radars painting the same formation collapse into one entry.
--
-- Range and terrain are the ENGINE's answer, not ours. Asking the radar's own
-- controller what it holds means the unit's real detection envelope, terrain masking,
-- the radar horizon and low-level beaming have already been applied: a 1L13 and a
-- 55G6 differ because DCS says they differ, and a contact down in a fjord is absent
-- because DCS says it is. This is the same property the bundled EWRS script
-- advertises, and the reason neither script does line-of-sight maths of its own.
--
-- Detection is filtered to RADAR on purpose. An unfiltered getDetectedTargets() also
-- returns VISUAL, OPTIC, IRST, RWR and DLINK contacts, so a radar site would inherit
-- tracks datalinked from elsewhere and cue fighters onto aircraft it never actually
-- saw, bypassing exactly the terrain masking that makes flying low worth doing.
--
-- EXTRA_RANGE_CAP is only an optional hard clip on top, off by default, because
-- clipping every radar to one flat number is precisely the crude model the engine
-- already does better.
local function detectedContacts(sideKey, sideId)
    local contacts = {}
    for _, gname in ipairs(ewrGroupNames(sideKey)) do
        local okg, group = pcall(Group.getByName, gname)
        if okg and group and group:isExist() then
            local ewrPos
            for _, u in ipairs(group:getUnits() or {}) do
                if u and u:isExist() then ewrPos = u:getPoint() break end
            end
            if ewrPos then
                do
                    local okc, controller = pcall(function() return group:getController() end)
                    if okc and controller then
                        local okd, targets = pcall(function()
                            return controller:getDetectedTargets(Controller.Detection.RADAR)
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
                                            if not contacts[tname]
                                                    and (EXTRA_RANGE_CAP <= 0
                                                         or dist3(ewrPos, tpos) <= EXTRA_RANGE_CAP) then
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

-- DEBUG heartbeat. Watching from the outside it is genuinely hard to tell an
-- intercept from a racetrack leg that happens to point at the contact -- the flight
-- looks committed, then turns back on its orbit. This states outright, every cycle,
-- what the plugin believes each eligible flight is doing.
-- Straight-line range to the closest airborne enemy, whether or not anyone has
-- detected it. This is the discriminator the status line needs: a cue and an
-- unaided radar contact both end with fighters going afterburner, and the only way
-- to tell them apart from the outside is the RANGE at which the flight commits. GCI
-- reaches far past a fighter's own radar, so "INTERCEPTING at 110 NM" and "holding,
-- no cue" until 30 NM are different mechanisms, not different luck.
local function nearestHostileNM(sideId, pos)
    local other = (sideId == coalition.side.RED) and coalition.side.BLUE
                                                 or coalition.side.RED
    local best, bestName
    for _, cat in ipairs({ Group.Category.AIRPLANE, Group.Category.HELICOPTER }) do
        local okg, groups = pcall(coalition.getGroups, other, cat)
        if okg and groups then
            for _, g in ipairs(groups) do
                if g and g:isExist() then
                    for _, u in ipairs(g:getUnits() or {}) do
                        if u and u:isExist() and u:inAir() then
                            local d = dist3(pos, u:getPoint())
                            if not best or d < best then
                                best, bestName = d, g:getName()
                            end
                        end
                    end
                end
            end
        end
    end
    return best, bestName
end

-- What the FLIGHT itself holds, split by how it holds it.
--
-- Reporting this unfiltered was misleading: the range it returned matched the plain
-- geometric range to the nearest bandit exactly, at 105 and 147 NM, which no MiG-23
-- radar can do. Unfiltered getDetectedTargets() evidently includes the coalition's
-- shared picture, so the flight merely KNEW about the contact rather than having
-- found it -- and calling that "prosecuting its own contact" claimed more than the
-- data supports. Only the RADAR-filtered figure is genuine own-sensor detection, so
-- the two are returned separately and labelled for what they are.
local function ownContact(group, sideId, pos)
    local okc, controller = pcall(function() return group:getController() end)
    if not okc or not controller then return nil, nil end

    local function nearest(filter)
        local okd, targets = pcall(function()
            if filter then return controller:getDetectedTargets(filter) end
            return controller:getDetectedTargets()
        end)
        if not okd or not targets then return nil end
        local best, bestName
        for _, det in ipairs(targets) do
            local obj = det.object
            if obj and obj:isExist()
                    and Object.getCategory(obj) == Object.Category.UNIT
                    and obj:getCoalition() ~= sideId then
                local d = dist3(pos, obj:getPoint())
                if not best or d < best then
                    best = d
                    local okg, g = pcall(function() return obj:getGroup() end)
                    bestName = (okg and g and g:getName()) or "?"
                end
            end
        end
        return best, bestName
    end

    local rNM, rName = nearest(Controller.Detection.RADAR)
    local aNM, aName = nearest(nil)
    return rNM, rName, aNM, aName
end

local function statusReport()
    local lines = {}
    for _, side in ipairs(SIDES) do
        local okg, groups = pcall(coalition.getGroups, side.id, Group.Category.AIRPLANE)
        if okg and groups then
            for _, group in ipairs(groups) do
                if group and group:isExist() and isInterceptorName(group:getName()) then
                    local name = group:getName()
                    local lead
                    for _, u in ipairs(group:getUnits() or {}) do
                        if u and u:isExist() and u:inAir() then lead = u break end
                    end
                    local state
                    local a = assigned[name]
                    if a then
                        state = string.format("INTERCEPTING %s (%ds left)", a.target,
                            math.max(0, math.floor(a.expires - timer.getTime())))
                    elseif not lead then
                        state = "on the ground"
                    else
                        local rNM, rName, aNM, aName =
                            ownContact(group, side.id, lead:getPoint())
                        if rNM then
                            state = string.format(
                                "no cue, OWN RADAR holds %s at %s NM", rName, nmText(rNM))
                        elseif aNM then
                            state = string.format(
                                "no cue, no radar contact, only shared awareness of %s at %s NM",
                                aName, nmText(aNM))
                        else
                            state = "holding, no cue, sees nothing"
                        end
                    end
                    if lead then
                        local d, dName = nearestHostileNM(side.id, lead:getPoint())
                        state = state .. (d and string.format(
                            "; nearest bandit is %s at %s NM", dName, nmText(d))
                            or "; no bandits airborne")
                    end
                    table.insert(lines, name .. ": " .. state)
                end
            end
        end
    end
    if #lines > 0 then
        env.info("GCI| status: " .. table.concat(lines, " | "))
        trigger.action.outText("GCI status\n" .. table.concat(lines, "\n"),
            math.max(5, UPDATE_INTERVAL - 1))
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
    if DEBUG then statusReport() end
    return timer.getTime() + UPDATE_INTERVAL
end

log(string.format(
    "started | radar range: %s | divert %d NM | intercept %ds | tick %ds | DEBUG=%s",
    EXTRA_RANGE_CAP_NM > 0 and (EXTRA_RANGE_CAP_NM .. " NM cap")
        or "per-unit (engine radar model + terrain masking)",
    DIVERT_RANGE_NM, INTERCEPT_DURATION, UPDATE_INTERVAL, tostring(DEBUG)))

for _, side in ipairs(SIDES) do
    log(string.format("%s EWR sites known: %d", side.key, #ewrGroupNames(side.key)))
end

timer.scheduleFunction(runCycle, nil, timer.getTime() + UPDATE_INTERVAL)
