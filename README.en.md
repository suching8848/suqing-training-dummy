# SuQing's Training Dummy

[简体中文](README.md)

Build a training dummy in the vanilla building menu and use normal melee attacks to train six weapon skills. Valid hits award XP through the vanilla skill system. Targets Project Zomboid Build 42.22.2 single-player.

| Mod ID | Function and dependencies |
| --- | --- |
| `SuQingTrainingDummy` | Main mod. Construction, melee training, durability and repairs use vanilla Lua APIs. |
| `SuQingTrainingDummyViewpoint` | Optional 3D model. Requires the main mod and `Viewpoint`. Both views use the same placed dummy. |

## How to use it

1. Select the dummy under SuQing's Training Dummy in the building menu. Requires Carpentry 1 and a hammer. Uses 4 planks, 6 nails and 4 ripped sheets. The hammer is retained.
2. Land a hit with an axe, long blunt, short blunt, long blade, short blade or spear weapon. Each valid attack awards 0.5 base XP by default, using the weapon's scripted category. The vanilla XP multipliers apply.
3. Right-click to see the dummy's durability. A new dummy has 300 HP and loses 1 HP per valid melee weapon hit. It breaks at zero. A repair needs a hammer and uses 1 plank and 1 ripped sheet to restore up to 100 HP.

Adjust the base melee XP per attack in the SuQing's Training Dummy sandbox options. Modded weapons are classified by their assigned vanilla weapon categories.

Experimental firearms training is off by default. When enabled, the candidate checks the character's aim ray on a live shot. The dummy must be on the same floor, at least 3 tiles away, and unobstructed. A successful training shot awards 1 base Aiming XP by default. The exercise checks a geometric chest hit region. The game still handles ammunition and gunfire sounds. Firearms and aiming in both isometric and Viewpoint camera modes await in-game testing.

## Test package

Close the game and place the two mod folders from the archive in the `mods` folder under your user data directory. Enable the main mod in a separate test save. Enable the optional 3D model with Project Viewpoint 0.1.6.2. The main mod supplies the isometric tiles. Break placed dummies in the test save before removing the main mod.
