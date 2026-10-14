# v0.2.13 — native artwork and party repair

This change restores the archived complete Peon/Shaman, Boar and red Imp
models requested by the user. It keeps the current Warrior and Warlock raster
imports, the approved building facades and the readable interior layouts.
Historical art generators are never run during this build.

## Artwork sources and native dimensions

- Archived native actors: `gfx/peon_classes/shaman/`,
  `gfx/pokemon/rattata/`, `gfx/pokemon/geodude/`. Versioned imported packets:
  `gfx/native_actor_restore_v0213/`.
- Active outdoor decor: whole supplied PNGs under
  `references/characters/peon_of_warcraft_environment_pack_v2_art_quality/`.
  The canonical composition and post overlays are stored separately in
  `gfx/canonical_decor_v0213/` and `gfx/zone_passages_v0213/`.
- Passage pillars: complete 8×32 source regions from the approved
  `references/characters/razor_hill_inn_gbc/razor_hill_inn_interior_192x160.png`.
  The cave retains the supplied full 64×64 Durotar entrance.
- Large masters: complete Tauren/Orc/Undead bodies from
  `references/characters/class_masters/class_masters_crystal_style_sheet_reference.png`.
  Nearest sampling to 24×24 is a documented raster conversion, not recovery
  of a native pixel grid. The split Warrior front is excluded because its
  supplied image contains only an axe.
- Rock stages use complete supplied small-rock 16×16, copper-vein 32×32 and
  large-rock 32×32 PNGs at original scale inside front 56×56/rear 48×48
  canvases. They vibrate through whole-image one-pixel translations. World
  icons use nearest sampling where the 32px source must fit 16px. The same
  organic source serves both battle views; no anatomy is invented.
- Lightning rotates the individual supplied player/enemy/impact PNGs at
  90 degrees, preserving every source pixel and binary alpha. Projectiles
  use 32×16 canvases and travel horizontally between the native battlers.

Each import has a source hash, transformation manifest and native decoded
preview under `references/generated/`. Original sources are preserved.

## Gameplay and interface

- Native single-active-member party combat; START opens ROSTER. Companions
  retain native four move slots, PP, learning, switching and naming.
- Petit cailloux vibrant evolves at level 8 into Veine Tellurique, then at
  level 12 into Roche Elementaire. Native record names remain within ten
  glyphs; full stage names appear in the member information card.
- Native ball throw, shrinking, bounce, suspenseful wobbles, breakout and
  success cue for the reusable control stone. Capture probability and
  native RNG consumption remain unchanged.
- Passive simultaneous pet attacks and battle totems are retired. The old
  passive-pet clearing hook is inert, preserving the new resource panel.
- Real mana/rage gauges appear in the world HUD and in combat. Selected
  attack type labels use localized colored native-font glyphs. Native HP,
  EXP, actor palettes and the normal font remain separate.
- Sleeping quest worker moves to Valley of Trials. The three class masters
  occupy The Den's western training building. The hearthstone inn is kept.
  The shared Razor Hill hut retains its original attendant.
- Warlock master is named **Bismillah LesTenèbres**. The native font gains
  a grave-accent glyph; its unreadable bold `m` uses the existing regular
  `m` silhouette. Every other glyph remains byte-identical.
- Cold Continue rebuilds the map's sprite allocation before restoring its
  objects. This prevents the large class masters from displaying pieces of
  the player after loading a save. Native party records and events are kept.

## Allocation and compatibility

The selected thirteen outdoor maps support 216 patterns. The extra 24 use
GBC VRAM bank1 `$8E00..$8F7F`; logical `$E0..$F7` remain signed tile IDs.
Emotes begin at `$8F80`; text/portrait caches at `$9600` remain separate.
Razor Hill requires 206 actual patterns. Other maps retain the 192-pattern
path. No new persistent save fields are added.

Three 24×24 masters use 27 native OAM entries. Their room omits the walking
Imp follower while preserving its party record; it returns outside. The
world HUD uses six entries, leaving room for the hero within the 40-object
limit. Placement and actual LCD tests also check the ten-object scanline
limit. World HP, mana and both hero palette families remain protected.

Build: `python3 tools/build_peon_v0213.py` with RGBDS 1.0.4. The ROM is a
2 MiB CGB-only MBC3+RTC cartridge with 32 KiB battery RAM. Physical Chromatic
hardware is not available in this session; native emulator evidence and
header/checksum validation are recorded separately.

## Validation and next map step

Final compiled-ROM reports and screenshots are listed in
`references/generated/v0213/validation.json`. Evolution tests additionally
use a separately compiled, explicitly guarded fixture to reach levels 8
and 12 through real battles; the released ROM contains no fixture.

The imported biome supplies existing outdoor anchors. New jungle-tree
placements and other unplaced pack categories remain future work, rather
than being replaced by schematic artwork. Building The Den further should
reuse these canonical blocks, preserve the paired trigger lines and clear
arrival lanes, and audit each new object's palette, collision and pattern
cost before adding it.
