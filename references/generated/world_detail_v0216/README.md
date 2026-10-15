# World actor detail import v0.2.16

These files are static native-packet decodes and source-crop comparisons. They
are not screenshots and do not establish in-game rendering or playability.

The four heroes are imported directly at 24×24 from the four dedicated WORLD
views in the approved raster sheets under
`references/generated/peon_sprite_redesign_v030/originals/`. The world crop
coordinates and source hashes are recorded in `import_report.json`. Combat
views are never used. This is a lossy nearest-sampled raster import, not recovery
of a native pixel grid, new illustration, or newly drawn anatomy. Alpha is
thresholded at 128, as in the approved prior import; no smoothing is applied.

Base Peon and Shaman reuse those exact four silhouettes with a one-pixel upward
full-body bob at gait address 1. Addresses 0 and 2 share the still. Warrior and
Warlock repeat their four provided stills for the three existing gait addresses,
as in v0.2.15. These are not three separately illustrated walking poses.

Supplied NPC WORLD PNGs are only 16×16. They retain their exact complete supplied
silhouette and the previously documented whole-body fallbacks for damaged crops.
The conversion preserves their original darkest outline and deep source shadow,
then fits skin, leather, cloth, and equipment to existing hardware palettes.
Dim source material is no longer automatically mapped to black because an
existing Game Boy Color palette is brighter. There is no claim of invented finer
NPC anatomy. Crawler, Kolkar, sleeper, and unbound roster packets keep their
existing v0.2.15 native bytes when no new source detail is available.

Every actor retains 12 streamed frames of 144 bytes, 24 mask bytes, and 108
palette-attribute bytes. Established exported symbols and binding records are
unchanged. The native 16px movement/collision grid, battle art, buildings, maps,
palettes, OAM admission, and save format are unchanged by this importer.

`static_validation.json` records exact packet/PNG/mask decoding for all 468
frames and unchanged hashes for the 495 canonical character PNGs plus the four
approved source rasters. `hero_world_comparison.png` and each role's
`comparison.png` show dedicated WORLD source / v0.2.15 / v0.2.16. The
`world_<direction>_<pose>_24x24.png` files are transparent native exports.
