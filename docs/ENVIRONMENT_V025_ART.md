# Native environment redraw for v0.2.5

All 47 environment block definitions have original new pixel art. The builder does
not redraw from old tile graphics or resize the large generated concept into
the game. The Warcraft/WoW reference hierarchy and source inspections are in
`ENVIRONMENT_V025_REFERENCES.md`; the concept remains an illustration only.

Orc structures use red hide, ivory tusks, warm timber and dark arched doors.
The 64×64 Den roof has a stitched hide seam and curved tusk supports. Troll
roofs use light ochre thatch and woven timber details. Cliffs have layered
sunlit sandstone and broad darker sediment planes; boulders have angular
facets. Cacti have red blooms, inland dead trees retain open branch gaps, and
coastal palms have leaning trunks and coconuts. Standards, palisades, fortified
jambs, signs, ritual masks, bedding and tables follow the same colour rules.

The current block IDs, collision definitions and actual door coordinates are
retained. Hut blocks 4/29 have their visible entrance in the bottom-right
movement quadrant, `x16–31, y16–31`, open at the right edge for Razor Hill's
east-approached hut. Den block 11 has its door at global `x16–31, y48–63` in
the 64×64 image. Cave block 15 is a dark rock mouth above the separate open
transition block 16. Closed fortified jambs do not imply another entrance.

Road variants 17–26 keep their named connections. Their 24-pixel-wide centre
band spans `4–27`, placing both movement-cell centres clearly on the beaten
earth. Full transition block 16 remains open in all four movement quadrants.
Separate path work updates the existing branches without changing their
collision or save allocation. Seven fixed screens are still a separate camera
and saved-location migration; this art patch does not claim that migration.

## Native allocation and precision

The final atlas uses **192 8×8 patterns**, 96 in each native background bank.
Every tile has one palette with four RGB555 colours. Palette data and previews
use `tools/build_peon_environment_palettes.py`; no approximate RGB rounding or
historical palette generator is used by the environment compiler.

The direct modular drawing yielded 201 patterns. Nine tiny shade variants
share patterns to fit the hardware allocation, changing 43 shade pixels across
the original patterns, at most seven in any 64-pixel pattern. Every merged
pair keeps its exact palette and zero/nonzero silhouette. All plants, cave
patterns, actual door quadrants, Horde emblems and the animated flames are
protected. There is no image resampling or antialiasing.

Two unique flame tiles occupy native IDs 0/1 in bank 0 at `$9000/$9010`.
Only braziers (34) and campfires (39) reference them. Three poses use palette 4
for a warm amber/cream core, including underground. The animation file is
96 bytes: phase-0 left/right, phase-1 left/right, phase-2 left/right, 32 bytes
per pose. Runtime animation belongs to the root engine patch and requires
separate native verification.

## Reproduction and inspectable assets

Run `python tools/build_peon_environment_v025.py`. It gates the tile budget
before replacing the native graphics, preserves the 47 block indices, and
writes only the new `references/generated/environment_v025/` evidence tree.
It does not write map arrays or collision scripts or build the ROM.

- `props/`: clearly named transparent native PNGs and nearest-neighbour 8×
  previews; the full Den is `the_den_horde_hide_and_tusks.png`.
- `blocks/`: all 47 native block RGBA images and enlarged previews.
- `sources/`: index images, palette grids and binary alpha masks for inspection.
- `maps/`: current-map compiler reconstructions, explicitly not emulator captures.
- `manifest.json`: block coverage, exact palette data, changes, file names and
  door alignment.
- `budget_review.json`: exact native allocation and bounded shade sharing.
- `fire_animation.json`: animation tile IDs, banking and three-pose byte layout.
- `static_art_validation.json`: independently recomputed native pixels,
  palette/bank attributes and fire bytes match the frozen drawing.

Transparency in prop PNGs has only alpha 0/255. Background margins are baked
into the regional ground when compiled for the ROM. Full ground/water/floor
textures naturally occupy their complete tile rather than being isolated
object cutouts.

Frozen native inputs:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `gfx/tilesets/peon.png` | 2849 | `8eaf7fdbdaab0b33d61a2a8572c87a9c6af6f940acd1c454d6c2421cbaa93bca` |
| `gfx/tilesets/peon_palette_map.bin` | 128 | `bac92394bc0f45254d8d7c0517841cff72ad086d157129bd464f0ae4bde9abe5` |
| `data/tilesets/peon_metatiles.bin` | 752 | `99d627482f3bd5de2fdc739d2a2057b99e155dbfacc3ad2670fa1a47a2ed3e79` |
| `gfx/tilesets/peon_environment_fire.bin` | 96 | `a8623b0ac352e1ba0817055b6ff1ff70d6cfef14aacb397fea3ecb80b3265962` |

Static drawing checks pass. ROM captures, region transitions, fire frame writes,
door traversal and battery-save cold restarts are recorded by the native QA
agent after the full build. Physical Chromatic testing remains separate.
