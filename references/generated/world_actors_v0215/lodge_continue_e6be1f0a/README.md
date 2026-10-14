# Three class lodge, Zone Two worker and real cold Continue

Exact ROM SHA-256:
`e6be1f0a31ce390f07d8d3a181248ac7945f2085692a3930bee3d4f54d6b8e5a`.

Aggregate status: `PASS`; all three class suites: `PASS`.

All three actual class selections passed the initialized class flags, party,
attacks, kit and player-name assertions. The test uses only ordinary buttons
in private fresh ROM copies. No emulator RAM writes, CPU substitutions,
loaded states or user battery saves were used. Native read-only observers
wait for menu readiness and completed OAM publication; controlled presses
release after the first movement/cursor acknowledgement.

Fresh lodge entry and cold Continue both show all 27 unchanged master cells
and exactly 939 opaque master pixels. Each hero's complete 24×24 frame matches
its nine-tile native source, exact nonblank tile mask and every opaque actual
LCD pixel. Shaman and Warlock use 36 room OAM objects; Warrior uses 35 because
one authored tile is empty. Maximum scanline occupancy is 6, below the limit 10.
The six-object HUD is omitted entirely in this room because only 4/5 OAM slots
remain. No body cells are replaced by HUD or cut from a character.

All real master speakers/portraits and matching native training menus pass;
the other two masters refuse the incorrect class. The full name
Bismillah LesTenèbres remains readable. The Zone Two worker at (20,13) wakes
through its native quest script; returning to the foreman yields 100c once.

Each class saves through the actual SAVE menu, writes its own private 32 KiB
battery, closes the emulator and cold boots CONTINUE. Full party records,
names, moves, HP, event flags, money, class, map and position remain equal.
The restored bodies/palettes pass the same strict LCD check after an observed
native shadow-OAM publication and a completed LCD scan. Warlock's party has
its same Imp, hidden only in the lodge and visibly restored outdoors even
after this cold Continue.

`validation.json` contains the measured per-class results. PNGs are actual
native 160×144 LCD captures; `_4x.png` files use nearest-neighbor enlargement.
This is emulator evidence, not a physical ModRetro device test.
