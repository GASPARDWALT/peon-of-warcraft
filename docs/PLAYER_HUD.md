# Native player portrait and life gauge

The overworld HUD reads the apprentice’s actual `wPartyMon1HP` and
`wPartyMon1MaxHP` on every sprite refresh. It is native ROM output, with no
new persistent fields or mana system. Combat wounds and inn healing update
its red life gauge.

## Fixed geometry

Every eligible world view uses the same four hardware objects: an 8×8 Peon
face and a 24-pixel life gauge, both anchored on screen row 3. The precise
ink bounds are `(2,3)..(36,11)`, or 34×8 pixels. Its position, face, bar width
and scale no longer change when NPCs enter or leave the viewport. This fixes
the former switch between a 16×16 portrait and an 8×8 miniature.

The four-object footprint is deliberate: the normal Den spawn already uses
36 visible world objects, and GBC has only 40 total. A permanent eight-object
portrait would discard actors or disappear at that ordinary spawn. The full
portrait remains a prepared asset; the world renderer uses only the fixed
small face. A larger permanent panel requires a separate background renderer
rather than spending more of the current world object budget.

The gauge uses floor division with one minimum red pixel while actual HP is
nonzero, so an apprentice at critical health does not look already defeated.
Zero HP or zero maximum HP displays an empty gauge. HP above its maximum is
clamped visually to a full bar. A 24-bit multiplication intermediate keeps
partial fills accurate across the complete native 16-bit HP range.

## Native object limits and safe omission

Every completely offscreen 8×8 tile is omitted from final OAM. Partially
visible tiles and all actor structures remain unchanged, and every retained
world tile keeps its full data and original relative order. At most 36 such
world objects may coexist with the four-object HUD.

The HUD checks the GBC ten-objects-per-scanline limit. A quick union accepts
ordinary empty upper rows; dense upper rows are checked individually across
all eight HUD scanlines. This permits disjoint-row actors that the old union
check falsely treated as crowding. On an exceptionally unsafe frame, the
whole HUD is omitted rather than shrinking it or clipping NPCs. The panel
never switches size. The four HUD objects take priority only inside their
small rectangle; actual emulator tests compare every other pixel against an
otherwise identical HUD-disabled render.

Only existing OBJ palettes 2 and 0 are read: green skin and red life. A
16-byte stack composition buffer shifts retained world OAM once; no new
save or temporary RAM allocation is required.

## Other interfaces and graphics reservation

The HUD hides during dialogue, scripted sequences, battles, maps and menus.
Map graphics reload restores the existing fourteen tiles in OBJ bank 0
`$8600..$86df`; their byte content and allocation are unchanged. The two level
aura tiles immediately afterward remain separate. Native validation checks
standing-sprite allocations and reloads after dialog, battle, menu and map
returns.

Relevant implementation:

- `engine/overworld/peon_player_hud.asm`: fixed geometry, exact scanline
  budgeting, live health fill and actor-preserving OAM composition.
- `engine/overworld/overworld.asm` and `map_objects.asm`: existing graphics
  reload and refresh hooks; no new hook or map event is added.
- `tools/build_peon_player_hud.py`: reproducible native and transparent
  assets, written to the new deep-polish folder.
- `tools/validate_peon_fixed_hud.py`: ordinary intro, crowded/scrolled views,
  wounds, healing and UI return captures; separate explicit capacity,
  scanline, critical-HP and invalid-maximum diagnostics. It checks actual
  hardware OAM and RGB555 pixels, CPU register preservation, palettes,
  actor order and protected player/world data.

Current assets and captures are in
`references/generated/deep_polish/hud/`. `*_asset_preview*` denotes prepared
art; `*_in_rom*` denotes actual 160×144 emulator output. The JSON report
records the exact tested ROM. Earlier released assets and reports in
`valley_layout_update/hud/` are historical and remain untouched.
