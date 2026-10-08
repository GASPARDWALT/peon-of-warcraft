# Actual ROM rear-pose captures

`validation.json` records the exact tested ROM hash and native pixel checks.
The normal route uses a fresh new game, buys the merchant's potion, accepts
Gornek's quest, uses the reusable Earth Totem and potion, and chooses Mace
Strike and Lightning Bolt through the real battle menus. That route edits no
RAM and loads no emulator states.

Separate diagnostic cases rewind the isolated encounter and set enemy
species/HP, the test spell/PP list, an active totem and the existing battle
scenes option. These are explicitly listed in the report; they do not claim
to test the Yarrog quest or the complete trainer progression.

The rear picture contains 36 column-major tiles at VRAM bank0
`$9310..$954f`. Mace shows brace → swing → idle; Nature casts, Healing Wave,
Rockbiter and Lightning Shield show brace → idle. With battle scenes off,
only idle is shown and the temporary pose flag remains cleared. Native RGB555
pixels are compared to the original three frame binaries, including the
unchanged battle palette.

Immediate helper-return checks protect enemy fronts, fonts, gold-rank tiles,
totem tiles, and the VRAM/WRAM bank selectors. Enemy animation tails may be
initialized by the first actual enemy attack; that legitimate cache fill is
compared to its compiled enemy artwork. Both ordinary bag-item returns and
diagnostic bag round trips must restore the native idle picture.

Files ending in `_actual_rom.gif` contain real 160×144 game frames enlarged
2× with nearest-neighbor scaling. GIF delays average 60 frames per second
using 20/20/10 ms timing, accounting for GIF's 10 ms timing units. Files ending
in `_actual_native_transparent.png` are 48×48 crops of real, pixel-verified
frames, with palette index0 replaced by binary transparency. They are not
concept illustrations or separately rendered approximations.
