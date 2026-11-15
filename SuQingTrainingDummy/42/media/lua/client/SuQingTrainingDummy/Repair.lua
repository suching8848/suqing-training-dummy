require "TimedActions/ISBaseTimedAction"
require "ISUI/ISToolTip"
require "SuQingTrainingDummy/Core"

local Dummy = SuQingTrainingDummy
local Repair = ISBaseTimedAction:derive("ISSuQingTrainingDummyRepair")
local repairHP = 100

local function usableHammer(item)
    return not item:isBroken()
end

local function isDamaged(dummy)
    return Dummy.isDummy(dummy) and dummy:getHealth() < dummy:getMaxHealth()
end

local function findMaterials(player)
    local inventory = player:getInventory()
    local hammer = inventory:getFirstTagEvalRecurse(ItemTag.HAMMER, usableHammer)
    return hammer, inventory:getFirstTypeRecurse("Base.Plank"), inventory:getFirstTypeRecurse("Base.RippedSheets")
end

function Repair:isValid()
    if not Dummy.isSoloPlayer(self.character) or not isDamaged(self.dummy) then return false end
    local square = self.dummy:getSquare()
    local playerSquare = self.character:getCurrentSquare()
    if not square or not playerSquare or square:getZ() ~= playerSquare:getZ()
        or not playerSquare:isAdjacentTo(square) or not playerSquare:canReachTo(square) then
        return false
    end

    local inventory = self.character:getInventory()
    return not self.hammer:isBroken() and inventory:containsRecursive(self.hammer)
        and inventory:containsRecursive(self.plank) and inventory:containsRecursive(self.cloth)
end

function Repair:waitToStart()
    self.character:faceThisObject(self.dummy)
    return self.character:shouldBeTurning()
end

function Repair:start()
    self:setActionAnim("Build")
    self:setOverrideHandModels(self.hammer, nil)
end

function Repair:update()
    self.character:faceThisObject(self.dummy)
    self.character:setMetabolicTarget(Metabolics.UsingTools)
end

function Repair:complete()
    if not self:isValid() then return false end

    local plankContainer = self.plank:getContainer()
    local clothContainer = self.cloth:getContainer()
    if not plankContainer or not clothContainer then return false end

    self.character:removeFromHands(self.plank)
    self.character:removeFromHands(self.cloth)
    plankContainer:Remove(self.plank)
    clothContainer:Remove(self.cloth)
    self.dummy:setHealth(math.min(self.dummy:getMaxHealth(), self.dummy:getHealth() + repairHP))
    self.dummy:DirtySlice()
    return true
end

function Repair:new(character, dummy, hammer, plank, cloth)
    local action = ISBaseTimedAction.new(self, character)
    action.dummy = dummy
    action.hammer = hammer
    action.plank = plank
    action.cloth = cloth
    action.maxTime = character:isTimedActionInstant() and 1 or 100
    return action
end

local function queueRepair(dummy, player)
    if not Dummy.isSoloPlayer(player) or not isDamaged(dummy) then return end
    local hammer, plank, cloth = findMaterials(player)
    if not hammer or not plank or not cloth then return end
    if luautils.walkAdjObject(player, dummy, true) then
        ISTimedActionQueue.add(Repair:new(player, dummy, hammer, plank, cloth))
    end
end

local function fillContext(playerIndex, context, objects, test)
    local player = getSpecificPlayer(playerIndex)
    if not Dummy.isSoloPlayer(player) then return end

    for _, object in ipairs(objects) do
        if Dummy.isDummy(object) then
            if test then return ISWorldObjectContextMenu.setTest() end
            local condition = context:addOption(getText("IGUI_SQTD_Condition", object:getHealth(), object:getMaxHealth()))
            condition.notAvailable = true
            if isDamaged(object) then
                local option = context:addOption(getText("IGUI_SQTD_Repair"), object, queueRepair, player)
                local hammer, plank, cloth = findMaterials(player)
                option.notAvailable = not hammer or not plank or not cloth
                local tooltip = ISToolTip:new()
                tooltip:initialise()
                tooltip.description = getText("Tooltip_SQTD_Repair", repairHP)
                option.toolTip = tooltip
            end
            return
        end
    end
end

Events.OnFillWorldObjectContextMenu.Add(fillContext)
