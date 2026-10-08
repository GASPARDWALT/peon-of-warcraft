# Valley of Trials: annotated layout contract

The user's full annotated Valley map was received in chat on 2026-10-08.
The image has seven green rectangles, numbered 1–7. The original annotated
attachment is visible in the conversation; it has not been stored as a
repository source file. Do not claim an existing unannotated reference is that
attachment. Existing terrain references remain under
`references/zones/valley_of_trials/` and `references/zones/the_den/`.

## Meaning of the annotations

- Red: impassable mountains defining the edges and passages.
- Off-white: the walls at the Valley exit, in zone 7.
- Green rectangles: approximately what the player should see on each screen,
  including the corresponding Warcraft landmarks and decorative placement.
- Zone 4: Hana'zua offers the Sarkoth quest.
- Zone 5: Sarkoth's encounter.
- Zone 6: the cave entrance, hostile level-three imps outside it, and a
  separately loaded cave interior.
- In the zone-1 Den close-up, blue dots identify the vendor camp (potions,
  water and food); the purple dot identifies the class-training camp below.
  The Warrior and Warlock masters must rebuff the Shaman without granting
  equipment, class changes or another reward.
- A few guards may patrol one or two safe steps. Quest givers/vendors remain
  findable; patrols must not intersect a required doorway or hostile trigger.
- Paths must use readable beaten earth and rock-framed openings. The user is
  supplying an additional path drawing; final connections are pending that
  drawing. Do not silently invent the requested path topology.

The atlas should show the complete Valley outline, the current player and
yellow `!` at remaining actions for accepted quests. Exploration fog remains
required; keeping the outer silhouette visible need not reveal unexplored
interior details. Quest-giver states stay yellow `!`, gray `?`, yellow `?`.

## Implemented preparatory patch

This patch prepares the cave approach on the existing map and improves road
contrast. It does **not** yet claim to reproduce the seven requested screens.

Two hostile red level-three imps are appended to the current Valley map at
`(25,6)` and `(27,9)`. Each has its own permanent victory flag and awards
30 copper without an item drop or free heal. Interaction and proximity use the
same guarded script. Defeat uses the existing bound-inn recovery. Existing
quest actor indices, event IDs, map IDs, coordinates and warp pairs are retained.

The exterior familiars use previously unused Valley OBJ palette 6; gray active
quest markers keep palette 5. Reloading the map must restore both. The existing
cave entrance `(24,4)` and interior return `(10,16)` remain connected.

Path palette 4 uses more contrasting beaten earth in outdoor regions, amber
against Sen'jin's pale sand, and a cool gray trail underground. No collision
data is changed in the Valley. In The Den, block `(4,3)` changes from a boulder
to walkable floor for the two new merchants at `(8,6)` and `(8,7)`. Native
testing exposed OAM clipping with their first placements near the crowded
center; the alcove keeps the vendors accessible near the blue reference dots.
Existing actor coordinates and warp cells are unchanged.
Continue repairs this one block after Crystal overlays its saved 30-block
screen cache, then buffers the screen again before initializing current NPCs.
The native v0.2.3 upgrade test walks to both alcove cells to verify the repair.
`tools/build_peon_wayfinding_preview.py` refreshes
the retained palettes and creates clearly labeled compiler reconstructions
under `references/generated/valley_layout_update/`; actual game captures are
separate.

## Required before the seven-screen migration

The current Valley remains a scrolling map, not seven fixed screens. A native
screen is 160×144 pixels, or 10×9 movement cells. Crystal uses 32×32-pixel blocks;
a 5×5-block map is 160×160 and still follows the player. Literal fixed screens
require a deliberate camera/border change.

Append new map IDs after current map 24; never insert IDs among existing maps.
Translate saved map/XY and player-object coordinates once, and rebuild the
saved 30-block `wScreenSave` overlay. Refreshing only NPC pointers does not
migrate saved terrain. Keep quest/death flags, bag contents, HP/charges and
bound-inn destinations. Update atlas/palette/marker lookups which currently
assume the contiguous map IDs 14–20 or Valley's actor slots 5–7. Verify ordinary
entry/exit and a real battery-save cold restart from each affected zone.

This milestone waits for the path drawing before defining final screen edges
or relocating Hana'zua/Sarkoth. It must preserve the published v0.2.3 artifacts.
