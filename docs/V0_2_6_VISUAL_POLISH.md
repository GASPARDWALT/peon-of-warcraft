# Peon of Warcraft v0.2.6 — visual fixes

[Download the ROM](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/v0.2.6/peon_of_warcraft_v0_2_6.zip) · [Transparent art, native captures and offline gallery](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/v0.2.6/peon_of_warcraft_v0_2_6_assets.zip) · [Standalone browser player](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/browser-player-v0.2.6/peon_of_warcraft_v0_2_6_player.zip)

Extract the ROM ZIP and load `peon_of_warcraft_v0_2_6.gbc` in a GBC emulator.
For the browser player, extract its ZIP, open
`peon_of_warcraft_v0_2_6_player.html` in Chrome or Edge, then click **Jouer**.
For the images, extract the assets ZIP and open `index.html`.

## What changed

- Light fixed-cell dialogue and menu text; player, enemy and mentor names
  have a separate heavier face. Fixed partially typed names, scrolling
  attributes, and name tiles corrupted by enemy animations or spell cleanup.
- Warrior and Warlock now have their own humble Orc apprentice art:
  12 world direction/step frames and three battle back poses per class.
  Shaman world/rear art is preserved. Class previews show the selected class
  immediately; Continue shows the verified saved name once.
- The friendly imp is smaller in the world. The battle imp and Earth Totem
  are 16×24, with separate tile allocations. Firebolt launches from the imp's
  hand; the animated purple Shadow Bolt starts beside the Warlock's staff.
  Fixed the palette guard's WRAM-bank error and restored palettes after casts.
- Dark door openings, flat thresholds, visible trails and the right-hand cave
  opening align with actual movement/warp cells. Closed architecture remains
  visibly closed. Horde banners and rugs share a clearer emblem.
- Kept the existing seven-zone geography, map IDs, collisions, NPC events,
  rewards, prices, damage, potion rarity and spell charges.

Character's front panel currently displays one frame. Extra transparent front
frames are supplied as art; the panel does not animate them. Baked title and
atlas lettering keeps its authored pixels. This milestone fixes observed
visual faults; it does not establish that every possible game state is bug-free.

## Save transfer

Use the emulator's **battery save** (`.sav`/`.ram`, 32 KiB), not an emulator
save state. Keep a backup. If loading the ROM as a file, give the battery the
same base name as the new ROM in the location your emulator expects.
In the browser reader use **Importer .sav**, then choose **Continue**.

All pre-existing WRAM/SRAM symbol addresses and saved item, move, species,
event and map identifiers are retained. Three genuine v0.2.5 characters
(Shaman, Warrior, Warlock), saved at The Den after their first quest, have
passed migration and a subsequent native save/cold Continue. Their names,
party records, charges, inventory, money, coordinates and event flags survive;
the class graphics and companion reconstruct from the existing flags.
Other old saved locations were not exercised by this migration suite.

Browser full-session checkpoints are tied to their ROM hash. To move from
the v0.2.5 reader to v0.2.6, export the old game's `.sav` and import that
battery into the new reader. An old full-session JSON is not a version upgrade.

## Verification

Delivered ROM SHA-256:

```text
fe80c80dee9ef2926c906e2ac18d36a2ce16dc1bd92291cf1dd54ebe58c523f5
```

The release script requires five passing reports for this exact binary:
class graphics, typography, companions/spells, doors/paths and old-save
migration. The evidence directory is
`references/generated/visual_polish_v026/`; ordinary gameplay and temporary
diagnostic fixtures are labelled separately. The release gallery excludes
preliminary and failed runs.

Ordinary checks cover all three class routes, 36 world poses, five casts,
six class previews, three battery restarts, nine doors, nine reciprocal
zone/cave links, four interior cold restarts, 44 menu opens, 512 fire frames,
harvested cacti, the earned seven-sector atlas and mailbox returns.
Typography adds 51 rendered-pixel checks and 6,893 immediate hardware
glyph/attribute checks, including partially typed and scrolling names.
Dialogue lint passes for 828 rows with the longest player name.

A private clean source build with RGBDS 1.0.4 regenerates the new graphics
and produces the identical ROM. CI now installs the pinned Python art
dependencies and uses modern GNU Make on macOS; remote CI has not been
reported as passing by this task.

The independent browser core checks the CGB-only header, 2 MiB ROM,
MBC3+RTC+RAM+battery mapper, 32 KiB SRAM, checksums, tick-based RTC,
checkpoint restoration and twelve emulator lifecycle cycles. The browser
routes check ordinary play, actual native SAVE/cold Continue, audio, touch
controls and narrow layouts on the exact packaged HTML.

## Remaining limits

One real save, four actions, spell charges instead of a common mana/rage
pool, finite enemies and the existing prototype services remain. This does
not implement a full equipment system or all of WoW Classic.

The emulator clock pauses while the browser is closed; a raw `.sav` contains
SRAM, not the RTC. Neither the physical Chromatic, DevDay cartridge profile,
firmware nor hardware save retention was tested. No cartridge was programmed
and the ModRetro plugin was not used. See [browser instructions](BROWSER_PLAYER_V026.md)
for hosting and the distinction between emulation and hardware testing.

## Rebuild

Use RGBDS 1.0.4 and GNU Make 4.3 or newer. Install the art dependencies in
a Python virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r tools/peon_visual_requirements.txt
make pokecrystal.gbc -j4 RGBDS=/path/to/rgbds-1.0.4/
python3 tools/lint_durotar_text.py
```

The optional `tools/rebuild_peon_v026.sh` also regenerates the environment
review sheets in the new folder. It uses `PEON_RGBDS` for the tool path.
Do not run historical art generators over published reference folders.
Native checks require PyBoy 2.7.0; browser checks need Playwright, Chromium
and Node. Detailed graphics allocations are documented in
[class graphics](CLASS_PLAYER_GRAPHICS_V026.md), [typography](TEXT_STYLE_V026.md),
[companions/spells](PETS_SPELLS_VISUAL_V026.md) and [doors/paths](V0_2_6_PATHS_DOORS.md).
