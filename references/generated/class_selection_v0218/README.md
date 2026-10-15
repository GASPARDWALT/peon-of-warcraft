# Class master portraits v0.2.18

Static native conversion evidence, not emulator screenshots. The three complete 64x68 historical authored portraits under peon_sprite_redesign_v030/selection are read-only sources. Their character identities follow the supplied class-master references; these files are not user PNG extractions or recovered source grids. The historical build_selection.js generator is never run by this importer.

No scaling, smoothing, dithering, silhouette editing or anatomy drawing occurs. Four transparent rows pad the bottom to64x72. Each portrait uses72 row-major8x8 tiles (1152 bytes),72 palette IDs3..7, and five4-color RGB555 palettes (40 bytes). attrs.bin deliberately omits the VRAM-bank1 bit; the caller must OR$08. Each portrait/attrs/palettes group is in one ROMX section in graphics.asm. Labels use PeonMaster{Kento,Zogzog,Bismillah}PortraitV0218 with Attrs/Palettes suffixes.

BG index0 is opaque dark panel/ink RGB555(3,2,3), shared by every palette. It may represent source-opaque ink as well as background. Source alpha is preserved separately in hardware.png and source_padded.png; hardware_bg.png shows the actual opaque BG colors. Never infer a sprite transparency mask from these BG indices.

Palettes use only existing source material colors besides the fixed background. Fine gradients are reduced by the per-tile four-color limit. Face/eye, horn/tusk, fur/beard, armor and robe materials guide palette assignment; Kento's tiny red iris tiles keep a dedicated source-color palette. The import reports retain per-tile before/after color counts and weighted face-region error information.

hardware_bg.png is the1x review, hardware_6x.png is nearest-neighbor only, and comparison_6x.png shows source left/native right. Native1x and6x outputs were visually inspected; final engine rendering remains separate ROM validation.
