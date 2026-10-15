# Welcome-scene raster import v0.2.18

`*_composite_source.png` shows the whole supplied/generated figure over the same unmodified nearest-sampled Durotar background. `*_figure_fit_rgba.png` preserves the binary foreground silhouette separately.

`*_hardware.png`, `*_hardware_4x.png`, and `four_states_contact_2x.png` decode the actual emitted 2bpp packets, tilemap, attributes and five shared GBC palettes. The flat areas are underneath the engine’s guaranteed opaque identity bar, right-hand menu and footer. They are deliberately normalized to avoid spending VRAM on permanently hidden pixels. These are import reviews, not screenshots from a running ROM.

All figures have their feet at native y124, within x18..81. Sources are copied byte-for-byte into `assets/selection_v0218/`. This is explicitly lossy raster conversion with nearest sampling; no native source pixel grid is claimed. No silhouette or equipment was drawn or repaired during the import. The class source has exactly three connected alpha figures; their measured equipment overhang is preserved rather than cut at the nominal equal-third panel boundaries.

`import_report.json` records exact source hashes, crops, fits, palettes, reserved VRAM ranges, native tile counts and binary pixel round-trips. It also proves identical background pixels outside the union of figures and declared opaque UI regions on all four states.
