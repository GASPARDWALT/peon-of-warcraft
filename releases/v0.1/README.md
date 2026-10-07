# Peon of Warcraft v0.1 — first playable prototype

This build replaces the normal Crystal opening and starting house with a short
Warcraft opening and one playable hub. Its purpose is to test the flow and expose
engine/design conflicts, rather than deliver finished artwork or the full world.

## Play

Open `peon_of_warcraft_v0_1.gbc` in a Game Boy Color emulator on Windows, such as
SameBoy or BGB. Use the emulator's configured D-pad, A, B and Start buttons.

1. Press Start at the title.
2. Select **NEW CHARACTER** with Down, then A. There is one real save slot.
3. Use A to advance the sleeping-peon, hunter, BONK and Hold sequence.
4. Preview the masters with Up/Down. Only **KENTO / SHAMAN** accepts A in v0.1.
5. Receive the crude mace, wooden shield, apprentice totem and Lightning Bolt.
6. Arrive at The Den. Walk north to the NPC below the persistent `!` and press A.
7. Accept the first quest. Walk east to the boar and interact with A to spar.
8. Select FIGHT, then **LIGHTN.BOLT**. Win and return to the quest giver.
9. Kento, west of the arrival point, restores HP and move PP.
10. Press Start and choose SAVE. After closing and reopening the ROM, select
    CONTINUE to resume from the saved position.

The PACK's KEY ITEMS pocket contains the three starting gear items. SHAMAN opens
the existing party/status interface for the single prototype combatant.

Start a fresh character for this build. An older save without the Shaman state is
rejected by Continue with an explanation. Creating a new character over an existing
save requires confirmation. Keep a separate copy of any older `.sav` you value.

## Implemented scope

- Native title with PEON OF WARCRAFT, the exact requested Start prompt wrapped
  across lines, and a small original gate vignette.
- One-slot character presentation with a central technical sprite preview.
- Sleeping pose, hunter approach, BONK sound/text, black fade and eye-opening reveal.
- Compact Grommash Hold with Thrall and three master representations.
- Right-hand class descriptions; only Shaman is enabled.
- Shaman kit, two usable attacks, The Den, quest marker, quest acceptance and a
  friendly boar sparring encounter. Quest state persists in the save.
- Four-direction peon walking and ordinary NPC allocation.

## Deliberate limitations

- One real character/save slot. The original SRAM backup remains recovery data.
- The Shaman is internally species MACHOP (ID 66), renamed SHAMAN. A training boar
  uses RATTATA (ID 19), renamed BOAR. These IDs are prototype adapters.
- Gear is recorded as non-discardable key items using previously unused item IDs
  $19/$2d/$32. It does not yet change stats or support equipment slots.
- Lightning Bolt reuses THUNDERSHOCK's electric damage/animation and is abbreviated
  LIGHTN.BOLT in the constrained move list. Mace Strike reuses POUND.
- PP is still Crystal PP, not shared mana. Some battle/menu terminology, icons,
  sounds, trainer presentation and the title music are still from Crystal.
- Artwork is simple native pixel art, not the detailed generated concept sheet.
  The player uses the already integrated 16×16 sprite; no 16×24 renderer is added.
- Only the Den is freely playable. Valley and Hold are small cinematic sets.
  Cave, Sen'jin, Razor Hill and the complete Valley are not implemented.
- Class descriptions and the character preview use a compact GBC layout; no
  multiple slots, scrolling WoW panel or full character-creation system exists yet.
- Combat is 1v1. No party expansion, equipment engine, advanced loot or future spells.
- Console/cart hardware has not been tested. ROM remains CGB-only, 2 MiB,
  MBC3+timer+battery, with 32 KiB SRAM; cart support for that configuration matters.

## Conflicts found and resolved

1. New-game event initialization was attached to the bedroom. The opening explicitly
   calls Crystal's standard initializer, and spawn now goes to the opening set.
2. Map block zero is a border sentinel. Walkable ground therefore uses block 8.
3. Crystal's text `<NEXT>` advances two rows. Class-panel lists use `<LF>` to fit
   the 160×144 screen without writing past the tilemap.
4. Friendly wild defeat did not fit the trainer-oriented CANLOSE path. Wild CANLOSE
   loss now returns a loss result without loading a nonexistent trainer portrait.
   The sparring script heals and reloads locally instead of invoking whiteout.
5. Medium-slow growth is unsafe at level 1. The Shaman uses medium-fast growth;
   inherited evolution and later Pokémon moves were removed from its learnset.

Map IDs were appended to group 26, leaving existing map IDs unchanged. Persistent
prototype states name four existing unused event bits. Maps share the dormant
BattleTowerOutside scene byte; event flags govern progression. No saved RAM fields
or SRAM structures were inserted, and save/load/checksum routines are unchanged.
This does not make original Crystal saves semantically compatible with the prototype.

## Build and verify

Use RGBDS 1.0.4 and Python with Pillow. Tests also require PyBoy 2.7.0.

```sh
python tools/build_peon_prototype_assets.py
make -j4 RGBDS=/path/to/rgbds-1.0.4/
python tools/validate_peon_intro.py
python tools/validate_peon_sprite.py
python tools/package_peon_v01.py
```

The intro test uses ordinary button input for the new game, locked classes, quest,
combat and battery-save restart. It observes emulator hooks without modifying RAM.
After those checks, a separate saved-state test lowers HP to one to verify the
friendly-defeat recovery branch; that fault injection does not validate the intro.
The separate renderer test forces facing states only to inspect all 16 tile layouts;
its walking and save checks use ordinary input. Temporary ROM copies protect user saves.

The requested AGENTS, START_HERE, LOCKED_DECISIONS and IMPLEMENTATION_ROADMAP files
were absent from origin/main when this work began. The user-approved flow and the
older root project context guided this build. Four world-map WebP references could
not be decoded; readable Den/Hold/cave/UI references supplied the available direction.

## Useful feedback

Report the screen or location, the buttons pressed and the result you expected.
Try class previews, dialogue pacing, finding the quest NPC, casting the spell,
movement/collisions, opening the pack and restarting after saving. A screenshot
and the emulator name help reproduce a problem.
