# Readable native font for v0.2.5

The standard text now uses an original clean pixel drawing in
`gfx/font/peon_readable.png`: stronger six-pixel capitals, five-pixel lowercase
with clear ascenders/descenders, a slashed zero, distinct `I`, `l`, `1` and `i`,
larger punctuation dots, and a clean accented `é` for `Péon <name>`.
Lowercase sentences remain lowercase. This improves dialogue readability
without changing the size of a text box while it is open.

Every character remains one **8×8 tile**, using only black/white pixels and no
antialiasing. There are still 128 standard glyphs occupying exactly 1,024 ROM
bytes. The `Font` label, native loader, character codes, cursor arrows, symbols,
textbox borders and icon tiles retain their original contracts. Forty-two
unredrawn standard glyphs remain exactly identical to the original sheet.
Dialogues retain the existing eighteen-column wrapping and player-name limit.
Text speed and the existing input controls remain available through Options.
No variable-width font, text-engine rewrite or save-layout change is involved.

The drawing applies wherever the engine loads the standard font: new-character
selection/naming, dialogues, Character/Bags/Inventory, vendors, trainers and
battle labels. The title's embedded image lettering, map artwork and tiny
health-overlay digits are separate graphics and are intentionally not described
as converted standard-font glyphs.

## Implementation and references

- `tools/build_peon_readable_font.py` draws the source and transparent preview
  deterministically. It preserves `gfx/font/font.png` as the reference sheet.
- `gfx/font.asm` selects the new sheet through the existing `Font` label and
  asserts the unchanged 128-tile size.
- `tools/validate_peon_readable_font.py` verifies source dimensions, binary
  pixels, preserved glyphs and ambiguous-letter distinctions. Its native phase
  uses a private fresh game and ordinary buttons to enter `Péon ABCDE`, open
  Character/Bags/Inventory and speak to Gornek. It compares actual ROM font
  bytes, all 128 uploaded VRAM tiles and live CGB RGB555 text pixels.

The following primary sources were successfully read online on 12 October
2026 to confirm the fixed-tile implementation conventions; their glyph art
was not copied:

- [GBDK font interface](https://github.com/gbdk-2020/gbdk-2020/blob/develop/gbdk-lib/include/gbdk/font.h)
- [pret/pokecrystal font loader](https://github.com/pret/pokecrystal/blob/master/engine/gfx/load_font.asm)

This is original art inspired by readable native Game Boy interfaces; it is
not a claim that the font of any particular commercial game was reproduced.

## Generated files

All new evidence is in `references/generated/environment_v025/font/`:

- `peon_readable_glyphs_transparent.png`: transparent cream-ink glyph sheet.
- `peon_readable_sheet_native.png`: exact 128×64 monochrome source preview.
- `peon_readable_sheet_8x.png`: nearest-neighbour enlargement.
- `peon_font_comparison_native.png` and `peon_font_comparison_3x.png`: source
  drawings compared in equal fixed cells; these are not emulator screenshots.
- `font_build.json` and `font_source_validation.json`: deterministic source
  metadata and static checks.
- `baseline_v024/`: genuine ordinary-input screenshots and report from the
  previous ROM, when requested with `--baseline`.
- `native_validation/`: genuine current-ROM screenshots and SHA-256 report.

The final native result must pass against the exact packaged ROM hash. Prepared
PNG drawings alone are not evidence that the ROM is using the new font.
