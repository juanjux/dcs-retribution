-- the state.json file will be updated according to this schedule and on mission end
local WRITESTATE_SCHEDULE_IN_SECONDS = 15

logger = mist.Logger:new("DCSRetribution", "info")
logger:info("Check that json.lua is loaded : json = "..tostring(json))

crash_events = {} -- killed aircraft will be added via S_EVENT_CRASH event
dead_events = {} -- killed units will be added via S_EVENT_DEAD event
unit_lost_events = {} -- killed units will be added via S_EVENT_UNIT_LOST
kill_events = {} -- killed units will be added via S_EVENT_KILL
kill_details = {} -- structured S_EVENT_KILL records {target, initiator, weapon} for the UI feed
base_capture_events = {}
destroyed_objects_positions = {} -- will be added via S_EVENT_DEAD event
mission_ended = false
dirty_state = false -- Track if state has changed and needs writing

-- Player-despawn loss guard (414th): a player dropping to spectator — or the
-- mission ending with players still airborne — makes DCS fire S_EVENT_CRASH/DEAD
-- for that aircraft, which would otherwise be counted as a combat loss and attrit
-- the airframe even though the pilot survived (2026-06-20: GERBIL F-14s recorded
-- lost while alive at mission end). We mark a unit when its player LEAVES the seat
-- and suppress the despawn crash/dead/lost that immediately follows. A real
-- shootdown fires the crash/dead while the player is still in the seat (BEFORE the
-- leave), so it is still recorded. Ejections are tracked separately and NEVER
-- suppressed — an ejection is a real loss of the airframe.
player_left_units = {} -- unit name -> mission time of S_EVENT_PLAYER_LEAVE_UNIT
ejected_units = {}     -- unit name -> true; ejected = real loss, never suppress
PLAYER_LEAVE_GRACE_S = 5 -- a crash within this long after a leave = the despawn

local function ends_with(str, ending)
   return ending == "" or str:sub(-#ending) == ending
end

local function messageAll(message)
    local msg = {}
    msg.text = message
    msg.displayTime = 25
    msg.msgFor = {coa = {'all'}}
    mist.message.add(msg)
end

function write_state()
    local _debriefing_file_location = debriefing_file_location
    if not debriefing_file_location or debriefing_file_location == "" then
        error("Unable to save DCS Retribution state: debriefing file path is unavailable")
    end

    if not json then
        error("Unable to save DCS Retribution state, JSON library is not loaded")
    end

    local fp, open_error = io.open(_debriefing_file_location, 'w')
    if not fp then
        error("Unable to open state file for writing: "..tostring(_debriefing_file_location).." ("..tostring(open_error)..")")
    end
    local game_state = {
        ["crash_events"] = crash_events,
        ["dead_events"] = dead_events,
        ["base_capture_events"] = base_capture_events,
		["unit_lost_events"] = unit_lost_events,
		["kill_events"] = kill_events,
		["kill_details"] = kill_details,
        ["mission_ended"] = mission_ended,
        ["destroyed_objects_positions"] = destroyed_objects_positions,
        ["model_time"] = timer.getTime(),
    }
    local ok, write_error = pcall(function()
        fp:write(json:encode(game_state))
    end)
    fp:close()
    if not ok then
        error(write_error)
    end
end

local function canWrite(name)
    local f = io.open(name, "a")
    if f then
        f:close()
        return true
    end
    return false
end

local function testDebriefingFilePath(folderPath, folderName, useCurrentStamping)
    if folderPath then
        local filePath = nil
        if not ends_with(folderPath, "\\") then
            folderPath = folderPath .. "\\"
        end
        if useCurrentStamping then
            filePath = string.format("%sstate-%s.json",folderPath, tostring(os.time()))
        else 
            filePath = string.format("%sstate.json",folderPath)
        end
        local isOk = canWrite(filePath)
        if isOk then 
            logger:info(string.format("The state.json file will be created in %s : (%s)",folderName, filePath))
            return filePath
        end
    end
    return nil
end

local function discoverDebriefingFilePath()   
    -- establish a search pattern into the following modes
    -- 1. Environment variable RETRIBUTION_EXPORT_DIR, to support dedicated server hosting
    -- 2. Embedded DCS Retribution dcsRetribution.installPath (set by the app to its install path), to support locally hosted single player
    -- 3. System temporary folder, as set in the TEMP environment variable
    -- 4. Working directory.
    
    local useCurrentStamping = nil
    if os then  
        useCurrentStamping = os.getenv("RETRIBUTION_EXPORT_STAMPED_STATE")
    end

    local installPath = nil
    if dcsRetribution then
        installPath = dcsRetribution.installPath
    end
    
    if os then
        local result = nil
        -- try using the RETRIBUTION_EXPORT_DIR environment variable
        result = testDebriefingFilePath(os.getenv("RETRIBUTION_EXPORT_DIR"), "RETRIBUTION_EXPORT_DIR", useCurrentStamping)
        if result then
            return result
        end
        -- no joy ? maybe there is a valid path in the mission ?
        result = testDebriefingFilePath(installPath, "the DCS Retribution install folder", useCurrentStamping)
        if result then
            return result
        end
        -- there's always the possibility of using the system temporary folder
        result = testDebriefingFilePath(os.getenv("TEMP"), "TEMP", useCurrentStamping)
        if result then
            return result
        end
    end

    -- nothing worked, let's try the last resort folder : current directory.
    if lfs then
        return testDebriefingFilePath(lfs.writedir().."Missions\\", "the working directory", useCurrentStamping)
    end
    
    return nil
end

debriefing_file_location = discoverDebriefingFilePath()
local error_message_shown = false

write_state_error_handling = function()
    local _debriefing_file_location = debriefing_file_location
    if not debriefing_file_location then 
        _debriefing_file_location = "[nil]"
        logger:error("Unable to find where to write DCS Retribution state")
    end

    -- Only write if state has changed since last write
    if dirty_state then
        if pcall(write_state) then
            dirty_state = false -- Reset dirty flag after successful write
            error_message_shown = false
        else
            if not error_message_shown then
                messageAll("Unable to write DCS Retribution state to ".._debriefing_file_location..
                        "\nYou can abort the mission in DCS Retribution.\n"..
                        "\n\nPlease fix your setup in DCS Retribution, make sure you are pointing to the right installation directory from the File/Preferences menu. Then after fixing the path restart DCS Retribution, and then restart DCS."..
                        "\n\nYou can also try to fix the issue manually by replacing the file <dcs_installation_directory>/Scripts/MissionScripting.lua by the one provided there : <dcs_retribution_folder>/resources/scripts/MissionScripting.lua. And then restart DCS. (This will also have to be done again after each DCS update)"..
                        "\n\nIt's not worth playing, the state of the mission will not be recorded.")
                error_message_shown = true
            end
        end
    end

    -- Reschedule quickly if mission is over and we still have unsaved changes,
    -- otherwise use the normal cadence.
    local next_schedule_in_seconds = WRITESTATE_SCHEDULE_IN_SECONDS
    if mission_ended and dirty_state then
        next_schedule_in_seconds = 1
    end
    mist.scheduleFunction(write_state_error_handling, {}, timer.getTime() + next_schedule_in_seconds)
end

activeWeapons = {}

-- True if `name` is a player jet that just LEFT the seat (and did not eject) — i.e.
-- this crash/dead/lost is the despawn after the player went to spectator or the
-- mission ended, not a kill. The mark is NOT consumed: a single despawn can fire
-- CRASH *and* DEAD *and* UNIT_LOST for the same unit, and all three must be
-- suppressed, so we gate purely on the time window (a leave+re-occupy+real-loss
-- inside PLAYER_LEAVE_GRACE_S seconds is not physically possible).
local function is_player_despawn(name)
    if name == nil or ejected_units[name] then
        return false
    end
    local left_at = player_left_units[name]
    return left_at ~= nil and (timer.getTime() - left_at) <= PLAYER_LEAVE_GRACE_S
end

local function onEvent(event)
    -- Track player seat-leaves and ejections first so the loss handlers below can
    -- tell a despawn (player left, survived) from a real shootdown.
    if event.id == world.event.S_EVENT_EJECTION and event.initiator
       and event.initiator.getName then
        ejected_units[event.initiator.getName(event.initiator)] = true
    end

    if event.id == world.event.S_EVENT_PLAYER_LEAVE_UNIT and event.initiator
       and event.initiator.getName then
        player_left_units[event.initiator.getName(event.initiator)] = timer.getTime()
    end

    if event.id == world.event.S_EVENT_CRASH and event.initiator then
        local name = event.initiator.getName(event.initiator)
        if not is_player_despawn(name) then
            crash_events[#crash_events + 1] = name
            dirty_state = true
        end
    end

    if event.id == world.event.S_EVENT_UNIT_LOST and event.initiator then
        local name = event.initiator.getName(event.initiator)
        if not is_player_despawn(name) then
            unit_lost_events[#unit_lost_events + 1] = name
            dirty_state = true
        end
    end
	
	if event.id == world.event.S_EVENT_KILL and event.target then
        local target_name = event.target.getName(event.target)
        kill_events[#kill_events + 1] = target_name
        -- Also record who killed it and with what, for the UI event feed. All
        -- accessors are pcall-guarded so a missing field never breaks the mission.
        local detail = { ["target"] = target_name }
        if event.initiator then
            pcall(function() detail["initiator"] = event.initiator:getName() end)
            pcall(function() detail["initiator_type"] = event.initiator:getTypeName() end)
            pcall(function()
                local pn = event.initiator:getPlayerName()
                if pn and pn ~= "" then detail["initiator_player"] = pn end
            end)
        end
        if event.weapon then
            pcall(function() detail["weapon"] = event.weapon:getTypeName() end)
        end
        kill_details[#kill_details + 1] = detail
        dirty_state = true
    end

    if event.id == world.event.S_EVENT_DEAD and event.initiator and event.initiator.getName then
        local name = event.initiator.getName(event.initiator)
        if not is_player_despawn(name) then
            dead_events[#dead_events + 1] = name
            local position = event.initiator.getPosition(event.initiator)
            local destruction = {}
            destruction.x = position.p.x
            destruction.y = position.p.y
            destruction.z = position.p.z
            destruction.type = event.initiator:getTypeName()
            destruction.orientation = mist.getHeading(event.initiator) * 57.3
            -- Only track actual units/buildings, not debris/crash models
            if destruction.type ~= nil and
               string.find(destruction.type, "GENERIC_CRASH_MODEL") == nil and
               string.find(destruction.type, "_CRASH") == nil then
                destroyed_objects_positions[#destroyed_objects_positions + 1] = destruction
            end
            dirty_state = true
        end
    end

    if event.id == world.event.S_EVENT_MISSION_END then
        mission_ended = true
        dirty_state = true
        if pcall(write_state) then
            dirty_state = false
        end
    end

end

mist.addEventHandler(onEvent)

dirty_state = true
write_state_error_handling()

-- Escort leash
-- Escorts are kept within their engagement range relative to the escorted group.
-- This is driven by the mission-injected dcsRetribution.Escorts table.

local function escort_leash_get_group(id)
    local group_id = tonumber(id)
    if not group_id or group_id <= 0 then
        return nil
    end
    return Group.getByID(group_id)
end

local function escort_leash_set_roe(group, roe)
    if not group then
        return
    end
    local controller = group:getController()
    if controller then
        controller:setOption(AI.Option.Air.id.ROE, roe)
    end
end

local function escort_leash_update()
    -- Keep running even if dcsRetribution data isn't available yet (trigger ordering)
    if not dcsRetribution or type(dcsRetribution.Escorts) ~= "table" then
        return timer.getTime() + 10
    end

    for _, pair in pairs(dcsRetribution.Escorts) do
        local escort_group = escort_leash_get_group(pair.escortGroupId)
        local escorted_group = escort_leash_get_group(pair.escortedGroupId)

        -- If the escorted group no longer exists (dead/despawned), ensure escort isn't stuck.
        if escort_group and not escorted_group then
            escort_leash_set_roe(escort_group, AI.Option.Air.val.ROE.OPEN_FIRE)
        elseif escort_group and escorted_group then
            local escort_unit = escort_group:getUnit(1)
            local escorted_unit = escorted_group:getUnit(1)
            if escort_unit and escorted_unit then
                local escort_pos = escort_unit:getPoint()
                local escorted_pos = escorted_unit:getPoint()
                local dx = escort_pos.x - escorted_pos.x
                local dz = escort_pos.z - escorted_pos.z
                local distance = math.sqrt(dx * dx + dz * dz)

                local max_dist = tonumber(pair.engagementRangeMeters) or 0
                if max_dist > 0 and distance > max_dist then
                    escort_leash_set_roe(escort_group, AI.Option.Air.val.ROE.RETURN_FIRE)
                else
                    escort_leash_set_roe(escort_group, AI.Option.Air.val.ROE.OPEN_FIRE)
                end
            end
        end
    end

    return timer.getTime() + 10
end

timer.scheduleFunction(escort_leash_update, nil, timer.getTime() + 1)
