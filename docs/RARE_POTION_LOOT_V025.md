# Rare potion loot — v0.2.5

Each newly defeated, finite enemy has an independent **1/6 chance** to add one
potion to the normal item bag. This is an average, not a guaranteed potion on
every sixth kill. It is the requested prototype balance, not a transcription of
the individual loot tables of World of Warcraft Classic.

- Shaman and Warlock: successful drops are two parts **HEAL POTION** to one part
  **MANA POTION**. Their total potion chance remains 1/6.
- Warrior: every successful potion drop is a **HEAL POTION**. Unusable mana
  potions do not drop for this class.
- Healing restores up to 20 HP. Mana restores up to five charges of each
  prepared magical action; spell charges are the current save-compatible mana
  substitute. These effects belong to `CLASS_POTIONS_V025.md`.

The same enemy cannot be farmed by walking through its old tile. A victory
commits its existing saved retirement flag before it invokes the loot script.
Fleeing, losing, rejecting a neutral encounter, and revisiting a dead enemy
grant nothing. The two successive road scorpids roll separately: the first
scorpid's existing saved `FIRST` bit prevents another roll if the second fight
ends in defeat or flight.

A successful receipt displays one brief message identifying the potion. A
failed roll adds no message. If the bag cannot receive the item, existing item
stacks, coins, XP and quest progress remain intact and the script returns
without freezing input. Optional full-bag loot is not placed on the ground or
deferred for a later retry. Boss claws and the Burning Blade Medallion retain
their separate, existing questgiver recovery path.

Implementation:

- `engine/events/peon_loot.asm`: common native helper and feedback script.
- `main.asm`: includes that helper.
- `maps/TheDen.asm`, `maps/ValleyOfTrials.asm`,
  `maps/BurningBladeCavern.asm`, `maps/DurotarRoad.asm`: 16 finite kill hooks,
  covering the boar, scorpids, familiars, Sarkoth, cavern enemies and road fauna.
  The split valley screens share those guarded scripts.
- `tools/validate_peon_rare_loot.py`: native runtime validation.

The helper uses Crystal's existing `RandomRange(6)`, which rejects byte values
252–255 and divides each of the 252 accepted byte values into six equal
groups. Exactly 42 accepted inputs succeed: `42/252 = 1/6`. Caster selection
uses the corresponding unbiased `RandomRange(3)` and adds no second potion.
The original Potion and Ether IDs are reused; no new save fields, counters,
event flags, inventory allocation or random generator are added.

Validation separates actual play from fault injection:

- Fresh Shaman, Warrior and Warlock characters use ordinary buttons to win a
  real boar encounter. Exactly one loot helper call executes. Returning to its
  cleared tile neither starts another combat nor grants another item.
- Explicit, disposable RNG-byte fixtures execute the real native helper for
  all 256 range-six inputs, all 255 accepted range-three inputs, and both
  rejected tails. No CPU instruction, division or item receipt is substituted.
- Declared temporary inventory fixtures verify full bags, a full 99-item stack,
  caster receipt and Warrior rejection of mana drops.
- Declared temporary battle HP/speed fixtures produce actual native flee and
  loss outcomes. Neither outcome calls the drop helper or changes inventory
  and copper; the enemy remains alive.

The report and native screenshots are saved in
`references/generated/environment_v025/loot/`. Each report records the exact
ROM SHA-256 tested. No user battery-save file is read or changed.

Reproduce after building the current ROM:

```sh
PYTHONPATH=/workspace/toolchains/pyboy-preview \
  python3 tools/validate_peon_rare_loot.py --expected-sha <rom-sha256>
```
