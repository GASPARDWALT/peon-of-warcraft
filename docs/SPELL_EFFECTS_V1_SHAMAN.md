# Spell effects v1 — native Shaman import

This change imports the four Phase 1 effects directly from the supplied pack.
It keeps existing move/item IDs, learning progression, party records and saved
data layouts. No character, creature or environment artwork was redrawn.

## Canonical addition and source files

`Add_spell_effects_pack_v1` is commit
`270a9ef45a38ab8e761da25224121cd3af0032f7`, adding:

`references/characters/peon_of_warcraft_spell_effects_pack_v1.zip`

ZIP SHA256:
`924f64d56c2ddb6497dc24db4bc110908ac074d7de197c4a071a759ffe0a8ae0`.

The archive is extracted into
`references/characters/peon_of_warcraft_spell_effects_pack_v1/`.
All 103 extracted files match their original ZIP bytes, including the BOM/CRLF
CSV. The canonical `manifest.csv`, `manifest.json` and
`docs/CODEX_IMPORT_AND_IMPLEMENT_SPELL_EFFECTS.md` were read before integration.
There are 99 PNGs: 59 individual assets, 18 reference sheets, 21 source-atlas
images and one preview. Only the following 13 individual Phase 1 PNGs are used
by the native converter:

| Ability | Exact files relative to the extracted pack |
| --- | --- |
| Lightning Bolt | `icons/lightning_bolt_icon_16x16.png`; `player_back/lightning_bolt_player_back_16x32.png`; `enemy_front/lightning_bolt_enemy_front_16x32.png`; `impacts/lightning_bolt_explosion_32x32.png` |
| Rockbiter | `icons/rockbiter_icon_16x16.png`; `player_back/rockbiter_player_back_32x32.png`; `enemy_front/rockbiter_enemy_front_32x32.png` |
| Earth Shock | `icons/earth_shock_icon_16x16.png`; `player_back/earth_shock_player_back_32x32.png`; `enemy_front/earth_shock_enemy_front_32x32.png` |
| Earth Totem | `icons/earth_totem_icon_16x16.png`; `player_back/earth_totem_player_back_32x32.png`; `enemy_front/earth_totem_enemy_front_32x32.png` |

## Import and native animation

`tools/import_peon_spell_pack_v1.py` reads the individual PNGs, keeps every
source coordinate and alpha bit, splits each canvas into 8×8 tiles and safely
deduplicates indexed tile patterns. It verifies `rgbgfx --colors dmg` output
against the selected indices, then compresses with native
`tools/lzcompress --matching --align 4` and checks decompression round trips.
Derived files are isolated in `gfx/peon_spell_pack_v1/`.

The originals contain more colors than hardware allows in an 8×8 OBJ tile.
Three palettes per ability, each containing three source-derived opaque RGB555
colors plus transparent index 0, occupy OBJ slots 4–6. Color fitting is recorded
per source tile; dimensions, silhouettes and alpha are exact. There is no
smoothing, interpolation, dithering or texture redraw.

| Ability | Actual native binding | Packet tiles | LZ bytes | OBJ rows per source frame |
| --- | --- | ---: | ---: | --- |
| Lightning Bolt | `THUNDERSHOCK` ($54 / 84) | 15 | 224 | player 4; enemy 4; impact 7 |
| Rockbiter | `SWORDS_DANCE` ($0e / 14) | 28 | 224 | player 14; enemy 14 |
| Earth Shock | `THUNDERPUNCH` ($09 / 9) | 28 | 240 | player 14; enemy 14 |
| Earth Totem | `PEON_EARTH_TOTEM` (`ITEM_94`, $94 / 148), plus a visual-only animation token | 26 | 192 | player 13; enemy 13 |

All source directions are compiled and selected explicitly with `hBattleTurn`.
Lightning's enemy file differs from a simple mirror. The other three supplied
enemy files happen to be mirrors, but are still imported and hashed separately.

Each individual source contains one static image. Native objects animate its
position: Lightning travels diagonally to its target and plays the supplied
impact; Rockbiter rises on its caster; Earth Shock briefly shakes at its target;
Totem rises into place. No additional drawn source frames are claimed.

The new renderer is selected only by a logical palette-bit sentinel. It uses
each imported tile's OBJ palette while preserving all legacy OAM flag behavior.
Its row bodies, graphics, palettes and renderer share a floating ROM bank;
small registries stay in the fixed animation banks. Only `wOBPals2` is changed,
so native `wOBPals1` defaults remain available for subsequent effects.

The placed Totem uses the full 32×32 player source: 16 row-major tiles at VRAM
bank 1 `$8ad0..$8bcf`, and 13 sparse OBJ entries in slots 24–36. It draws behind
opaque background pixels, preserving portraits, text, bold glyphs and the party
sidebar. Normal animation and level feedback wrappers release this layer before
other effects, then restore it. Placement occurs after Bags has restored the
battle screen and consumes the existing ordinary item turn; the item is reusable.

The imported 16×16 Totem icon is displayed through the existing Bags icon
loader. The other three icons are converted and retained, but no move-icon UI
was added in this phase.

## Corrections made during integration

- Native `FinishBattleAnim` previously reset OBJ palettes after Totem redraw.
  The redraw now follows the palette reset, without growing the fixed bank.
- Both native stat-reset loops filled eight bytes even though seven are actual
  stat stages. The eighth bytes now contain transient Peon state, which caused
  Rockbiter and Lightning Shield to start at 7. The loops now fill exactly the
  seven stages; their native initializer leaves these charges at zero.
- The enemy Totem placement was raised by eight pixels so its complete initial
  rising canvas stays above the player-name row. Every native test frame now
  asserts this boundary; the player and persistent positions are unchanged.

No RAM/SRAM bytes, species IDs, party structures or saved-event IDs were added.
The older Haze, Psych Up and Transform bulk-stat commands remain outside this
four-effect validation; audit their use of the eighth padding byte before
expanding those abilities around the Peon transient states.

## Builds and reproducibility

Use RGBDS 1.0.4 (`PEON_RGBDS` can select another installation directory):

```sh
python3 tools/build_peon_spell_pack_v1.py
python3 tools/build_peon_spell_pack_v1.py --fixture --no-import
```

The builder freezes all 207 historical generator outputs and rejects a Make
plan that would redraw old art. Normal and test objects have separate suffixes.
Both ROMs are 2 MiB, CGB-only, with valid checksums and MBC3+RTC+32 KiB
RAM+battery declarations. This is header and emulator evidence; physical
ModRetro programming, RTC clock behavior and battery persistence were not tested.

The normal game starts through its unchanged opening and class selection.
The isolated test target, `pokecrystal_spell_test.gbc`, enables
`PEON_SPELL_TEST` and `PEON_ENVIRONMENT_TEST`, starts a native level-8 Shaman
on the existing environment inspection map, and exposes eight scenarios through
its guide. From spawn (12,17), step left once and press A toward the guide.

Cases 1–4 use ordinary Fight moves/Bags. Cases 5–7 trigger the corresponding
enemy move through an ordinary battle action. Case 8 previews the enemy Totem
direction inside a real native battle; this prototype has no enemy Bags/item
turn, so it creates no enemy field entity. Enemy Rockbiter retains native
Swords Dance attack stages; the player uses the existing charge-next-strike
mechanic. Enemy actions do not consume the player's mana.

The test foe is the existing mapped level-10 Orc Guard (`MACHAMP`), with native
HP 200 and no progression rewards. Only case 4 lowers both native enemy Attack
copies to 1 so the placement, subsequent casts and menu-return checks are
survivable. These constructor changes are absent from the normal ROM.

## Test evidence and limits

Final builds and tests passed:

- Normal ROM SHA256:
  `c6d1a104335541fae9a5de09da8965263ef1cd08f2bf4fe3913f112b9ff744ac`.
- Eight-scenario test ROM SHA256:
  `1221b9c6f4194444ced6a00573d2a5d837314ee070ab0ddf553bbbd149cf885f`.
- All eight native scenarios pass. Player mana costs are 15/25/30 for
  Lightning/Rockbiter/Earth Shock; the Totem retains its existing zero-mana
  item behavior. Rockbiter starts at zero, becomes one and is consumed by a
  genuine next physical strike. The enemy uses native +2 Attack stages.
- The full persistent source packet has 313 opaque pixels, of which 306 remain
  visibly exact behind normal foreground graphics. All 16 tiles and 13 OBJ
  rows remain intact after placement, Lightning, a stock strike and Bags return.
- Maximum observed hardware use is 16 OBJ entries and 7 on a scanline,
  including entries whose X coordinates hide them.
- The normal ROM passes the existing three-class source-art observer for
  native opening, all four world directions/three walking poses, a genuine
  basic attack and all three imported rear combat poses.
- A tracked-files-only rebuild yields byte-identical normal and test ROMs.
  Native Make also regenerates all ten new bitplane files byte-identically
  from the importer's indexed PNGs. All 3,279 previous tracked graphics files
  remain unchanged.

Delivered ROMs, symbol/map files and ZIP:
`releases/spell-effects-v1-shaman/`.

Reproduce the bounded emulator checks with PyBoy 2.7 and NumPy/Pillow:

```sh
python3 tools/validate_peon_spell_pack_v1.py \
  --rom pokecrystal_spell_test.gbc --sym pokecrystal_spell_test.sym \
  --expected-sha 1221b9c6f4194444ced6a00573d2a5d837314ee070ab0ddf553bbbd149cf885f
python3 tools/validate_peon_spell_pack_v1_compatibility.py \
  --rom pokecrystal.gbc --sym pokecrystal.sym \
  --expected-sha c6d1a104335541fae9a5de09da8965263ef1cd08f2bf4fe3913f112b9ff744ac
```

Build reports, source hashes, color conversion records and actual runtime
captures are in `references/generated/spell_tests/`. `staticpreviews/` contains
source/conversion comparisons, not emulator proof. `runtime/` contains native
combat captures and its validation report; `compatibility/` records the normal
game's three classes, all world facings and rear combat poses.

The sparring observer uses normal buttons, isolated ROM copies and read-only
VRAM/OAM/palette observation. It does not inject RAM, call CPU routines,
restore emulator states or open user batteries. Native tests cover both source
directions, imported tile bytes, per-tile palettes, alpha-mask LCD pixels,
movement, damage, mana, player Rockbiter charge/consumption, enemy attack stages,
and Totem restoration after casts, a stock strike and Bags return. The no-EXP
fixture cannot reach a level-up glow, whose wrapper was reviewed statically.

The native effect packet budget is 79 tiles; the largest new packet uses 28.
One effect source uses at most 14 hardware OBJ entries and four per tile row.
The registry now contains 200 objects, 200 framesets, 249 OAM sets out of 252
available codes, and 47 graphics groups. The fixed Move Animations bank retains
171 bytes; normal Battle Core retains 9 bytes and the isolated test Core is full.
Future effects need registry/bank planning before appending more OAM sets.

Phase 2 and Phase 3 assets remain intact in the canonical pack; their 14 new
native imports are not part of this Phase 1 delivery. Next implement the six
Warlock/demon effects with the same source-preserving converter and directional
tests, after making room in the animation registries.

The exact created/modified file list is
`references/generated/spell_tests/changed_files.txt`.
