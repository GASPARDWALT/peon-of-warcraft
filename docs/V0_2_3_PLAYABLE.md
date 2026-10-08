# Peon of Warcraft v0.2.3

This patch retains the playable Shaman chapter from The Den through Valley of
Trials, Burning Blade Cavern, Sen'jin, Razor Hill and Orgrimmar Gate. It adds
apprentice movement during battle and revises attrition between encounters.
See `V0_2_3_COMBAT_AND_BALANCE.md` and the packaged runtime reports for measured
behavior and the limits of ordinary-button tests versus isolated diagnostics.

Extract `peon_of_warcraft_v0_2_3.zip` and open the `.gbc` in a GBC emulator.
Use the D-pad to move, A to interact/confirm, B to cancel, Start for character,
bags, map, save and Hearthstone, and Select for the earned zone map.
The map is awarded after Gornek's second quest; undiscovered zones stay hidden.
Yellow-outline creatures are neutral; red-outline enemies attack on proximity.

The apprentice keeps a crude mace, wooden shield, belt totem and Lightning
Bolt. Kento offers paid, level-gated training. Battles keep four prepared
attacks. BAGS provides potions, water and the reusable Earth Totem. Consumables
and totem placement spend a turn. A third encounter without recovery can be
dangerous: buy supplies and deliberately visit inns. No win grants a free heal.

Quest markers, harvestable cacti, one-time XP/equipment rewards, finite visible
enemies, doors, inns and native music remain part of the same chapter. Other
class routes, full equipment slots, multiple saves and simultaneous party
combat remain unimplemented. No new world maps are added by this patch.

Back up a battery save before migrating it to the new ROM basename. Retain
your emulator's `.sav`, `.srm` or `.ram` extension. Use native battery saves,
not emulator save states, across versions. Continue reloads current Peon NPC
definitions while retaining the player location, inventory and progress.
Wandering NPCs reset to their defined starts. Existing v0.2.2 characters keep
their reusable Earth Totem; Kento cannot grant a duplicate. Older characters
can obtain it at Kento and retry later if their bags are full.

The ROM contract remains CGB-only, 2 MiB, MBC3 with RTC and battery-backed
32 KiB SRAM. Physical ModRetro Chromatic/cart/RTC testing remains unperformed.
The release packager requires fresh prior runtime reports, the new movement
and balance reports, four real-version save upgrades and browser QA, all on
the exact packaged ROM hash.

Extract the art ZIP and open `durotar_v023/index.html`, keeping its sibling
`durotar_v022`, `durotar_v021`, `durotar_v02` and `title_portal_gbc` folders.
Concepts, prepared/locked art, diagnostic fixtures and historical captures are
identified separately. The current gallery links directly to PNG/GIF files.

Rebuild retained native inputs through `tools/rebuild_peon_v023.sh`. Existing
v0.2.2 data generators are not rerun to overwrite calibrated combat stats.
