# Kento's apprentice training — v0.2.2

Kento in the Den sells eleven Shaman lessons at even levels. Mace Strike and
Lightning Bolt always remain in the first two active slots. Two further slots
hold purchased training spells; the player chooses which to replace when both
are occupied. An owned spell may be prepared again without paying a second time.

| Level | Lesson | Native move ID | Copper | Prototype effect |
| --- | --- | --- | --- | --- |
| 2 | Rockbiter | 14 | 10 | Empowers the next physical attack, then expires |
| 4 | Earth Shock | 9 | 100 | Nature damage with a chance to interrupt a slower foe |
| 4 | Flame Shock | 52 | 50 | Fire damage and guaranteed burn except immunity/status protection |
| 6 | Healing Wave | 105 | 100 | Restores half maximum health during combat |
| 8 | Lightning Shield | 115 | 100 | Lightning retaliation against a melee attacker |
| 10 | Strength of Earth Totem | 96 | 400 | Raises the apprentice's attack for this combat |
| 12 | Purge | 114 | 720 | Removes the enemy's positive stat bonuses |
| 14 | Frost Shock | 58 | 200 | Frost damage lowers the enemy's speed |
| 16 | Flame Shock II | 126 | 400 | Stronger fire damage and guaranteed burn except immunity/status protection |
| 18 | Windfury | 3 | 600 | Two to five physical hits in the native multi-hit model |
| 20 | Chain Lightning | 87 | 800 | Heavy Nature damage against one foe |

Purchasing grants initial spell charges. Free re-equipping preserves the
destination slot's remaining charges, capped to the selected spell's maximum;
it does not refill health, Lightning Bolt or other active spell charges. An
already prepared spell changes neither charges nor money. B cancels purchasing
or choosing a replacement before any charge or ownership flag is written.

Kento no longer gives repeat equipment or free restoration. The fire is scenery;
the northeast Den hut is the inn. Successful battles retain health and charge
costs. Defeat recovery uses the separate native respawn helper. Grommash Hold's
scene and direct NPC interaction share the `EVENT_PEON_SHAMAN` guard, so the
character's name, apprentice kit and initial moves are not initialized twice.
The kit also contains the one-time Earth Totem inventory object; it is separate
from the level-10 Strength of Earth lesson. Six active attacks would expand native
party/move/save structures, so v0.2.2 keeps four stored attacks and a separate
usable totem in the bag rather than changing the save format.

## Classic provenance and adaptations

Prices come from the local archived CMaNGOS Classic-DB 1.12.1 snapshot
`/tmp/peon-classic.sql.gz`, identified by `db_version` as Melting Pot v2, z2815.
The reference rows are `npc_trainer_template` template 61 and `npc_trainer`
Swart 3173, with spell identities in `spell_template`:

| Lesson | Classic cast spell | Trainer learn spell | Classic base level/cost |
| --- | --- | --- | --- |
| Rockbiter Weapon rank 1 | 8017 | 8020 | 1 / 10 copper |
| Earth Shock rank 1 | 8042 | 8043 | 4 / 100 copper |
| Healing Wave rank 2 | 332 | 1326 | 6 / 100 copper |
| Lightning Shield rank 1 | 324 | 1303 | 8 / 100 copper |
| Strength of Earth Totem rank 1 | 8075 | 8077 | 10 / 400 copper |
| Purge rank 1 | 370 | 1333 | 12 / 720 copper |

Rockbiter is deliberately delayed to level 2. Classic's rank-1 Healing Wave
(331) is a free starting spell; this demo first unlocks healing at level 6 and
uses the rank-2 trainer cost. Prices are archived base prices, without reputation
discounts, not a claim of live Blizzard verification. The user-requested Flame
Shock at level 4 costs an explicitly adapted 50 copper;
Frost Shock 14, Flame Shock II 16, Windfury 18 and Chain Lightning 20 and their
prices are prototype progression, not canonical rank-unlock claims. Windfury
uses the native two-to-five-hit model, and Chain Lightning has one target in
this single-enemy build.

Turn order, half-health healing, combat-duration totem and PP-backed charges
are native turn-based
adaptations rather than an exact recreation of Classic timings and mana.

The eleven lessons reuse numeric move slots already absent from accessible
demo encounters, except slot 52: its former Firebolt use moves to slot 53 in
the three accessible imp/cultist/boss learnsets. MACHOP remains the internal
player species; its evolution list is
empty and its only automatic starting moves are Mace Strike and Lightning Bolt.
Later levels never show the old Pokemon learning/forgetting interface.
Earth Shock uses the internal Electric special category for Nature damage; its
native earth animation does not make it a physical attack or consume Rockbiter.

`tools/validate_peon_trainer.py` separates the fresh normal-button purchasing,
refusal and battery-save route from explicitly labelled level/money/charge
diagnostics used to cover later lessons quickly. Its report and screenshots
belong under `references/generated/durotar_v022/trainer_validation/`.

Legacy Shaman saves receive the new reusable Earth Totem at Kento if it is
missing. A full bag leaves the handoff retryable. An existing Totem skips the
handoff, and the original mace, shield and belt totem are never given again.
