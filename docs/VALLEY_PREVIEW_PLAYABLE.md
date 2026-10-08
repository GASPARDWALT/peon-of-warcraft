# Valley visual preview

This preview builds on the released v0.2.3 Shaman chapter. It prepares the
annotated Valley direction without changing the current map IDs, warp pairs
or save layout. One Den boulder block becomes a walkable merchant alcove to
keep the new sellers outside the crowded center. The seven-screen layout is
not implemented yet; the Den and Valley still use the existing scrolling maps.
See `VALLEY_SCREEN_LAYOUT.md` for the intended geography and migration work.

## Play

Extract the preview ZIP and open its `.gbc` in a Game Boy Color emulator.
D-pad moves, A interacts/confirms, B cancels, Start opens the menu, and Select
opens the earned zone atlas. Gornek awards the atlas after his second quest.
It shows the player on the current discovered region, questgiver states and
remaining active objectives. It is still a region atlas, not a combined
overview of all seven requested Valley screens.

The Den adds provisioners selling water, Minor Potions and Tough Bread.
Five bread cost 25 copper, matching the verified Classic vendor offer.
Use bread from BAGS outside combat for up to 10 HP; a full-health character
keeps it. This instant healing is a prototype adaptation of Classic food.
Potions retain their combat turn cost. Warrior MoCMoc and Warlock Xasthur
have their own appearances and refuse Shaman training. A Razor Hill guard
patrols a short bounded lane clear of required doors.

Two hostile level-three Vile Familiars guard the cave approach. Each defeated
enemy disappears permanently and grants 30 copper once, with no item drop
or free heal. Rest at an inn and buy supplies before entering the cavern.
Existing quests, cacti, equipment, spell training and battles remain available.

The native décor uses more faceted ochre rocks, layered canyon shelves, Horde
crests, lashed palisades and brighter flames within the same 192 tile slots.
A small Peon portrait and a red life gauge show actual current/max HP while
walking. The HUD hides during dialogue, menus and combat. It uses a compact
version in crowded views and can temporarily hide when hardware sprite limits
leave no safe space. Mana is not implemented by this preview.

The boar grunt and Lightning Bolt effect use original short GBC pulse/noise
synthesis. Wowhead's sound catalog returns a proxy 403 from this environment;
these have not been measured against the user's eventual WoW reference files.
Native APU WAV previews accompany the captures in `sound_effects/`.

## Saves and hardware

Use the emulator's native battery save, not a save state, across versions.
Back it up, then copy it beside the new ROM using the same basename and
your emulator's `.sav`, `.srm` or `.ram` extension. There remains one real
save slot. No event IDs are shifted; the two new enemy flags use reserved
space. Continue refreshes the one changed alcove block and its screen cache,
so an older save cannot leave the new vendors behind the old boulder.
Physical Chromatic/cart/RTC testing remains to be done.

The ROM retains the CGB-only, 2 MiB, MBC3+RTC, battery-backed 32 KiB SRAM
contract. This preview does not certify a particular flash cartridge.

## Visual files

All new public images, reconstructions and actual emulator captures are in
`references/generated/valley_layout_update/`. Prepared transparent icons and
compiler map reconstructions are labeled separately from runtime captures.
The annotated user images remain visible in chat; they are not falsely
identified as existing unannotated repository files.

Rebuild using `sh tools/rebuild_peon_valley_preview.sh`. Do not run the old
world/item generators to overwrite calibrated combat data or released art.
