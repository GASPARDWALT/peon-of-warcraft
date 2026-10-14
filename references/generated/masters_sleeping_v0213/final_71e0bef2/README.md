# Native lodge and sleeping-worker validation

ROM SHA-256: `71e0bef22a4d1fee32af20a94fb8474db29f0d610f60a0fdfcd93c00fdab8a9a`.

All three class routes passed using actual buttons in private fresh ROM
copies. No emulator RAM writes, loaded states, CPU substitutions or user
battery files were used. Each route enters the western The Den lodge,
checks all three masters, opens the correct native trainer, refuses the
other two classes, wakes the Zone Two worker and returns for exactly one
100c reward.

Both fresh entry and cold Continue show all 27 master graphics tiles and
exactly 939 opaque source-converted pixels on the actual 160×144 LCD.
The scene has 37 visible OAM objects, with at most five on one scanline.
The masters are complete 24×24 bodies imported from the supplied class
master reference; see `references/generated/large_masters_v0213/README.md`
for the honest raster conversion and palette constraints.

The Warlock retains its Imp as party member two. Its walking follower is
hidden only in this room, returns outside, and cannot block the doorway.
The full name Bismillah LesTenèbres is readable in the native dialogue.

Each route uses the game's actual SAVE option, writes a private 32 KiB
battery file, stops the emulator and cold boots CONTINUE. Full party
records, nicknames, moves, HP, quest flags, money, class and position remain
identical. The rebuilt current master scene passes the same tile, LCD
pixel, OAM and palette checks after the restart.

Screenshots are native LCD captures; files ending `_4x.png` use only
nearest-neighbor enlargement. Main evidence for each class:

- `all_three_complete_large_masters_native_lcd.png`
- `master_<class>_native_training_menu.png`
- `master_warlock_dialogue.png`
- `zone_two_sleeping_peon_wakes.png`
- `foreman_lazy_quest_reward.png`
- `training_lodge_cold_continue_native_lcd.png`

This is emulator evidence, not a claim of a physical ModRetro device test.
