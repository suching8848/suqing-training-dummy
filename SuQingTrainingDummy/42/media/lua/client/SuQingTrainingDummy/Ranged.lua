require "SuQingTrainingDummy/Core"

local Dummy = SuQingTrainingDummy
if isClient() or isServer() or Dummy.rangedTrainingLoaded then return end

local MIN_RANGE = 3
local MAX_TRACE_RANGE = 100
local TORSO_RADIUS = 0.30
local MIN_TORSO_HEIGHT = 0.27
local MAX_TORSO_HEIGHT = 0.64
local FLOOR_HEIGHT = 2.44949
local CORNER_EPSILON = 0.000001
local aimVector = Vector2.new()
local pending = setmetatable({}, { __mode = "k" })

local function targetIn(square)
    local objects = square:getObjects()
    for index = 0, objects:size() - 1 do
        local object = objects:get(index)
        if Dummy.isDummy(object) then return object end
    end
end

local function hasMovingBlocker(square, shooter)
    local movingObjects = square:getMovingObjects()
    for index = 0, movingObjects:size() - 1 do
        local object = movingObjects:get(index)
        if object ~= shooter and (instanceof(object, "BaseVehicle")
            or (instanceof(object, "IsoGameCharacter") and not object:isDead())) then
            return true
        end
    end
    return false
end

local function edgeBlocked(from, to)
    return not to or from:isBlockedTo(to) or from:isWindowTo(to)
end

local function mayCrossCorner(from, side, destination, shooter)
    return not edgeBlocked(from, side) and not edgeBlocked(side, destination)
        and not side:isSolid() and not side:isSolidTrans()
        and not hasMovingBlocker(side, shooter) and not targetIn(side)
end

local function torsoIntersection(ray, x, y, enter, leave)
    local offsetX, offsetY = x + 0.5 - ray.x, y + 0.5 - ray.y
    local crossDistance = offsetX * ray.dy - offsetY * ray.dx
    local radiusSquared = TORSO_RADIUS * TORSO_RADIUS - crossDistance * crossDistance
    if radiusSquared < 0 then return nil end

    local centerDistance = offsetX * ray.dx + offsetY * ray.dy
    local hitDistance = centerDistance - math.sqrt(radiusSquared)
    if hitDistance < enter or hitDistance > leave then return nil end

    local hitHeight = ray.height + hitDistance * ray.slope
    if hitHeight < MIN_TORSO_HEIGHT or hitHeight > MAX_TORSO_HEIGHT then return nil end
    return centerDistance
end

local function firstSquareCrossing(origin, tile, direction)
    if direction > 0 then return 1, (tile + 1 - origin) / direction, 1 / direction end
    if direction < 0 then return -1, (origin - tile) / -direction, 1 / -direction end
    return 0, math.huge, math.huge
end

local function traceShooter(player, ray, range)
    local cell = getCell()
    local x, y, floor = math.floor(ray.x), math.floor(ray.y), ray.floor
    local current = player:getCurrentSquare()
    if not current or current:getX() ~= x or current:getY() ~= y or current:getZ() ~= floor then return nil end
    if hasMovingBlocker(current, player) then return nil end

    local stepX, nextX, intervalX = firstSquareCrossing(ray.x, x, ray.dx)
    local stepY, nextY, intervalY = firstSquareCrossing(ray.y, y, ray.dy)
    local enter = math.min(nextX, nextY)
    while enter <= range do
        local nextSquare
        if math.abs(nextX - nextY) <= CORNER_EPSILON then
            nextSquare = cell:getGridSquare(x + stepX, y + stepY, floor)
            if not mayCrossCorner(current, cell:getGridSquare(x + stepX, y, floor), nextSquare, player)
                or not mayCrossCorner(current, cell:getGridSquare(x, y + stepY, floor), nextSquare, player) then
                return nil
            end
            x, y = x + stepX, y + stepY
            nextX, nextY = nextX + intervalX, nextY + intervalY
        elseif nextX < nextY then
            x, nextX = x + stepX, nextX + intervalX
            nextSquare = cell:getGridSquare(x, y, floor)
            if edgeBlocked(current, nextSquare) then return nil end
        else
            y, nextY = y + stepY, nextY + intervalY
            nextSquare = cell:getGridSquare(x, y, floor)
            if edgeBlocked(current, nextSquare) then return nil end
        end

        if hasMovingBlocker(nextSquare, player) then return nil end
        local leave = math.min(range, nextX, nextY)
        local dummy = targetIn(nextSquare)
        if dummy then
            local distance = torsoIntersection(ray, x, y, enter, leave)
            if distance and distance >= MIN_RANGE then return dummy end
            return nil
        end
        if nextSquare:isSolid() or nextSquare:isSolidTrans() then return nil end
        current = nextSquare
        enter = leave
        if enter >= range then return nil end
    end
end

local function readAim(player)
    local aim = player:getAimVector(aimVector)
    local dx, dy = aim:getX(), aim:getY()
    local length = math.sqrt(dx * dx + dy * dy)
    local floor = math.floor(player:getZ())
    local height = player:getAimOriginPosZ() - floor
    local degrees = player:getCurrentVerticalAimAngle()
    if not (length > CORNER_EPSILON and height > 0 and height < 1 and math.abs(degrees) < 45) then
        return nil
    end
    local pitch = math.rad(degrees)
    return {
        x = player:getAimOriginPosX(), y = player:getAimOriginPosY(), floor = floor,
        height = height, dx = dx / length, dy = dy / length,
        slope = math.tan(pitch) / FLOOR_HEIGHT, horizontalScale = math.cos(pitch),
    }
end

local function onWeaponSwingHitPoint(player, weapon)
    if not Dummy.isSoloPlayer(player) then return end
    pending[player] = nil
    if not Dummy.getOption("EnableRangedTraining") or not weapon or not weapon:isAimedFirearm()
        or not weapon:isRanged() or weapon:getPhysicsObject() or player:getPrimaryHandItem() ~= weapon
        or player:getVehicle() or player:isRangedWeaponEmpty()
        or player:isDoShove() or player:isShoveStompAnim() or player:isAimAtFloor() then
        return
    end

    local ray = readAim(player)
    if not ray then return end
    local range = math.min(MAX_TRACE_RANGE, weapon:getMaxRange(player)) * ray.horizontalScale
    if not (range >= MIN_RANGE) then return end
    local dummy = traceShooter(player, ray, range)
    if dummy then pending[player] = { target = dummy, weapon = weapon } end
end

local function onPlayerAttackFinished(player, weapon)
    if not player then return end
    local shot = pending[player]
    pending[player] = nil
    if not shot or shot.weapon ~= weapon or player:isDead() or player:getLastHitCount() ~= 0
        or not Dummy.getOption("EnableRangedTraining") or not Dummy.isDummy(shot.target) then
        return
    end
    Dummy.onRangedHit(player, shot.target)
end

-- The native shot animation starts the candidate, and the native completed attack
-- rejects interrupted shots. The range exercise uses a centered aiming ray because
-- the engine's actual pellet spread and impact points are unavailable to Lua.
Events.OnWeaponSwingHitPoint.Add(onWeaponSwingHitPoint)
Events.OnPlayerAttackFinished.Add(onPlayerAttackFinished)
Dummy.rangedTrainingLoaded = true
