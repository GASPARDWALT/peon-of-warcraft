# Peon of Warcraft v0.2.8

This release refines the native 160×144 Game Boy Color presentation. It keeps
one Crystal battery save and the existing four-action battle record.

## Changes

- Three original low-level Orc apprentices, with independent directional
  world frames and three rear battle poses: mace/shield/totem Shaman, simple
  axe Warrior and novice hood/wand Warlock. Transparent PNG/APNG assets are
  provided at native size, with separately labeled enlarged source previews.
- Blue, red and purple class-selection backgrounds, while skin and equipment
  keep their own palettes.
- Traversable quest indicators. Their available/accepted/complete state still
  follows the actual quest flags; the NPC itself retains its collision.
- Wand Strike replaces the Warlock's basic melee presentation and uses a
  ranged projectile. Saved move IDs and damage rules remain unchanged.
- Redesigned elemental particles and projectiles, and a bounded VBlank general-DMA upload
  for complete player battle poses. Menu, HUD, totem and enemy transfers
  preserve the correct VRAM bank and background refresh mode.
- Rounded hide/timber huts and inns, corner beds and wall fire bowls. Clear
  foot exits retain every old walkable room coordinate and door destination.
- A recognizable hand-drawn Horde crest on wall banners. Carpet art is plain
  cloth, with no repeated ground crests.
- A looping native arrangement from the supplied “What's Up” sheet music.
  The arrangement scope and transcription are documented in the music assets.
  The same theme is used across Peon maps and battles; the title and short
  reward jingles retain their separate roles.

## Play and files

The ROM archive contains `peon_of_warcraft_v0_2_8.gbc`, its exact-hash manifest
and native validation reports. The separate art archive includes an `index.html`
gallery: extract the whole archive before opening it. Source drawings and
actual emulator captures carry distinct labels. Source-only cast halos are
reusable artwork and do not claim to be implemented ROM effects.

The standalone browser player is distributed in its own archive. Extract it
and open its HTML file with a browser; no external ROM or WASM download is
needed during play. Keyboard: arrows, Z/A, X/B, Enter/Start and Shift/Select.
Touch controls, audio and battery import/export remain available.

## Saves and console

The ROM retains CGB-only mode, MBC3 with RTC, 2 MiB ROM and 32 KiB battery RAM.
Existing map/item/move indices and saved record sizes are retained. Import an
older character as a `.sav` battery file, rather than an old emulator snapshot.
Browser session snapshots are tied to their exact ROM hash. The browser RTC
pauses while closed; a raw `.sav` contains RAM without RTC metadata.

Cold save continuation and old-battery migration are validated in emulators.
The physical Chromatic and DevDay cartridge still require console tests; no
cartridge is programmed by this release workflow.

The project remains a prototype: three classes share the original stat model,
spell charges stand in for mana/rage, four actions are stored, and not every
named NPC has an individual portrait. These art changes do not implement a
new equipment storage system, simultaneous multi-enemy battles or multi-save.
