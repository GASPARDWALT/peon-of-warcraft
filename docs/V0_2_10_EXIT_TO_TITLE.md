# v0.2.10 — EXIT returns to the title

Selecting EXIT in the native Start menu used to close the menu and resume the
world. It now waits for A/START to be released, then uses the existing native
reset path to return to the Peon title. A fresh START opens character selection.
Continue loads the last saved character and location. B still closes the menu
and resumes the world.

EXIT does not autosave. Save with Start → SAVE to retain changes since the
previous save. Reset clears temporary menu/display/working memory; the real
save and backup remain intact. The native graphics scratch buffer in SRAM bank
0 is temporary, so its normal clearing is recorded separately from saved data.

The only native source change is `engine/menus/start_menu.asm`: the EXIT action
and its description. Save addresses, party records, mapper, RTC configuration,
maps, graphics and gameplay systems remain those of v0.2.9.

The final ROM SHA-256 is
`0e2d747636788211b9a046df698ef9fecdafd1166e0514381815fd88ed22bb66`.
It remains CGB-only, 2 MiB, MBC3+RTC+RAM+battery, with 32 KiB save RAM.
The build completed with zero compiler warnings or errors.

Native checks cover 18 EXIT → title → START → Continue cycles across the
three current classes and three genuinely upgraded old saves. A held for 240
frames waits for release; the title remains stable for 600 neutral frames.
Full saved identity, all party records, bag, quest flags, money and location
match after Continue. No SAVE or New Game is triggered by EXIT.

Browser checks cover all three normal class routes, native save/cold Continue,
exact title pixels, a title session checkpoint/reload, held-A input, keyboard,
audio and mobile touch. Twelve engine initialization/reset cycles also pass.
Only expected graphics scratch bytes change; every byte of persistent save
memory outside that declared buffer remains identical.

Evidence: `references/generated/exit_title_v0210/` and
`references/generated/browser_player_v0210/`. These are emulation checks;
physical Chromatic/DevDay hardware remains untested.

For a ROM upgrade, import a native `.sav`, not an older emulator checkpoint.
When loading an older pre-v0.2.9 save, perform SAVE once after Continue to retain
the existing party/resource migration, including a Warlock's new Imp.

The separate `references/generated/peon_sprite_redesign_v030/` pack contains
the new native-size Peon PNGs and class-master proposals. They are not included
in this ROM. Their color palettes/tile allocations still need game integration.
