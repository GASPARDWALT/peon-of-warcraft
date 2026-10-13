# Uploaded Durotar decor — native ROM import v0.2.11

Sources remain intact in `references/characters/durotar_asset_pack_v1/` and
`references/characters/razor_hill_inn_gbc/`. The importer uses those real PNG
pixels, not any historical drawing generator. Native source dimensions and
placement grids remain unchanged; the derived 2bpp graphics select one of the
existing seven scene palettes for each 8×8 tile.

The full 96×80 Razor Hill exterior is used at all nine existing house/inn
entrances in The Den, Sen'jin and Razor Hill, plus two existing closed guard
lodges at the Orgrimmar gate. The old Razor Hill towers beneath these enlarged
facades are superseded by the new source architecture. Its doorway is centered at the
original warp. All six existing palm anchors use the whole 32×48 palm canvas,
including its canopy. Round/tall cactus, large rock, Horde banner, palisade
modules, skull, sand/cracked ground and all three 16×16 brazier frames come
from the Durotar pack. Old unprovided deadthorn silhouettes use the provided
round cactus at the same solid anchor.

The four 192×160 shared interiors and the 256×192 cinematic Grommash hall use a **source-derived modular assembly** of the
uploaded interior: copied corners, wall panels, beds, tables, hearths, doorway
and repeated native wood-floor modules. The hall retains its cinematic carpet and master positions. The original interior uses 455 unique
8×8 patterns after palette conversion; it cannot be a literal complete tilemap
in this engine's 192-pattern allocation. The modular rooms preserve source
pixels at 1:1 within each recorded crop; the source itself is not downsized or
overwritten. Doorway and service NPC positions remain unchanged. Seventeen previously
walkable movement cells now form physical facade body walls; protected door
landings, patrols and NPC talking approaches stay reachable. The other 5,107
movement cells retain their original collision values. A breadth-first search
checks every warp and service approach in all 18 maps.

Per-map native graphics packets permit this artwork within 192 patterns per
map while retaining `TILESET_PEON`. Original block meanings 0–66 remain
available. Each map appends only its own visual aliases (fewer than 128 total),
with original collision values except the documented 17 new body-wall cells. The map header
selector also retains the original palette/font and quest/HUD hooks. Dynamic
`changeblock 38` and each map's border block are included in its allocation.
Inactive block entries reuse the first scenery pattern; no active source tile
is dropped to meet the budget.

A generated 17-entry Continue relocation table moves legacy saves on these
new body walls to nearby reachable safe floor. It runs after the existing v029
relocation pass, preserves all character/save fields and synchronizes native
player coordinates. Normal arrivals retain the established warp coordinates.

The walkable upper roof/eaves use the native GBC background priority bit.
Each map carries a 32-byte priority bitset in the existing unused tileset
header word (`wTilesetAnim + 2`). Initial and scrolling attribute loading call
a small same-bank helper to add bit 7 while preserving palette and bank bits.
The helper caches the caller tile ID before selecting WRAM1 for header reads,
then restores the original WRAM bank and loop registers.
Font IDs 96–127 and animated fire IDs 0–3 have zero priority flags. This keeps
walking characters behind the roof without blocking their existing routes.

The three uploaded brazier phases now require four exclusive animated 8×8
tiles at IDs 0–3. They use the engine's existing animation timer; graphics for
other objects cannot reuse those four patterns.

`manifest.json` records source hashes, crop coordinates, full-object placements,
per-map allocations and unused assets. `native_conversion_validation.json`
checks all movement-cell collision changes, safe Continue destinations, roof priority masks and native packet sizes. The `previews/`
images are compiler reconstructions, **not emulator screenshots**. Runtime QA
captures are produced separately from the final rebuilt ROM.

Larger cave entrance, unused alternate props/banners and the former generic
Durotar hut/inn sources remain available without claiming they are imported.
The opening scene contains no building; its full palm is imported separately.
All enterable service facades, the two standalone guard lodges and the cinematic
hall now use the supplied architecture. Guard lodges retain their existing
closed/non-enterable behavior; no invented warp or service is added.
