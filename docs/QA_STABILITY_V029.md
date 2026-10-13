# Native team and save checks for v0.2.9

This describes the validation method. Runtime success is established only by
the result files naming the final ROM and symbol SHA-256, not by this document
or by generated source art.

## Cold save upgrade

`tools/validate_peon_save_upgrade_v029.py --prepare` plays the frozen v0.2.8
candidate with actual buttons. Each class completes the real intro and naming,
buys its level-two lesson, fights the first boar, and turns in Gornek's first
quest. The three fixtures have actual combat injury and spent spell charges.
The Warrior also fights a scorpid and level-three imp because its boar died
before attacking. A native Save-menu write and a separate cold Continue prove
each source 32 KiB battery before it is used for migration testing.

The observer constants, maps, collision rows and symbols are frozen before
v0.2.9 integration. The private batteries belong to this validator and are not
user saves. Preparation and upgrade never write emulator memory or load states.

The upgrade compares all six native party records, party names/OTs, character
identity, all 256 event bytes, all bag pockets, money, saved location/return
warp metadata and both saved Dex bitsets. The allowed changes are explicitly
bounded: the hero's three resource metadata bytes, plus the one new native Imp
record/species/name/OT and reserved starter flag for a legacy single-member
Warlock. Existing memory addresses and persisted numeric IDs must stay equal.
The geometry suite separately checks safe relocation from newly blocked cells.

A second native save and cold Continue must preserve the upgraded records
exactly. Character → right → Team → cancel also must not alter a saved record,
refill a resource or initialize another Imp.

## Ordinary team and recruitment route

`tools/validate_peon_team_recruitment_v029.py` starts from copies of those
genuine source batteries and continues with the exact candidate ROM. It checks:

- One class-relic quest and item, with no repeated kit/relic grant.
- Wrong-family refusals while a roster place is free, and a correct-family
  Warlock refusal while its initial two places are occupied.
- Actual native HP/status/base-ball catch-rate thresholds on each relic roll;
  failed and successful attempts leave the reusable relic quantity unchanged.
- Recruited allies as native party records with the captured level, HP and
  status, without a ball effect, nickname question or Dex-entry screen.
- Character's Team panel, preferred actor, real companion starting combat,
  and voluntary native switching with one enemy turn opportunity.
- The real scorpid, Hana'zua, Sarkoth and Gornek-report chain unlocking the
  third place; a Warlock can then recruit another Imp as record three.
- One-time class quest experience and copper, with a repeated master visit
  preserving the completed reward.
- Complete settled native PPU backgrounds at the new Team panel, its return
  and battle restoration, using actual VRAM/banks/palettes/window registers.

Selecting a single class is a preflight check. The report explicitly separates
that scope from the complete three-class gate. The full gate requires all three
classes against one immutable ROM/symbol pair.

Resource spending/supplies and pack retirement/loot/flee/loss edge cases belong
to the separate resource and combat suites. Six-role animation/source packets,
active ally backs, crowded Sen'jin, OAM scanlines and protected VRAM belong to
the art/combat suites. These complementary checks do not imply physical
Chromatic/cartridge testing, arbitrary old saves, or every possible game state.

## Final native result

The complete ordinary three-class gate and the three genuine old-save upgrades
passed on immutable candidate07:

- ROM SHA-256: `4530c718bf299ec9e1c8de8c52895906a81024345bd60717cd5c99dbd30b8a93`.
- Symbol SHA-256: `87226ec5c81393762a3f7b2f6b11e43e68e0fc687b8cc3c0d22c3a74e25b2376`.
- Canonical results: `references/generated/recruitment_v029/team_runtime/validation.json`
  and `references/generated/recruitment_v029/save_upgrade/validation.json`.
- Final actual screenshots/GIFs: `team_runtime/final/{shaman,warrior,warlock}/`;
  `team_runtime/final_gallery_manifest.json` hashes all 158 passing native files.

The ordinary route additionally checks that capture preserves the actual
player object and removes the target object, then continues walking. It
independently recomputes all six captured raw stats from the linked ROM base
stats, original DVs, level and native stat experience. Locked-row refusal,
TEAM cancellation and voluntary switching restore the twelve battle-font
packets and the live bold-name references/actual RGB555 pixels. Together the
three class routes provide 34 settled PPU surfaces and nine battle-font/name
checks, including native complete cold party saves.

The genuine Sen'jin battery comes from the actual Warlock quest/report/recruit
route. The level-five hero and its two real Imps use native RUN through the
west/east Kolkar aggressors and the Road pack, with unchanged experience,
copper and retirement flags. The Troll Inn then heals the actual party before
a native Save at Sen'jin `(10,8)`. This proves playable travel and supplies the
crowded-map art gate; it does not claim the underleveled party won those packs.
Pack victories, partial retirement and forced replacements are independently
covered by the combat suite's explicitly labelled native diagnostic fixtures.

## Bugs found before the final gate

The native tests found two concrete recruitment integration defects: object
scripts used 16-bit pointers to another ROM bank, and the capture scripts used
`disappear 1` for runtime object1 even though script NPC operands are one-based.
The latter deleted the player's runtime object0. Map-local `farsjump` wrappers
and corrected script operands fix those defects; the final ordinary captures
verify the resulting behavior rather than relying on source inspection.

Native Warlock spell/pet regression also exposed the final glyph of ten-letter
Kolkar names losing its bank1 bold-font attribute after animation restoration.
The row-zero font guard now retains column10. Genuine new menu-return checks
and the final combat/art suites verify the restored fonts and visible pixels.
Old failed/preflight evidence is diagnostic and excluded from the final gallery.
