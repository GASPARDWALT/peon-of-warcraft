# Native player portrait and life gauge

The overworld HUD reads the apprentice's actual `wPartyMon1HP` and
`wPartyMon1MaxHP` on every sprite refresh. It is a native ROM overlay, not an
HTML mockup. The red gauge follows combat damage and ordinary inn healing.
The current single-character implementation continues to use Crystal's first
party member as its character-stat backing data. No save fields are added.

The normal panel occupies 52×16 pixels at the upper left: a 16×16 hand-pixelled
Peon face and a 32-pixel life gauge. Native OBJ palettes 2 and 0 supply green
skin and red life without changing the map, quest-marker or enemy palettes.
There is no new mana resource or artificial mana reading in this patch.

Crystal and GBC allow 40 hardware objects overall and ten per scanline.
Fully offscreen8×8 tiles are omitted from the final OAM table; partially visible
tiles and actor structs remain unchanged. Every visible world tile retains its
complete OAM entry and relative order. At the normal Den spawn, four wholly
offscreen tiles are freed so the compact portrait and life bar are visible.
The HUD
uses eight additional objects only when both budgets permit it; a busier view
uses an eight-pixel face and a 24-pixel gauge in four additional objects.
In an exceptionally dense view the HUD is temporarily omitted. A stack-only
composition buffer shifts the world once per refresh, limiting the overlay to
at most 160 OAM byte writes instead of repeatedly moving every world object. UI priority
places the portrait over scenery/actors immediately behind its small rectangle,
as expected of an overlay. Its conservative upper-row budget prevents the HUD
from introducing scanline clipping into the rest of that row.

The HUD hides during dialogue, scripted sequences, battle and menus. Menu and
atlas exits use the existing map graphics reload to restore the fourteen native
tiles at OBJ bank 0 `$8600..$86df`. This reservation is below the standard font
and above the supported Peon maps' second standing-sprite table. The native
validator checks the standing-sprite allocations at every graphics reload.

Relevant implementation:

- `engine/overworld/peon_player_hud.asm`: graphic load, budget checks, live
  life-gauge calculation and OAM composition.
- `engine/overworld/overworld.asm`: world-graphics reload hook.
- `engine/overworld/map_objects.asm`: sprite-refresh hook.
- `tools/build_peon_player_hud.py`: deterministic native/transparent assets.
- `tools/validate_peon_player_hud.py`: ordinary intro, wounds, healing,
  dialogue/menu returns, actual hardware OAM/VRAM/pixels and explicitly labeled
  capacity/HP-bound diagnostics.

Assets and actual captures are saved under
`references/generated/valley_layout_update/hud/`. Files named
`*_asset_preview*` are graphics previews; files named `*_in_rom*` are actual
160×144 emulator captures. The JSON report identifies the exact tested ROM.
