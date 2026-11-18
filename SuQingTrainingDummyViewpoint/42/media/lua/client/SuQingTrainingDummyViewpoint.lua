local modelRegistered = false

-- Viewpoint 0.1.7 discovers the model through pack.properties.
local function registerLegacyModel()
    if modelRegistered or not Viewpoint or Viewpoint.Addons or not Viewpoint.ModelPacks then
        return
    end

    local registerModel = Viewpoint.ModelPacks.register
    if registerModel then
        modelRegistered = registerModel(
            "SuQingTrainingDummyViewpoint",
            "media/viewpoint/resourcepacks/suqing-training-dummy-models/package.properties"
        )
    end
end

Events.OnGameBoot.Add(registerLegacyModel)
Events.OnGameStart.Add(registerLegacyModel)
