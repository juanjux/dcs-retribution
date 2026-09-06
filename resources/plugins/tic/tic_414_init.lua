-- 414th TIC initialization & ambient-fire extension.
-- Loaded by the Retribution mission generator immediately AFTER TIC_v1.1.lua.
-- The generator preamble sets GLSCO.AutoInitialize/AutoStart = false, so this
-- file owns battle initialization. If this file does not run, TIC never
-- starts — keep it loaded right after the main script.
--
-- Ambient fire: stock TIC "simulate" ROE only fires when a combatant has a
-- line-of-sight target within ~2 NM. Where terrain (towns, ridges) blocks
-- LOS, the front goes silent and looks dead from the air. When a combatant
-- comes up empty, this extension gives it a chance to area-fire a salvo
-- toward the nearest enemy formation anyway — tracers arcing downrange and
-- impacts around real enemy positions, without aimed lethality.

local AMBIENT_FIRE_CHANCE = 0.5 -- chance per empty firing cycle to speculate
local AMBIENT_FIRE_MAX_RANGE = 6000 -- m; ignore enemies farther than this
local AMBIENT_AIM_RADIUS_OUTER = 150 -- m; rounds land within this of the enemy
local AMBIENT_AIM_RADIUS_INNER = 30 -- m; ...but no closer than this (area fire)

if GLSCO == nil or GLSCO_COMBATANT == nil or GLSCO_BATTLEFIELD == nil then
    env.warning("tic_414_init: TIC is not loaded; skipping 414th TIC setup")
    return
end

local function ambientFireEnabled()
    return dcsRetribution
        and dcsRetribution.plugins
        and dcsRetribution.plugins.tic
        and dcsRetribution.plugins.tic.ambientFire == true
end

local function nearestEnemyCoord(combatant)
    if GLSCO.battle == nil then
        return nil
    end
    local myCoord = combatant:GetCoordinate()
    if myCoord == nil then
        return nil
    end
    local myCoalition = combatant:GetCoalition()
    local best = nil
    local bestDist = AMBIENT_FIRE_MAX_RANGE
    for _, formation in ipairs(GLSCO.battle.formations) do
        if formation:GetCoalition() ~= myCoalition then
            local combatants = formation:GetCombatants()
            for i = 1, #combatants do
                local enemy = combatants[i]
                if enemy:IsAlive() then
                    local coord = enemy:GetCoordinate()
                    if coord ~= nil then
                        local dist = myCoord:Get2DDistance(coord)
                        if dist < bestDist then
                            best = coord
                            bestDist = dist
                        end
                    end
                    -- One alive combatant per formation is plenty for
                    -- speculative fire; keep the scan cheap.
                    break
                end
            end
        end
    end
    return best
end

if ambientFireEnabled() then
    env.info("tic_414_init: ambient fire extension enabled")

    local baseSimulate = GLSCO_COMBATANT.simulate

    function GLSCO_COMBATANT:simulate()
        local target = baseSimulate(self)
        if target ~= nil then
            -- Stock TIC fired a real (LOS) salvo this cycle.
            return target
        end
        if math.random() > AMBIENT_FIRE_CHANCE then
            return nil
        end
        if not self:IsAlive() or self:IsWeaponFree() or self:IsRiding() then
            return nil
        end
        local coord = nearestEnemyCoord(self)
        if coord == nil then
            return nil
        end
        local vec2 = coord:GetRandomVec2InRadius(
            AMBIENT_AIM_RADIUS_OUTER,
            AMBIENT_AIM_RADIUS_INNER
        )
        -- Same fire-mission shape as stock GLSCO_COMBATANT:simulate().
        self.group:OptionROEOpenFire()
        local altitude = math.random(1, 5)
        local task = self.group:TaskFireAtPoint(
            vec2, 1, self.profile.SalvoQty, nil, altitude
        )
        self.group:PushTask(task, 0)
        return nil
    end
else
    env.info("tic_414_init: ambient fire extension disabled by plugin option")
end

-- Manual battle start (the generator preamble disabled TIC's auto path so
-- the ambient-fire wrapper above is installed before combatants activate).
env.info("tic_414_init: initializing TIC battle")
GLSCO:Initialize()
if GLSCO.battle ~= nil then
    env.info("tic_414_init: activating TIC battle")
    GLSCO.battle:Activate()
else
    env.warning("tic_414_init: GLSCO.battle is nil after Initialize!")
end
