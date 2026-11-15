require "SuQingTrainingDummy/Core"

local Dummy = SuQingTrainingDummy

-- A new swing supplies one award slot for the actual object-hit callback.
local swingWeapon = setmetatable({}, { __mode = "k" })
local meleeSkills = {
    { WeaponCategory.AXE, Perks.Axe },
    { WeaponCategory.BLUNT, Perks.Blunt },
    { WeaponCategory.SPEAR, Perks.Spear },
    { WeaponCategory.LONG_BLADE, Perks.LongBlade },
    { WeaponCategory.SMALL_BLADE, Perks.SmallBlade },
    { WeaponCategory.SMALL_BLUNT, Perks.SmallBlunt },
}

local function onSwing(player, weapon)
    if Dummy.isSoloPlayer(player) then swingWeapon[player] = weapon end
end

local function onFinish(player)
    if player then swingWeapon[player] = nil end
end

local function onHit(player, weapon, target)
    if not player or not weapon or not Dummy.isSoloPlayer(player)
        or weapon:isRanged() or weapon:getType() == "BareHands"
        or player:isDoShove() or player:isDoStomp() or not Dummy.isDummy(target) then
        return
    end

    -- The engine subtracts door damage and checks for destruction after this callback.
    local damage = weapon:getDoorDamage()
    if damage ~= 1 then target:setHealth(target:getHealth() + damage - 1) end

    if swingWeapon[player] ~= weapon then return end
    swingWeapon[player] = nil
    local scriptItem = weapon:getScriptItem()
    if not scriptItem then return end
    for _, mapping in ipairs(meleeSkills) do
        if scriptItem:containsWeaponCategory(mapping[1]) then
            Dummy.addXP(player, mapping[2], Dummy.getOption("MeleeXP"))
            return
        end
    end
end

Events.OnWeaponSwing.Add(onSwing)
Events.OnWeaponHitThumpable.Add(onHit)
Events.OnPlayerAttackFinished.Add(onFinish)
