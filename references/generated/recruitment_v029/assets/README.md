# Native recruitment and enemy artwork, v0.2.9

This is source artwork, not a claim that six new actors are already playable.
No species, item, move, sprite ID or saved field is assigned by the generator.
Root owns the future roster, eligibility, quests, stat tables and runtime
integration. The requested initial roster cap of two and later cap of three
therefore remain gameplay decisions outside this asset set.

Run `python3 tools/build_peon_recruit_assets_v029.py`. It reads native pixel
primitives from the v0.2.8 authoring tool without invoking its generator or
writing any v0.2.8 asset.

The six deliberately authored sets are:

- `earth_spirit`: floating earth/stone fragments and luminous green eyes.
- `demon_imp`: red skin, backwards-curved horns, long arms, clawed hands and tail.
- `orc_grunt`: close-cropped novice Orc, worn leather and a two-handed axe.
- `orc_warlock`: hostile novice Orc in a dark violet hood/robe, with a wand.
- `kolkar_archer`: humanoid upper body, horse barrel, four legs, longbow and arrow.
- `kolkar_melee`: the same centaur anatomy, with a polearm and a thrust pose.

Each set contains twelve 16×16 world frames, three 56×56 front frames and
three 48×48 rear frames. World tile ordering is row-major; battle pictures
are column-major per frame. `portrait_frames.bin` supplies a separate
row-major version of the 56×56 artwork. Rear centaur profiles face the enemy
at upper-right; their front attack profiles face the player. All four legs
remain in the authored native canvas.

Each set also provides deliberately drawn 8×8 and 16×16 heads for future
group indicators. These are small pixel faces, not resized battle images.
The three 16×16 recruitment items are `domination_skull`, `rally_horn` and
`elemental_relic`, each four row-major tiles with its own RGB555 palette.

`gfx/peon_recruits_v029/` contains indexed sources, raw tile binaries and
palettes. This directory contains no runtime code. Transparent native PNGs,
enlarged PNGs, contact sheets and APNGs are in the named asset subdirectories.
The GIF and paper review images are explicitly source previews on a paper
background. Frame transparency is binary alpha, and native palettes use at
most four indices; world objects use only indices1–3 as visible colors.

`asset_manifest.json` records sizes, tile order, palettes and binary hashes.
`static_validation.json` records source checks only. Actual native ROM
rendering, scanline limits, actor positioning, animations and palette
assignment still need validation after root integrates these files.
