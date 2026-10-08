# v0.2.3 native combat balance

The apprentice should handle two equal-level ordinary foes with little health
to spare. A third usually warrants a potion or better use of Shaman spells.
Higher-level enemies should pose a clear threat. This is a prototype balance
target, not a claim to reproduce Classic's damage formulas.

## Changes

Only four data lines changed:

| Native adapter / visible action | Previous | v0.2.3 |
| --- | ---: | ---: |
| Boar base Attack (`rattata.asm`) | 25 | 35 |
| Scorpid base Attack (`sandshrew.asm`) | 32 | 42 |
| Imp base Special Attack (`geodude.asm`) | 35 | 45 |
| Mace Strike power (`moves.asm`, stable move ID 1) | 40 | 50 |

HP, defenses, speed, creature XP rewards, Lightning Bolt and the apprentice's
base stats remain unchanged. Damage still follows the native level/stat/type
formula, with its ordinary rounding, critical hits, misses and status effects.
There is no blanket damage multiplier and no save-format change. Enemy stats
are generated when an encounter begins. The player's cached saved stats do
not need to be replaced for this adjustment.

## Native measurements

The final candidate used for the following measurements is
`d34ec40ef60af1ec90a946162254b837517867175654b0c6e282260fb91c4aae`.
The validator runs the real ROM in PyBoy. Its 99 chains cover starting levels
2, 4 and 6; boars, scorpids and imps; and seed values 17, 143 and 221.

| Policy | Two equal-level wins | Three equal-level wins | Third defeat or remaining HP ≤25% |
| --- | ---: | ---: | ---: |
| Starter Mace Strike only | 23 / 27 | 7 / 27 | 25 / 27 |
| Starter Lightning Bolt only | 27 / 27 | 14 / 27 | 18 / 27 |
| Flame Shock, then Bolt; levels 4 / 6 | 18 / 18 | 15 / 18 | 7 / 18 |

The Bolt-only third-fight concern occurs in 7/9 chains starting at level 2,
4/9 at level 4 and 7/9 at level 6. This deliberately reports mixed outcomes:
two ordinary foes are manageable; the next fight is risky, rather than a
scripted defeat.

A Minor Healing Potion is actually selected and consumed with ordinary
Start → Bags → inventory buttons before replaying the third Bolt fight.
Its native effect restores up to 20 HP. All 27 assisted third fights are won;
26/27 improve on the unassisted result. Poison and spell charges are unchanged
by the potion. None of these encounters calls `HealParty`.

Against a foe two levels above the starting apprentice, 21/27 trials end in
defeat or with no more than half of the resulting maximum HP. Fourteen of
these difficult encounters are still won. This leaves room for critical hits
and player decisions rather than making higher-level enemies unbeatable.

Flame Shock's guaranteed burn helps against physical attackers by reducing
their damage and dealing damage over time. Its separate strategy skips the
spell against Fire imps and uses Bolt instead. These optional diagnostic spell
slots do not constitute a trainer-acquisition test.

## What the fixtures do

The intro, menus, attacks, poison, PP consumption, XP, level-ups and defeat
recovery all execute through the ROM. The diagnostic sets a starter level
before the native party generator runs, then substitutes the scripted boar's
species and level before the native enemy generator runs. The hardware RNG
continues to generate actual rolls after the declared initial state is set.
No CPU execution, RNG return or damage result is substituted.

The world state is rewound to respawn an encounter between fights. The entire
48-byte native party record is copied unchanged across that rewind, preserving
HP, poison, moves, charges, XP, stats and the held weapon. Every following enemy
matches the player's current native level, including level-ups after a kill.
Level-ups retain the original addition of gained maximum HP; they are not full
heals. A poison defeat is also observed at the real recovery entry, since
residual damage can bypass a move's `CheckFaint` command.

The potion fixture supplies one temporary item stack, then uses the real menu
and item effect; it verifies the HP result and actual stack consumption. Flame
Shock fixtures place that learned spell in the temporary diagnostic record for
levels 4 and 6. Gear upgrades, Earth Totem and Healing Wave are excluded from
the main starter comparison. Walking poison damage between distant encounters
is excluded because the encounter world is rewound; real route tests cover
travel, shops, available potions and inn access separately.

The historical baseline uses the previous ROM
`bbda42f538d2704a601fc05ef5b44c8ca332538a9422dd237e45f74b24c4dc96`.
Its equal-level Bolt results were 26/27 second victories and 15/27 third
victories; Mace-only second victories were 12/27. The first fixed-level probe
also demonstrated why the next foe must follow the actual player level:
earned XP could otherwise make the later foes lower-level. Historical reports
retain their exact hash under `historical_rom_sha256` and are explicitly
excluded from final candidate validation. Added sprite-animation frames change
RNG timing too, so the baseline/candidate differences are not presented as
isolated statistical attribution to the four data lines.

## Reproducing the checks

Run `PYTHONPATH=/workspace/toolchains/pyboy-preview python tools/validate_peon_balance.py`.
The default runs the complete final scope and writes
`references/generated/durotar_v023/combat_balance/validation.json` only after
its native checks and quantitative assertions pass:

- At least 75% of two equal-level Bolt chains are survived.
- At least 50% of third Bolt chains end in defeat or no more than 25% HP.
- One actually consumed potion improves a majority of eligible third fights.
- A majority of +2-level foes cause defeat or no more than 50% HP.
- Equal-level fixtures match the actual player level at every fight.
- Native party state carries intact, and encounters never call `HealParty`.

Individual per-level runs can be used for diagnostics; `--combine candidate`
checks that all three current candidate reports match the frozen ROM before
applying the same final assertions. PNG captures show actual ROM frames, not
external illustrations. All tests use temporary ROM copies and never open a
user battery save.
