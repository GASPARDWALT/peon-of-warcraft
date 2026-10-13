# Readable native interiors v0.2.12

These five interior packets replace the old repeated bed/wall fragments with
one complete bed, bar, table and hearth around a clear central wood floor. They
are **source-based modular rooms**, not a literal import of the full source
room. Original source files and all exterior facade packets remain unchanged.

The only artwork input is
`references/characters/razor_hill_inn_gbc/razor_hill_inn_interior_192x160.png`,
SHA256 `3dafb5d6d1686a2d210b3bd93105ca39f3f12a5c1309d57203aef03204060f51`.
All composition pixels are pasted directly from that PNG at native scale.
No furniture is redrawn, resized, filtered or generated. `manifest.json`
records every source crop and placement, including the repeated structural
wall and clear floor tiles. Complete furnishings include their source shadows.
Additional beds, the lower table, animal hide, loose barrels and other source
decorations are excluded; the native budget does not support the full room.

`*_source_composition.png` retains the supplied crop colors.
`*_native.png` applies the actual four-colors-per-8x8-tile conversion using the
existing seven warm Peon background palettes. These are compiler previews,
not emulator screenshots. The 4x previews use nearest-neighbor display scaling;
the imported game art remains at 1x. Native tiles are frozen in the generated
`.2bpp` files and indexed tileset PNGs, with explicit palette and VRAM bank maps.

All five rooms use 175 patterns. These fit the
unchanged 192-pattern loader, protecting standard fonts, portraits, styled
names, walking sprites, emotes and HUD graphics. Static source hearth pixels
use `TilesetHouseAnim`, preventing the historical fire animation from writing
over the first source tiles. All background priority bits remain zero.

The service NPC stays at (6,4). The south exit moves internally to (5,9), with
the same warp index and `-1` return destination. The old (5,7) saved landing,
the Hearth return (5,6), and door approach (5,8) remain clear connected floor.
Bed/table interactions follow the new complete furnishings at (2,2)/(9,4).
Grommash Hold retains all four master coordinates and its initial (8,8) anchor.
Collision checks confirm reachable talking approaches. Generated Continue
relocations move only previously walkable cells now occupied by furnishings;
they add no saved fields and do not alter exterior relocation entries.

Regenerate these isolated assets with:

```sh
python3 tools/import_peon_readable_interiors_v0212.py --apply
```

This command writes only the versioned interior outputs and these five map
files. It does not invoke the old environment importer or an art generator.
The root integration includes `graphics.asm` in ROM, `palettes.asm` in the
existing attribute bank13, replaces only the five indoor header pairs using
`headers.asm`, loads `background.pal` only for these maps, and appends
`continue_relocations.asm` before the existing relocation-table terminator.
Build and runtime captures must verify the integrated packets in the actual ROM.
