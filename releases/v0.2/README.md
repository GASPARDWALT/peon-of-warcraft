# Peon of Warcraft v0.2 — Durotar prototype

Download `releases/v0.2/peon_of_warcraft_v0_2.zip`. Extract the `.gbc` and open it
in a Game Boy Color emulator. On Windows, use a GBC-capable emulator such as
SameBoy or mGBA. ROM: 2 MiB, CGB-only, MBC3 + RTC + battery, 32 KiB SRAM.
Physical Chromatic/cart flashing and RTC behavior on hardware remain untested.

## Walkthrough

1. Start → NEW. Follow the sleeping peon, bonk and Grommash Hold opening.
2. Choose Kento. The other masters are previews. Kento asks your name (up to
   five characters); dialogue then uses `Péon <name>`.
3. Begin as a level-two apprentice. Receive the crude mace, wooden shield, apprentice totem and Lightning Bolt.
4. At The Den, speak to Gornek below the yellow quest marker. Accept Cutting
   Teeth. Face the yellow-bordered boar east of camp and press A to fight.
   It never attacks merely because you approach.
5. Return to Gornek for Sting of the Scorpid. The red scorpid attacks when you
   enter its two-tile radius. Defeat it, return to Gornek and receive the map,
   green Barbed Club and Small Pouch.
6. Start → BAGS → A opens the real inventory. Left/Right selects a stack; A
   equips a weapon or uses Spring Water; B returns. The green club increases
   melee damage by 20%. Spring Water restores ten Lightning Bolt charges,
   capped at thirty; combat currently uses Crystal PP instead of a mana pool.
7. Select or Start → MAP opens the region atlas. Left/Right changes region;
   undiscovered regions remain hidden. Entering a region reveals that region.
8. The eastern road tile leads to Valley of Trials. Speak to Galgar at (8,10).
   Harvest three cacti by facing their lower edge and pressing A. Return for
   the Leather Bag and 50 copper. Bag capacity: 6 → 12 → 20 item stacks.
   Quest/equipment key items use a separate reserved pocket.
9. The northern cave entrance leads to Burning Blade Cavern. Red imps give
   repeatable fights and loot. A level-three familiar drops a gray Worn Mace
   (+5% melee); a level-five familiar drops a white Wooden Mace (+10% melee).
   Each victorious cave encounter has a 1/64 chance of a blue Shaman Mace
   (+30% Nature damage). Rarity is shown in text; the small catalog is custom
   prototype balance, not a complete Classic item database.
10. Duokna at The Den sells five Spring Waters for 25 copper, matching the
    Classic bundle/base price. There is no reputation discount, buyback or
    sell interface yet. The remaining connected regions are Durotar Road,
    Sen'jin Village, Razor Hill and Orgrimmar Gate.
11. Start → CHARACTER shows your portrait, level, health and equipped weapon.
    Start → SAVE writes the single battery-backed character slot.

## What is implemented and what is still a prototype

All characters and creatures encountered on this route use Warcraft art. Native
transparent exports include ten overworld characters (16×16), eight front/back
battle sets (56×56 / 48×48), animated PNGs, GIF previews and equipment icons.
Crystal's original inaccessible content remains in the source ROM. Full source
removal would be a separate engine cleanup. The player uses independent left
and right frames; ordinary NPC side frames are mirrored by Crystal.

The equipment backend has one real weapon slot, using the existing held-item
field and type damage bonuses. The shield and totem are starter story equipment;
there are no independently functional armor slots, armor scaling or complete
WoW character-sheet mechanics yet. White equipment is not an upgrade over the
quest's green club. The bags use the original 20-entry save allocation, so larger
future bags require a deliberate storage design.

Cutting Teeth and Sting use one enemy each rather than Classic's ten. Galgar
uses three harvests instead of ten. English dialogue is adapted and shortened;
these are not verbatim Questie/WoW quest-text exports. Galgar's bag reward,
Kento's intro and cave loot are prototype additions.

Maps are small connected block-based foundations, not completed replicas of
Durotar. Fog is per region, not per individual explored tile. The atlas currently
covers the implemented regions, not all of Azeroth. Detailed large concept art
is included separately from actual native-resolution screenshots; concept art
is not a claim about ROM rendering quality. The supplied MP3 has not been
converted to GBC audio; the engine's title music remains.

## Save compatibility and validation

No new WRAM/SRAM fields or item/map IDs were inserted before existing ones.
New quest/discovery/bag flags occupy previously unused event bits. The original
save allocation, checksums and single-slot behavior remain. An actual v0.1.1
battery save at The Den was continued successfully in the new ROM. Existing
characters keep their original name. Back up `.sav` / `.ram` before replacing a
ROM; positions outside the tested Den save and real cartridges are unverified.

Validation reports live under `references/generated/durotar_v02/`. Tests use
isolated temporary ROM copies and exercise normal buttons for the intro, naming,
quests, neutral/hostile mobs, vendor purchase, equipment, cactus/bag rewards,
map fog, all region transitions, imp loot, saving and cold restart. Renderer
checks force facing only; friendly defeat uses separately labeled HP injection.

## Reproduce

From the repository root, with RGBDS 1.0.4, Pillow, NumPy and PyBoy 2.7:

```sh
python tools/build_durotar_assets.py
python tools/build_durotar_extra_assets.py
python tools/build_durotar_maps.py
make -j4 RGBDS=/path/to/rgbds-1.0.4/
python tools/lint_durotar_text.py
python tools/validate_peon_intro.py
python tools/validate_peon_sprite.py
python tools/validate_peon_save_upgrade.py
python tools/package_peon_v02.py
```

Assets/visuals: `references/generated/durotar_v02/`. The asset ZIP contains a
local browser gallery: extract it and open `index.html`; no server is required.
