# Uniform exterior ground v0.2.20

This is the user's plain ochre option. Dense dirt behind transparent scenery and
the repeated V-shaped road grains are removed. One complete dark two-pixel grain
from the supplied dirt PNG remains per 32×32 floor block. Different route colors
and every original route border remain; there is no alternate dense patch.

Reproduce with `python3 tools/import_peon_uniform_ground_v0220.py`. This writes
only `gfx/quieter_ground_v0220/` and this review directory. The importer preserves
all 499 original PNGs, all original maps/scripts, regional palette files, prior
packets, collisions, approved buildings, source scenery and interiors. Native
packet readback and exact RGB comparisons run during each export. Unchanged
compressed packets are reused only when both their raw and compressed SHA256
match the last manifest.

The soil source is
`references/characters/peon_of_warcraft_environment_pack_v2_art_quality/durotar_valley/ground_durotar_dirt_01_32x32.png`.
The exact flat region is `(0,0,4,4)`; the complete grain is `(5,4),(6,4)`.
The color conversion keeps existing regional soil colors. Existing road pixels
provide their unchanged pale surface and edge colors; only their repeated three
grain indices are cleared, with the same supplied two-pixel grain used sparsely.

The source composition is recovered from the frozen v11/v13/v14 manifests and
native packets. Opaque source alpha is protected per pixel, including facades,
posts, cave and props. Recorded obsolete gateway markers and cleared thresholds
are accounted for before protecting current scenery. The exporter never erases
an opaque prop based on a color guess. Every input SHA256 and source placement is
recorded in `manifest.json`.

There are 13 native 216-pattern map packets. The largest uses 208 patterns.
Map block IDs, byte-exact collision rows and the reserved font gap are retained.
The old patch aliases remain valid but now render the same sparse floor texture.

Two small additional bindings are required by the engine integrator:

- `fire_frames_world.bin`: 192 bytes, exterior-only. All opaque native brazier
  pixels in all three source phases remain exact; only transparent dirt backing
  changes. The original shared interior file stays unchanged.
- `ground_bg3.bin`: 24 bytes, eight each for TheDen, RazorHill, OrgrimmarGate at
  offsets 0,8,16. BG3 is proved unused in every input metatile of those three
  maps, including inactive and scripted meanings. Its new colors preserve exact
  brown/ink/light prop RGB while matching the regional soil background.
  `ground_bg3.pal` records the same RGB555 values.

Rare scenery cells already need all four opaque native colors. A fifth exact
soil color cannot fit in that same 8×8 cell. Their opaque pixels stay exact and
their transparent ground uses the nearest existing palette tone. The manifest
measures these remaining tones. Water palettes in DurotarRoad and SenjinVillage
are unchanged.

`*_after_native.png` and `*_comparison_native.png` are rendered by decoding the
actual exported packets with the required regional BG3 profile. They are source
reviews, not screenshots from a running ROM. Runtime verification belongs to
the final integrated ROM and must check the exterior fire/palette selectors.
