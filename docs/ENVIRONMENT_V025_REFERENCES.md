# Durotar environment references for v0.2.5

Research and visual inspection completed on 2026-10-12. This document records
the references used for the environment redraw; it is not a claim that a
reference image, a proposed sheet or a compiler reconstruction runs in the ROM.
Native integration and emulator captures are recorded separately.

## Reference priority

1. The user's annotated Valley map in the conversation defines the intended
   geography: red mountains block travel, off-white walls frame the eastern
   exit, and the seven green rectangles describe the requested views.
2. The repository's actual WoW screenshots define the building and vegetation
   silhouettes. The Den and Sen'jin should retain different architectural
   identities.
3. Existing pixel-art references define how to simplify those silhouettes for
   the native screen, without adding detail that obscures doors or paths.
4. Online Warcraft II Horde building sheets provide a secondary reference for
   readable bone supports, timber structures, banners and entrances. Their
   bright green ground is not a reference for Durotar terrain.

The annotated user image remains a conversation attachment. It is not present
as a repository source file, and none of the unannotated maps below is a
replacement for that attachment. See [the layout contract](VALLEY_SCREEN_LAYOUT.md).

## Actual repository images inspected

| File | Observed detail and intended use |
| --- | --- |
| `references/zones/the_den/the_den_primary_reference.png` | Red hide roof, thick curved ivory bone supports, dark arched entry, sandstone base and broad clear approach. Primary Orc building reference. |
| `references/zones/the_den/Capture d'écran 2026-10-07 142802.png` | The Den's western pocket, circular rise and eastbound beaten track. Use for regional geography, not a building elevation. |
| `references/zones/valley_of_trials/valley_of_trials_inspiration_01.png` | Enclosed Valley, western Den, northern Burning Blade entrance and narrow fortified eastern exit. |
| `references/zones/valley_of_trials/valley_of_trials_inspiration_02.png` | The same unannotated Valley artwork as inspiration 01; it supplies no separate path drawing. |
| `references/zones/valley_of_trials/first_zone_layout_inspiration.png` | Terracotta ground, pale irregular trail, wide sparse acacia canopy, leaning pale trunk, sandstone stacks and isolated cacti. |
| `references/zones/valley_of_trials/valley_of_trials_inspiration_03.png` | Layered cliff faces, angular boulders, branching dead trees, two-armed segmented cacti and scattered bones. Pixel simplification reference. |
| `references/zones/senjin_village/images.jpg` | Conical ochre thatch, bowed rib supports, textile walls, dark stepped entrance, tall pennants and palms. |
| `references/zones/senjin_village/286SBVI9U95R1467053321379.jpg` | Open Troll village: timber entrance stairs, thatched hide roofs, red banners and sparse palms framing an unobstructed central road. |
| `references/zones/senjin_village/yvt8ladwa0m21.jpg` | Coastal position of Sen'jin and the route arriving from inland Durotar. This supplied map has visible colour bands; those bands are not terrain palette instructions. |
| `references/zones/Razor hill/Capture d'écran 2026-10-07 142559.png` | Razor Hill's crossing and surrounding canyon geography. Too small to infer individual door or wall details. |
| `references/generated/warcraft_audio_update/trees/durotar_trees_contact_sheet.png` | Earlier original deadthorn, crooked-acacia and coastal-palm proposals. These are prepared art, not screenshots of those three trees running in the game. |

The existing `docs/DUROTAR_TREE_REFERENCES.md` explains the native transparency
and palette constraints for those earlier proposals. Only runtime evidence for
the current candidate establishes which redraws have actually been integrated.

### A misleading cave reference

`references/zones/Valley_of_trial_CAVE/images.jpg` was inspected and its title
clearly reads **SKULL ROCK**. Skull Rock is not Burning Blade Cavern. Do not
copy its branching layout or claim it is the requested northern Valley cave.
It can illustrate a generic cavern-map silhouette; the playable cave keeps
its own authored connections until the correct layout is supplied or verified.

## Online references actually retrieved and inspected

Repository: [zanybaka/aicup](https://github.com/zanybaka/aicup), inspected
revision `a57d84f7fd4b3311b4f8b506a654535201054fb9`.
These images were fetched through the inherited cloud proxy with HTTP 200,
then opened with the image viewer. Original downloads remain in `/tmp` for
inspection and are not included in project artwork, assets archives or ROMs.
The source manifest records their exact URLs, dimensions and SHA-256 hashes.

| Online sheet | Detail useful for an original redraw |
| --- | --- |
| [Great hall](https://raw.githubusercontent.com/zanybaka/aicup/master/resources/WarCraft%202%20Sprites/tilesets/summer/orc/buildings/great_hall.png) | Broad rounded entrance, curved external ribs, red side banners and a clear stepped threshold. |
| [Barracks](https://raw.githubusercontent.com/zanybaka/aicup/master/resources/WarCraft%202%20Sprites/tilesets/summer/orc/buildings/barracks.png) | Red hide canopy, crossed bone spikes and an unmistakable dark front opening. |
| [Watch tower](https://raw.githubusercontent.com/zanybaka/aicup/master/resources/WarCraft%202%20Sprites/tilesets/summer/orc/buildings/watch_tower.png) | Four narrow wooden supports, open observation deck, tiny pennant and front ladder. |
| [Troll lumber mill](https://raw.githubusercontent.com/zanybaka/aicup/master/resources/WarCraft%202%20Sprites/tilesets/summer/orc/buildings/troll_lumber_mill.png) | Layered dark timber roof, red trim and readable corner posts. Secondary timber-structure reference, not a substitute for the local Sen'jin screenshots. |
| [Small fire](https://raw.githubusercontent.com/zanybaka/aicup/master/resources/WarCraft%202%20Sprites/missiles/small_fire.png) | Compact yellow hotspot, orange body, dark-red outer tongues and restrained changes between poses. |

The sheets depict Warcraft II rather than WoW Classic. Use their silhouette
economy; retain the Classic Durotar geography and buildings shown by the user's
references. No third-party sprite sheet is imported or traced into native assets.

GitHub repository searches for `warcraft sprites`, `warcraft horde`,
`wow classic assets`, `warcraft 2 browser`, `durotar`,
`warcraft2 javascript`, `warcraft buildings` and `orgrimmar` were accessible.
Search results alone are not evidence that a repository contains a usable
Classic building screenshot. Several results were unrelated frameworks,
add-ons or server code. Only the retrieved images above supplied online visual
evidence. The Warcraft II map-editor repository and Wargus README were found,
but neither was used as an additional building-art reference.

### Sites unavailable during this research

The root agent attempted the Valley of Trials page on `www.wowhead.com` and
the Orc architecture page on `warcraft.wiki.gg`. Both failed with a proxy
`403 Forbidden` while establishing the HTTPS tunnel. Their pages and images
were not inspected. A cloud network configuration draft is separate from
effective access and does not make either site available by itself.
No direct-network bypass or fetch-through relay was used.

## Drawing and placement rules

- **Orc buildings:** red ochre hide, ivory tusks, dark timber binding and a
  low sandstone base. The opening is the darkest broad shape. A pale threshold
  connects directly to the beaten road; decorative posts cannot conceal it.
- **Troll buildings:** ochre thatch and timber with curved rib braces, sparse
  woven patterns and a small stair. Palms and lighter coastal sand distinguish
  Sen'jin from the inland Orc settlement.
- **Doors and exits:** buildings have a visible opening and threshold; cave
  openings have irregular rock arches; the eastern Valley exit has paired
  off-white fortification edges. Keep these silhouettes distinct.
- **Cliffs and rocks:** use broad top planes with a top-left highlight and
  darker tiered faces. Impassable mountains form continuous boundaries. Small
  rocks may guide a passage but cannot create a hidden collision in a road.
- **Trees:** sparse flat-canopy acacia or crooked deadthorn inland; palms at
  the coast. Keep trunks off warp tiles, quest actors, pickups and required
  lanes. Avoid a continuous inland green forest.
- **Cacti:** compact green ribbed forms, readable arms and a small base shadow.
  A quest cactus remains distinguishable from scenery and its harvested state
  must become visibly empty ground while retaining the saved harvest flag.
- **Fire:** a compact yellow core, orange body and dark-red tips above a
  clearly readable stone ring or brazier. Frame changes must not change the
  obstacle footprint or spend NPC object slots.
- **Small decoration:** crate, barrel, sack, bone fragments, ore and banners
  share the same light direction and chunky one-pixel outlines. Keep secondary
  texture quieter than actors, quest markers and entrances.
- **Paths:** pale beaten earth with irregular shoulders and darker surrounding
  soil. Every existing mandatory route should remain continuous and easy to
  follow; add visual rock framing rather than an untested alternate shortcut.

The seven requested views retain these landmarks: zone 1 Den/vendor/class
camp, zone 2 eastbound crossing, zone 3 central Valley, zone 4 Hana'zua,
zone 5 Sarkoth, zone 6 Burning Blade entrance and separate cave interior,
zone 7 fortified eastern exit. The exact additional path drawing remains
missing. Do not present a newly invented seven-map camera migration as an
exact reproduction of that missing drawing.

## Native review checks

Review original transparent PNGs at native size before their enlargements.
Keep alpha binary, avoid antialiasing, and measure the compiled 8×8-tile budget
after palette reduction. Background transparency must be baked into the region
ground; a preview with transparent margins is not proof of native support.

After integration, inspect actual ROM captures at the Den thresholds, the cave
arch, the eastern exit and the Troll doors. Walk in and back out, load another
region and return, then cold-restart a battery save. Check that the previous
region's tiles, fire frames and harvested cactus appearances do not survive
into the wrong map. A static asset sheet cannot verify these transitions.
