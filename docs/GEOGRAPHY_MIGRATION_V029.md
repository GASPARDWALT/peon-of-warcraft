# Valley cliffs and save migration — v0.2.9

The geography proposal follows the seven relative regions of the annotated
Valley of Trials reference. The red annotations represent solid mountains,
and the ivory annotations represent the eastern exit walls. They are not
requests to paint the mountains bright red. The annotation image itself is
visible in the conversation; the repository's measured region rectangles are
approximate, so this is not a pixel-for-pixel trace of its red boundary.

The original map IDs, dimensions, nine pairs of portals, painted roads,
buildings, quest actors, and cactus coordinates remain stable. The Den still
uses a 384×320-pixel scrolling map, Valley of Trials 512×384, and the other five
sectors 160×160. A literal screen-per-region camera is not implemented here.

| Link | Direction |
| --- | --- |
| The Den → Valley of Trials | Right |
| Valley of Trials → Crossroads | Up |
| Crossroads → Hana'zua Camp | Left |
| Hana'zua Camp → Sarkoth Basin | Down |
| Sarkoth Basin → The Den | Right |
| Crossroads → Cave Approach | Up |
| Valley of Trials → Valley Exit | Right |
| Valley Exit → Durotar Road | Right |
| Cave Approach → Burning Blade Cavern | North cave entrance |

Fourteen appended metatiles, IDs 53–66, combine the existing cliff and bare-soil
quadrants. They add no 8×8 patterns or palettes to the 192-pattern allocation.
The first 53 metatiles and their collision meanings stay unchanged. New walls
join the outer mountain rim; they do not form free-standing invisible islands.
All NPC/quest/portal approaches and reserved new recruitment/pack anchors are
protected. The ivory fortification remains only along the east edge of region
7, with mountains elsewhere.

The changed external geometry converts 68 former FLOOR cells into WALL. A
Continue-only table relocates saves on those exact cells to reachable safe
floor. It does not change the map or its identity, reset quests, give rewards,
or move players during ordinary arrivals. Its nearest landing excludes warps,
actors, and aggro triggers. There is no new persistent geography field.

Eight further Continue entries handle newly occupied body anchors: the Earth
Spirit, Orc Grunt, neutral imp, two Kolkar, moved Road pack, and two Sen'jin
recruits. The complete table therefore has 76 rows. Most body landings are
adjacent; each Kolkar's four adjacent cells are planned aggro, so its landing
is two cells away on verified safe floor. This moves an old save out of an
NPC without granting a kill flag or silently starting the pack.

One combined-case correction keeps old Valley Exit save `(2,7)` on the safe
western road `(2,4)`. The original nearest landing `(2,6)` acquired Kolkar aggro
on its only two exits when those enemies were added. The corrected landing has
an ordinary western route through `(1,4)` to the original portal `(0,4)`.
`continue_landing_overrides.json` records this correction separately; the 68
blocked-cell identities and the original preparation records remain intact.

Preparation played the frozen v0.2.8 ROM
`943d460f6f76e15dff5b0fc2b8b11b90ba4c2ae79d5e190ea9dd3870b4d68620`
through ordinary buttons and native Save. It obtained 51 private 32 KiB
batteries: all 44 reachable changed cells plus one unchanged control in each
sector. Each battery was cold-continued on that old ROM and its full recorded
identity, party, XP, HP, inventory, money, flags, and location compared. The 24
other changed cells belong to pre-existing isolated floor pockets; no emulator
states or fabricated batteries were used for them. A normal Sarkoth victory,
the two starting healing potions, a real inn rest, and one familiar victory
opened otherwise blocked western ledges for the ordinary preparation route.
Seven additional old-save body anchors and five Road locations were also
prepared through actual walking/Save/cold Continue. With both optional fixture
groups enabled, the candidate suite covers 63 real batteries. Two Road controls
stand on the preserved WARP_PANEL quadrants next to the actual Sen'jin warp;
they are walkable transition tiles, not literal FLOOR or additional portals.

`tools/validate_peon_geography_v029.py --expected-sha SHA --rom FROZEN_ROM
--symbols FROZEN_SYM --include-road-saves --include-actor-saves` performs the
candidate upgrade check. It requires actual
ROM metatiles, collision quadrants, map blocks, reciprocal portal bytes, and
the complete migration table to match the proposed geometry. Each changed
battery must invoke the relocation once, each control zero times. After
Continue, the candidate must retain the recorded save data, apart from the
documented position and mana initialization bytes, show matching native floor
pixels, and permit an ordinary step away. Pass/failure evidence is written to
`references/generated/geography_v029/continue_validation.json`; the preparation
report is `old_save_preparation.json`. Prepared PNGs under `proposed/` are
source reconstructions, while candidate captures under `continue_runtime/`
come from actual emulator gameplay. Physical console tests remain separate.

The complete 63-battery suite passed again on the final native ROM SHA-256
`4530c718bf299ec9e1c8de8c52895906a81024345bd60717cd5c99dbd30b8a93`.
It verified player-object coordinates stayed synchronized after relocation,
and every landing allowed an ordinary step or its real reciprocal portal
without unintentionally starting combat. This caught and fixed the original
Continue behavior that retained the saved object position after updating only
`wXCoord`/`wYCoord`: the matched relocation now calls `RefreshPlayerCoords`.
The contact sheet `geography_native_continue_contact_sheet.png` contains nine
actual emulator frames of genuine old saves Continued on that exact final
ROM, enlarged without smoothing. Proposal drawings remain separately labelled
as source reconstructions; they are not used as final gameplay captures.
