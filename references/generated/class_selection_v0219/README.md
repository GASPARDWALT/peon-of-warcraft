# Illustrated class-master conversion v0.2.19

These are static import reviews, not captures from a running ROM.

Each approved full bust is fitted without clipping inside80×88 with nearest sampling only. This is explicitly lossy raster conversion, not native pixel-grid recovery. The isolated alpha silhouette is unchanged after the fit. No smoothing, dithering, drawing or silhouette repairs are performed.

Each role uses110 native8×8 BG tiles (1760 bytes),110 palette attributes3..7, and five4-color palettes (40 bytes). All palettes share opaque panel/ink RGB555(3,2,3). Source-opaque dark outline pixels may legitimately use BG index0; source alpha is retained separately in the review RGBA files. `hardware_bg.png` shows the actual opaque common panel color.

The per-tile conversion weighs faces, eyebrows, eyes, muzzle, tusks, fur and materials. Tauren fur and brown Orc skin keep separate warm shadows instead of collapsing all dark tones into a flat ink mask. Undead facial gray and violet eyes use their own material policy. Fine source shading is still reduced by the hardware palette limit.

For each role, `source_fit.png` is the full nearest raster before palette conversion, `hardware_bg.png` is the native1× review, `hardware_4x.png` is a nearest-only enlarged review, and `comparison_4x.png` places source fit left/native output right. `import_report.json` records source hashes, exact component crops, fit positions, palette colors, byte counts, packet round-trips, alpha agreement and face-region error metrics. Final ROM rendering must be verified separately.
