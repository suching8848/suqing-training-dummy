SuQingTrainingDummy = SuQingTrainingDummy or {}

local Dummy = SuQingTrainingDummy
local marker = "SuQingTrainingDummy"
local sprites = {
    suqing_training_dummy_01_0 = true,
    suqing_training_dummy_01_1 = true,
    suqing_training_dummy_01_2 = true,
    suqing_training_dummy_01_3 = true,
}

local optionDefaults = {
    MeleeXP = 0.5,
    EnableRangedTraining = false,
    AimingXP = 1,
}

local function isXPAmount(value)
    return type(value) == "number" and value >= 0 and value <= 100
end

function Dummy.getOption(name)
    local default = optionDefaults[name]
    local options = SandboxVars and SandboxVars.SuQingTrainingDummy
    local value = options and options[name]
    if type(default) == "number" and isXPAmount(value) then return value end
    if type(default) == "boolean" and type(value) == "boolean" then return value end
    return default
end

function Dummy.isSoloPlayer(player)
    return player ~= nil and not isClient() and not isServer() and instanceof(player, "IsoPlayer")
        and player:isLocalPlayer() and not player:isDead()
end

local function hasDummySprite(object)
    if not object or not instanceof(object, "IsoThumpable") then return false end
    local sprite = object:getSprite()
    return sprite ~= nil and sprites[sprite:getName()] == true
end

function Dummy.isDummy(object)
    return hasDummySprite(object) and object:getObjectIndex() >= 0
        and not object:isDestroyed() and object:getHealth() > 0
        and object:getModData()[marker] == true
end

function Dummy.onCreate(params)
    local dummy = params and params.thumpable
    if not hasDummySprite(dummy) then return end
    dummy:getModData()[marker] = true
    dummy:setBlockAllTheSquare(true)
    dummy:setCanPassThrough(false)
end

function Dummy.addXP(player, perk, amount)
    if not Dummy.isSoloPlayer(player) or not perk or not isXPAmount(amount) or amount == 0
        or player:getPerkLevel(perk) >= 10 then
        return false
    end

    player:getXp():AddXP(perk, amount)
    return true
end

function Dummy.onRangedHit(player, dummy)
    if not Dummy.isSoloPlayer(player) or not Dummy.getOption("EnableRangedTraining")
        or not Dummy.isDummy(dummy) then
        return false
    end

    Dummy.addXP(player, Perks.Aiming, Dummy.getOption("AimingXP"))
    dummy:Damage(1)
    if dummy:getHealth() <= 0 then dummy:destroy() end
    return true
end

return Dummy
