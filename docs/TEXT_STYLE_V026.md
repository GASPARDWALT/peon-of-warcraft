# Native typography — v0.2.6

The normal 8×8 Crystal font now uses light single-stroke letters. Uppercase,
lowercase, digits and punctuation retain the original encoded character IDs
and fixed cell width. Person names use a separate one-pixel heavier weight;
class names, items, instructions and dialogue remain regular.

Names are styled while rendering, with zero-width `<BOLD>` / `<REGULAR>`
controls for literal NPC names and automatic styling of the existing player
and battle name records. No name bytes, save records or existing RAM addresses
change. The text linter treats the controls as zero-width.

Native frame geometry and wrapping are unchanged. Style attributes follow text
scrolling, clear with emptied cells and reach the hardware BG map during normal
printing. Per-cell publication uses Crystal's BG origin and guarded VRAM writes,
without adding a frame wait for every letter. Battle palette resets preserve
existing name/text bank bits; HP bars and borders keep their normal attributes.

The 23-glyph cache uses two disjoint VRAM regions:

| Context | VRAM bank 1 | Native signed BG tile IDs |
| --- | --- | --- |
| World, dialogue and world menus | `$9690–$97ff` | `$69–$7f` |
| Battle and menus opened during battle | `$8920–$8a8f` | `$92–$a8` |

The battle region follows the rank, totem and imp graphics ending at `$891f`
and stays below enemy animation backups at `$9000–$97ff`. The world region
follows the nine speaker-portrait tiles ending at `$968f`. Existing visible
names retain cache ownership across dialogue scrolling. An unexpected cache
overflow leaves existing cached glyphs intact and falls back to regular weight
for additional distinct glyphs, instead of repainting an earlier name.

The new transient state occupies the previously unused WRAM0 range
`$cfd8–$cff1`. It is not saved. All pre-existing RAM symbols are compared against
the frozen v0.2.5 symbols during validation.

Source assets and previews:

- `gfx/font/peon_regular_v026.png` and `.1bpp`
- `gfx/font/peon_bold_v026.png` and `.1bpp`
- `references/generated/visual_polish_v026/font/regular_and_name_weight_3x.png`
- `references/generated/visual_polish_v026/font/font_build.json`
- `references/generated/visual_polish_v026/font/validation.json`

The native validator checks the current ROM digest, exact uploaded glyph bytes,
actual BG attributes and RGB555 glyph pixels, normal character/class/bag/battle
screens, scrolls, menu returns, enemy poses and an actual private battery
restart. Any temporary boundary fixtures are separately labelled; no user's
battery files are opened. Captures use the new v0.2.6 directory. Previously
published v0.2.5 assets and evidence are not regenerated.

Text baked into title/atlas artwork retains the image's authored pixels. The
native font change applies to text rendered by Crystal's text and menu engine.
