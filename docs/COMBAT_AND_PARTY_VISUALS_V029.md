# Native combat and party visuals, v0.2.9

The native battle is still one active fighter against one active opponent.
The player keeps a real party of two initially, with the third place unlocked
after reporting Sarkoth to Gornek. Opponent packs contain successive native
wild opponents, without a trainer, balls, or a trainer-party presentation.

## Finite packs

| Encounter | Members | Partial retirement | Full reward |
| --- | --- | --- | --- |
| Valley eastern gate | Kolkar Archer 7, Kolkar Raider 8 | Archer saved bit | Both actors retire, 60 copper |
| Burning Blade cultist, player level 4+ | Orc Warlock 4, Imp 4 | Warlock saved bit | Cultist actor retires, 25 copper |
| Southern road near Sen'jin | Scorpid 6, Scorpid 7, Raptor 7 | First and second saved bits | Pack actor retires, 75 copper |

The level-three cultist remains a solo encounter. A solo victory that raises
the player to level four does not grow another enemy during its animation.
Existing full-retirement bits continue to hide previously completed encounters.
The old road pack's first-member bit is retained when upgrading an old save.

Each defeated member goes through the native faint and XP path once. Partial
saved bits make a new attempt start from the surviving member after fleeing,
losing, saving, and cold restarting. The full map-script victory grants copper
and one rare-potion roll; there is no intermediate loot or refill. The one roll
per completed pack is deliberately rarer per creature than the solo 1-in-6 roll.

Replacement clears enemy-only status, stat stages and counter-move state. It
does not reset player HP, saved mana/rage, poison/burn, or the placed Earthbind
totem. Switching the active ally removes actor-specific buffs but leaves the
field totem. All exit paths clear battle-only field state before its RAM union returns to
terrain storage. A post-battle terrain byte is not a live totem flag.

The Road pack is temporarily hidden below level four without setting its
saved retirement flag. That mask is applied after Crystal regenerates object
masks, so a map callback cannot be overwritten by the native loader.
Level-four-plus characters see the pack again on map load.

## Graphics allocations

Each active companion has three independent 48×48 back poses in the existing
36-tile player region, bank 0 `$9310..$954f`. The shared atomic loader stages a
complete 576-byte pose and publishes it by CGB general DMA during VBlank.
No back-pose copy uses the enemy's front tiles or a partial visible-frame upload.

Two inactive-member indicators use native 8×8 heads and four-segment HP strips.
Four bank-1 BG tiles occupy `$8a90..$8acf`, immediately after the existing
23-glyph bold-name cache. These indicators add no OAM objects. Their heads
inherit the active portrait's palette; no EXP, HP, elite-rank, font or pet/totem
palette is overwritten. The inactive hero uses the small Orc head. This compact
display is an indicator, not a second independent fighter rendered on screen.

The passive imp attacks for one HP only when it is a living, inactive real
party member. It does not attack twice while it is the active fighter. Its old
six-cell footprint is erased when it is active or fainted, preventing a stale
duplicate companion beside the large combat silhouette.

The four-phase Kolkar arrow substitutes an equally sized 12-tile FX packet:
four retained Firebolt tiles plus eight arrow tiles. The existing projectile
objects gain native enemy-only bitmap mirroring. Guarded enemy Warlock, imp and
archer scripts launch beside their authored hands and travel two pixels left and
one pixel down per frame. Existing player and passive-imp launch paths remain
separate. The large active imp keeps its raised-hand origin and rises one pixel for
every two pixels right; the native pixels stay clear of the player HUD. Its
saved Firebolt id53 uses visual id52, so the scoped token branches enter the
actual Flame Shock animation target without changing Flame Shock itself.
No additional animation-object slots are allocated.

## Evidence and limits

The v0.2.8 checkpoint passed all 39 class casts, protected tile/font/palette
checks, consecutive-frame actor checks, and the ten-OBJ-per-scanline limit on
ROM SHA `943d460f6f76e15dff5b0fc2b8b11b90ba4c2ae79d5e190ea9dd3870b4d68620`.
That is the checkpoint's evidence, not proof for a subsequently rebuilt ROM.

`tools/validate_peon_packs_v029.py` checks the v0.2.9 native state transitions
using explicitly declared disposable, natively saved diagnostic fixtures.
The separate team/progression validator covers real recruitment and ordinary
quest progression. Source PNGs and compiler success do not establish runtime
correctness. Both native reports passed on final ROM SHA
`4530c718bf299ec9e1c8de8c52895906a81024345bd60717cd5c99dbd30b8a93`
and symbols SHA
`87226ec5c81393762a3f7b2f6b11e43e68e0fc687b8cc3c0d22c3a74e25b2376`.

- `references/generated/recruitment_v029/pack_runtime/validation.json`: all
  three packs, one native XP call per defeated member, one full reward,
  no repeated XP/reward after flee/loss and cold save, real mutual faint,
  forced living ally and subsequent full victory, Road visibility, native
  two- and three-member sidebar/font/resource pixels. Ordinary OAM peak 8;
  the native Selfdestruct corner reaches 10 without exceeding the limit.
- `references/generated/recruitment_v029/projectile_runtime/validation.json`:
  all four particle phases for the active imp, hostile imp, hostile Warlock
  and archer; native mirrored bitmap halves, impact and physical RGB555
  pixels; no coloured particle or impact inside the player HUD.

Transparent original bow frames are
`references/generated/recruitment_v029/combat_assets/kolkar_arrow_phase_00_16x8.png`
through `kolkar_arrow_phase_03_16x8.png`, with native APNG and enlarged PNGs
alongside. Actual emulator captures and animation GIFs are in
`references/generated/recruitment_v029/projectile_runtime/`.

Physical
Chromatic firmware, cartridge programming and hardware playback are separate
checks and require the actual device.
