# Companion, totem and projectile visuals — v0.2.6

This milestone changes native graphics and animation, without changing level
progression, damage formulas, spell charges, item prices or the battery layout.

The friendly imp now has its own walking sheet. The six original 16×16 native
cells retain the engine's 12 idle and 12 walking tiles, but the visible imp is
only 10×11 pixels in its standing pose. Sprite `$68` is appended after the
mailbox; hostile imp sprite `$4c` and its pixel art remain unchanged. Native
following, collision exclusion and the one optional actor slot retain their
v0.2.5 behavior. Continue recreates the new companion from the saved class flag.

The combat imp and carved Earth Totem are each **16×24**. This increases the
imp's height from 16 pixels and the totem from 8×16 without overlapping either
HUD, the player backpic or an elite enemy's dragon frame. Both use columns 8–9,
rows 4–6 of the 160×144 viewport; the player HUD begins at column 9, row 7, and
the dragon emblem occupies columns 10–11, rows 4–6. The Shaman's totem and
Warlock's imp have distinct reserved bank-1 tile ranges:

| Art | Tile IDs | Native bank-1 address |
| --- | --- | --- |
| Earth Totem | `$86..$8b` | `$8860..$88bf` |
| Imp idle/casting pose | `$8c..$91` | `$88c0..$891f` |

The imp raises its arm before shooting a small animated fireball. Firebolt
uses Crystal's native battle-object interpreter: one 8×8 particle moves two
pixels right per frame and one pixel up every eight frames, cycling four
original pixel frames. Its appended object function `$50` leaves all earlier
functions unchanged. The raised-hand origin (80,44) and impact (132,40) keep
the full particle above the HUD and meet the normal boar/scorpid body pixels.
The former whole-background-tile hopping is removed. The appended visual-only
special animation ID is `$116`; all previous move/special-animation IDs retain
their values. Original full-round guards and fixed **1 HP** pet damage remain.
The imp cannot attack after fleeing, a canceled item, a lost battle or an
already defeated combatant. A successful potion still costs one enemy turn,
then permits the pet attack. Pet finishing blows use native victory/XP/quest
handling.

Shadow Bolt gets a new four-frame 16×8 projectile with a dark trailing tail,
smooth native travel and a small impact. It launches beside the actual staff
tip at physical (32,52), using the same shallow function through (132,46), above the
reserved HUD rectangle and into the opponent's visible lower body. Only its
particle OBJ palette 6 is
temporarily tinted purple. The original OBJ palette source is preserved, so
native animation cleanup restores the prior palette. The guard switches from
the interpreter's WRAM bank 5 to the class/map bank 1 and restores the original
bank on every exit; both existing Shadow Bolt animation aliases are covered.
Actor portrait palettes,
font palettes and every background palette are protected. The Firebolt's
particle uses the existing red spell palette. No animation frame adds a fifth
player move or an extra enemy action.

Animation bytecode coordinates include the hardware OAM origin. Firebolt's
raw (88,60) becomes physical center (80,44); Shadow Bolt's raw (40,68)
becomes physical head (32,52). The two Shadow OAM tiles share a scanline and
are exactly eight pixels apart, forming the authored 16×8 source frame.
The floating motion helper leaves the pinned animation/music bank within its
original limit and changes neither audio nor WRAM allocation.

Original transparent PNGs and sheets, exact RGB555 colors, and the asset
manifest are saved in:

```text
references/generated/visual_polish_v026/pets_spells/assets/
```

The dedicated builder writes only new v0.2.6 targets:

```sh
python tools/build_peon_pet_spell_assets_v026.py
```

Do not invoke the older pet generator to recreate this milestone: its public
v0.2.5 evidence is immutable. The Makefile's explicit v0.2.6 grouped targets
rebuild the new native art on a clean checkout.

Native validation:

```sh
PYTHONPATH=/workspace/toolchains/pyboy-preview \
  python tools/validate_peon_pets_spells_v026.py --expected-sha ROM_SHA256
```

The normal route uses real controls for class selection, following, a mailbox,
room/zone transitions, battles and a 32 KiB cold battery restart. Separate
private diagnostics declare their temporary HP/speed fixtures: actual Shadow
Bolt casts, full/rejected/canceled potion actions, native flee and defeat,
Earth Totem placement, and a 1 HP pet finishing blow. The validator checks
actual framebuffer colors, native OAM animation phases and motion, protected
actor tiles, final palettes, spell charges, turn counts and absence of duplicate
followers. Native screenshots and animated GIFs are emitted next to the report
under `pets_spells/`; `validation.json` is successful only when `passed: true`
and its ROM SHA matches the delivered build.

Potion consumption is observed before enemy action and loot. Final inventory
also accounts for a legitimate native rare potion grant after victory; that
grant can replace the potion just consumed.
