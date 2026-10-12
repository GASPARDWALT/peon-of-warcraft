# Rounded Horde interiors — v0.2.8

The four shared Orc/Darkspear hut and inn interiors use a quiet, warm floor and
an octagonal hide/timber ring. The coarse corners fit Crystal's 32×32 metatile
grid. The inn has three corner bed plots, an accessible innkeeper, a table
and two fire-basin alcoves. One basin is fully visible in the northeast corner;
the other sits against the side wall. Huts also have two wall basins, and
Grommash Hold keeps its left banner and gains a basin on the right. The warm
basins use a bowl and flared tripod legs, with the existing animated flames.
The interior foot exit now shows a dark arch instead of an
unmarked road tile. The existing healer, inn binding and Hearthstone behavior
are retained.

The Horde crest is a hand-authored 16×16 open ring with a central diamond,
upper horns and two downward hooks. It appears on mounted cloth in metatile 6.
The repeated floor-carpet emblem is removed from huts, inns and Grommash Hold;
the carpet is plain red. Darkspear huts retain their wall talisman.

## Files and budget

- `tools/build_peon_environment_v028.py` builds the native tile sheet,
  palette attributes, metatiles and the four interior `.blk` arrays.
- `tools/peon_horde_emblem_v028.py` owns the exact 16×16 crest pixels.
- `tools/validate_peon_interiors_horde_v028.py` checks source geometry and
  runs the retained ordinary-input nine-door/room/save/menu/geography route
  against a specific compiled ROM hash.
- Reusable RGBA props and clearly labeled compiler map views are in
  `references/generated/polish_v028/environment/`.

The background allocation is still **192 native 8×8 patterns**, with the
animated flame patterns at slots 0 and 1. All plant silhouettes and actual
exterior doorway/cave patterns are protected during the small shade-variant
deduplication. Furniture has binary alpha; standalone cloth-banner and crest
PNGs omit the native wall backing so they can be reused directly.

The first **47 collision rows and block meanings are preserved**. Six block
IDs append to the tilemap data: 47–51 are solid room walls, and 52 reuses the
four `WARP_PANEL` collisions from the legacy interior threshold 16. Existing
map IDs, dimensions, exit `(5,7)`, warp events, object positions, innkeeper
interaction, bed/table events and all world block arrays remain unchanged.
Every previously walkable movement cell in all four rooms remains walkable,
including coordinates from earlier battery saves. No SRAM fields are added.

The source gate checks the old walkable-cell subset, native warp collisions,
NPC/bed/table approach reachability, marker-free floor art, three corner beds,
and the exact generated native inputs. Runtime proof requires the named ROM
hash, all nine building entrances/returns, four real cold room saves and 22
menu restoration cases. Compiler previews are not represented as game captures.

## References

- User-provided `references/zones/the_den/the_den_primary_reference.png`:
  dark entrance, reddish hide, ropes and pale tusk supports.
- User-provided
  `references/zones/Grommash_Hold/Grommash_Hold_Cataclysm_inside.webp`:
  warm hide/timber interior and wall-mounted red cloth.
- Official Orc tournament icon, fetched successfully from
  <https://wow.zamimg.com/images/wow/icons/large/inv_misc_tournaments_symbol_orc.jpg>.
  Used as a silhouette reference for original native pixel art, not as a ROM
  bitmap or palette source.
- Innkeeper Boorand Plainswind's original Barrens inn screenshot, linked by
  <https://www.wowhead.com/classic/npc=3934/innkeeper-boorand-plainswind>:
  <https://wow.zamimg.com/uploads/screenshots/normal/23677-innkeeper-boorand-plainswind.jpg>.
  Warm bowl fires on tripod supports provide the visual reference. The
  screenshot's player skeletons are not used as room decoration.
