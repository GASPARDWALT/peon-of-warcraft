# Larger, source-derived combat heroes — v0.2.16

The native loader contracts remain **48×48 / 36 tiles for rear pictures** and
**56×56 / 49 tiles for front and profile pictures**. Existing VRAM destinations,
palette slots, alpha conventions, save fields, enemy art and battle animations
are unchanged.

The Base and Shaman retain their archived native pixel designs. The Shaman
starts from the approved v0.2.14 head/body correction. A shared transform of the
complete body across all three poses fills the native picture envelope; the
head is never scaled independently. Original indexed colors stay unchanged.

Warrior and Warlock are imported again from their complete approved raster
crops, rather than enlarging an already reduced 48px picture. Native sampling
uses nearest only. Their skin, leather, purple robe, axe metal, hair and ink
are classified during RGB555 fitting so the renderer does not silently replace
green hands with purple. Source crease and edge contrast contributes to the
palette fit. Opaque palette entries are actual colors sampled from the source.
This is a lossy raster import, not exact native-grid recovery or newly drawn
detail. The two existing battle palettes still limit simultaneous shades.

The retired simultaneous Imp no longer occupies the Warlock's secondary
picture palette. Both existing hero palettes can retain source colors. Battle
mana/rage uses BG3, type text uses BG4, and regular text uses BG7; those palettes
are untouched. Profile-specific palettes retain their established separate
protocol.

| Idle picture | Visible area before | Visible area after |
| --- | --- | --- |
| Base, rear | 46×44 | 47×45 |
| Shaman, rear | 42×38 | 47×42 |
| Warrior, rear | 46×40 | 48×41 |
| Warlock, rear | 43×46 | 45×48 |
| Shaman, front | 54×44 | 56×46 |
| Warrior, front | 54×45 | 56×47 |
| Warlock, front | 54×54 | 56×56 |

Base/Shaman preserve three existing authored poses. The approved Warrior and
Warlock raster sheets contain one front and rear combat pose each; their three
engine slots repeat that pose, as before. No invented attack anatomy is added.

`manifest.json` records exact source paths, source SHA256 values, crop bounds,
alpha threshold, transforms, every pose's bounding box, visible pixel and skin
pixel counts, palette values, layout, and output hashes. Originals are not
modified. Reproduce with:

```sh
python3 tools/import_peon_combat_heroes_v0216.py
```

`pose_*.png` files decode the native packets with source alpha. The comparisons
under `references/generated/combat_heroes_v0216/` are static import evidence;
they are not emulator captures. The release must separately validate every
class and affected pose in the actual compiled ROM.
