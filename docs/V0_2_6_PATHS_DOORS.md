# Native doors and paths, v0.2.6

The playable map layout remains the published v0.2.5 layout. This pass redraws
the native entry cues so the visible entrance matches the movement cell that
actually enters a room. It also adds low stone steps at map transfers and
small shared pebble shadows to the sand paths.

All 18 map block arrays, map IDs, warp coordinates and destinations, NPC
coordinates, quest triggers and 47 collision rows are checked byte for byte
against published commit `d2806e2`. The seven-region route remains:

```text
1 The Den → RIGHT → 2 Valley
2 Valley → UP → 3 Crossroads
3 Crossroads → LEFT → 4 Hana'zua
4 Hana'zua → DOWN → 5 Sarkoth
5 Sarkoth → RIGHT → 1 The Den
3 Crossroads → UP → 6 Cave Approach → UP → Burning Blade Cavern
2 Valley → RIGHT → 7 Fortified Exit → RIGHT → Durotar Road
```

The Orc and Troll huts and the larger Den building now share a dark arched
16×16 doorway with an ivory rim and a small step. That image lies in the
bottom-right movement quadrant, the only passable quadrant of building
metatiles 4, 11 and 29. The eastern lip stays visually open because the
southwestern Razor Hill hut can only be approached from its east side: its
southern neighbor is an existing impassable palisade.

The cave mouth is above the right-hand lane, aligned with the real Cave
Approach entrance at `(5,2)`. The decorative mouth itself remains rock
collision; stepping onto the flat threshold below it performs the transfer.
Its left half is geological cliff rather than a second dark opening. The
watchtower has closed wooden shutters because it has no entrance event. The
retired Valley cave and the northern Orgrimmar prototype boundary remain
closed. Their artwork does not create additional destinations.

Map-transfer metatile 16 has a low stone line. All four original
`WARP_PANEL` quadrants remain intact. Roads keep their original shape and
collision meaning; the new pebble shading adds depth without drawing a
solid barrier across the walking lane. A road ending at a published closed
boundary remains a closed boundary. No new sea passage or map edge is opened.

The root-authored Horde emblem uses four native tiles shared by banners and
hall rugs. The complete environment still fits in 192 native patterns and 47
metatiles. The two animated fire patterns and their three frames are unchanged.
The allocator only merges nearby shade variants while keeping palette and
transparent silhouette unchanged. Doors, cave details and the emblem retain
their protected native patterns.

`tools/build_peon_environment_v026.py` writes the four native environment
inputs and new review files under
`references/generated/visual_polish_v026/paths_doors/`. It never writes to the
published v0.2.5 evidence. Transparent native prop PNGs are in `props/`, all
47 native block PNGs are in `blocks/`, and maps with cyan actual warp cells
are in `annotated/`. These pictures are compiler reconstructions, clearly
labelled separately from actual ROM captures in `runtime/`.

The release gate is `tools/validate_peon_paths_doors_v026.py --expected-sha
<release-ROM-SHA>`, with the PyBoy preview toolchain on `PYTHONPATH`. Its final
report is `paths_doors/validation.json`; the static drawing/geometry report is
`paths_doors/source_validation.json`. Only a report with `passed: true` and
the exact release ROM hash counts as native validation.

The normal-input test route checks all nine village doors and exact exterior
returns, cold saves in all four room types, all nine geographic links in both
directions, real cave-guard victories, three cactus harvests and an earned
atlas. It observes actual scenery RGB555 pixels, palette upload, all 192
terrain tiles and 512 fire frames. Character and Bags are opened inside and
after every door and after each room's cold restart: 22 restoration cases.
They check native regular and bold-name glyph pixels, the fixed 20×18 frame,
unchanged class/kit/health/charges/money/quests, and native scenery after the
menus close. The original native field-name font is restored on close; the
separate new body font is verified again whenever a menu opens. The inherited
earned-atlas check also verifies its two-bank
upload and restoration of the regular font and environment.

All emulator batteries are private temporary files. The main route uses
ordinary buttons and read-only observers; it does not modify game RAM or
load emulator states. A poisoned victorious character deliberately walks to
the inn healer before continuing the long tour, then returns to the original
map and cell. Native poison remains active gameplay, rather than being
disabled by the validation harness. A physical Chromatic/cart test is still
required.

The session class also guards direct diagnostic use: its capture method
always writes beneath the new v0.2.6 folder, even when the retained validators
have not been redirected. Direct probes and earlier failed candidates go in
`preliminary/` and are excluded from the release gallery. The complete route
redirects nested retained output globals as well, including fire GIFs and
runtime reports. Published v0.2.5 captures remain immutable.
