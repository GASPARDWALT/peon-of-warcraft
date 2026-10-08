# Native world polish

The world patch starts from the published audio preview, commit `1435e70`.
The retained thirteen playable map arrays have no byte-identical duplicates
after this patch. The two original duplicate pairs were Orc/Troll residences
and Orc/Troll inns; the outdoor maps were already distinct.

The four room types now read differently: short red rugs and sandstone for
orc residences, woven timber and a spirit mask for Darkspear homes, sandstone
aisles and tall braziers for orc inns, and woven bedding and a low ground hearth
for the troll inn. All furniture interaction positions remain intact.

Map IDs, dimensions, warp coordinates, exit targets and actor coordinates are
not changed by the world builder. The Den and Razor Hill still use one shared
Orc Inn room ID; residences still share their race's room ID. Every return
must lead to the exact door used to enter, including after a battery restart.
This patch does not claim a unique room allocation for every building.

## Native trees and memory budget

Nine deadthorn trees are placed on existing boulder cells, outside the mandatory
route. The native tree uses the prepared `deadthorn_tree.png` geometry with
three opaque wood colours plus transparent ground. It is drawn at 32×32;
there is no rescaling or soft sampling of the tree silhouette.

The background allocation remains exactly **192 8×8 tiles**. To make room for
sixteen tree tiles, sixteen extremely similar tile patterns were merged within
their existing palette. Across the 192 old tile patterns this changes **37
indexed pixels**, with a hard maximum of **three pixels in any original 8×8
pattern**. All soil grain patterns are protected. Reduction prioritizes the
smallest total used-pixel change, preserving widespread sand detail. Palette
assignments and collision semantics are preserved. The
builder always reads immutable baseline inputs, preventing repeated runs from
compounding this reduction.

New block IDs are appended after the original 42 blocks:

| ID | Artwork | Collision |
| --- | --- | --- |
| 42 | Deadthorn tree | Wall |
| 43 | Darkspear bedroll | Wall |
| 44 | Darkspear table | Wall |
| 45 | Woven timber floor | Floor |
| 46 | Darkspear spirit mask | Wall |

Every old cell retains its exact four movement collision values, including
cells that could contain an arbitrary old saved player position. No new tree
blocks a previous floor, doorway or quest approach.

The Den has clearer beaten-earth branches toward the vendor alcove and class
camp. The existing eastern Valley exit gains stone boundary jambs. These are
small improvements to the current connected scrolling maps; the requested
seven fixed screens still await the final path drawing and a separate camera
and saved-location migration design.

## Generation and verification

Run `python tools/build_peon_world_polish.py`, then regenerate the atlas with:

```sh
python tools/build_durotar_maps.py \
  --source references/generated/deep_polish/world \
  --output references/generated/deep_polish/world
```

The PNGs under `references/generated/deep_polish/world/maps/` are explicitly
labelled **compiler reconstructions**, with no NPCs painted into the terrain.
The transparent tree is `world/props/deadthorn_tree_native.png`. Original
published image galleries and release archives are preserved.

`world/validation.json` checks the tile budget, per-pattern pixel reduction,
all thirteen collision grids, all current warp paths, actor/background-event
approaches, and the absence of duplicate playable map arrays.

After building the ROM, `tools/validate_peon_world_polish.py --expected-sha SHA`
uses ordinary game buttons to enter all nine doors, return to their originating
locations, and save/cold-restart once inside each of the four room IDs. Read-only
observers compare both native terrain VRAM banks with the compiled tiles and
the loaded map blocks with current authored `.blk` data. Captures and the
native report go to `references/generated/deep_polish/world_runtime/`.

The global Peon Continue terrain refresh is required: Crystal's thirty saved
screen blocks otherwise overwrite newer map art. Current tile callbacks
reapply persistent harvested-cactus state after terrain reload. This is
separately checked by the release's old-save migration test.

Physical Chromatic hardware remains a separate verification step.

The frozen candidate `704022c22c441944d13e3ff65950a971e5c7ead614a1ff0e1bba476c340bea2d`
passes all nine door routes, all four room cold restarts, the actual terrain
VRAM checks, and the loaded-block cache checks. The actual gameplay sheet is
`references/generated/deep_polish/world_runtime/four_room_cold_restarts_contact_sheet.png`.
