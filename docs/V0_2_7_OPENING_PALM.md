# Peon of Warcraft v0.2.7 — sleeping beside a palm

[ROM download](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/v0.2.7/peon_of_warcraft_v0_2_7.zip) · [Browser player](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/browser-player-v0.2.7/peon_of_warcraft_v0_2_7_player.zip)

The opening now shows the Peon sleeping beside a palm in the Valley of Trials.
Its English dialogue reads "sleeps by a palm tree." The existing palm metatile
is placed at block (4,3), immediately north of the sleeper. The hunter walks
from (5,8) through (6,8) to (7,8), delivers the BONK, and the scene proceeds
to Grommash Hold and class selection.

Extract the ROM ZIP and load `peon_of_warcraft_v0_2_7.gbc` in a GBC emulator.
For browser play, extract the reader ZIP, open its HTML in Chrome/Edge, and
click **Jouer**. Keep your battery save (`.sav`/`.ram`); the memory layout is
unchanged. For the browser version, export/import `.sav` to transfer from
v0.2.6, because full-session checkpoints are tied to their native ROM hash.

Actual screenshots and the opening GIF are in
`references/generated/opening_palm_v027/`. The normal-button intro check
passes for all three classes, including hunter positions, BONK, master
selection, naming, starter kit and arrival at The Den. All three browser
routes additionally pass the first quest/battle, native SAVE, cold Continue,
session restore, audio, keyboard and touch. The core checks MBC3/RTC/SRAM
and checksums. No physical Chromatic cartridge was tested.

ROM SHA-256: `4a1fa7ff7e744cd8ca656e57491f21ef32b3ea515c0af784b5878802446a9a8a`.

Build with `make pokecrystal.gbc -j4 RGBDS=/path/to/rgbds-1.0.4/`.
The historical v0.2.6 art pipeline enforces its frozen map baseline; this
one-byte map edit is compiled directly, using the existing native palm art.
Previous releases and their evidence remain byte-exact.
