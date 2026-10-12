# Class supplies and native potion behavior

The v0.2.5 class prototype gives every new apprentice **two Minor Healing
Potions**. Shaman and Warlock also receive **one Minor Mana Potion**. The native
item-name records display `HEAL POTION` and `MANA POTION` to fit Crystal's fixed
name width without truncation. An existing save keeps its inventory; continuing
or revisiting a master does not grant another starter supply pack.

## Effects

| Supply | Native effect | Classes | Combat cost |
| --- | --- | --- | --- |
| Minor Healing Potion | Restore up to 20 HP, capped at maximum health | All three | One enemy action |
| Minor Mana Potion | Restore up to five charges in each prepared magical action | Shaman, Warlock | One enemy action |
| Spring Water | Restore up to ten charges in each prepared magical action | Shaman, Warlock | One enemy action |
| Tough Bread | Restore up to 10 HP outside battle | All three | Cannot be eaten during battle |

A full-health or zero-health character cannot use a healing potion. A full
spellbook cannot use mana or water. Warrior cannot use caster supplies. Rejected
uses leave the item, charges, health and turn untouched and show a reason inside
the existing fixed bag frame. Successful uses synchronize the party record and
active battle record before the enemy acts. Combat healing can therefore be
followed immediately by enemy damage; the visible post-turn HP can be lower
than the amount restored by the item.

Mana remains the prototype's **per-action spell charges**, not a new shared mana
pool. WoW Classic's numerical mana restoration is not being claimed here. The
physical basic action is excluded by its move ID rather than its slot, including
older imported spellbooks with reordered actions. Restoring charges preserves
the original two PP-Up bits and reads the real action's maximum from the ROM,
including Crystal's maximum of 61 charges for a 40-charge action with three
upgrades. Empty action slots remain untouched.

## Merchants and persistent data

Duokna and the camp provisioners at The Den, K'waii in Sen'jin Village and Jark
at Razor Hill sell one healing or mana potion for **25 copper**. These are
prototype prices; Spring Water remains five bottles for 25 copper. Existing
water/healing/bread menu positions remain 1/2/3; mana is added at position 4.
The fixed five-row shop menu fits the native screen. Each purchase checks
confirmation, money and inventory capacity before removing copper.

The health potion keeps item ID `POTION` (`0x12`). The mana potion reuses the
previously unreachable `ETHER` ID (`0x3f`) through the `PEON_MINOR_MANA` alias.
No item indexes, inventory sizes or save structures are renumbered. Minor mana
also has a native item-effect entry so it does not fall back to a Pokémon
party-selection prompt if a legacy item-use path reaches it.

The class starter axe and staff reuse the unused `TOWN_MAP` (`0x06`) and
`POKE_FLUTE` (`0x38`) IDs as non-consumable key items. The live Peon map is an
existing event-based UI rather than item `0x06`, so its reward remains intact.
These starter weapons identify the class kit; this change does not claim a new
multi-slot equipment/stat system. The backpack weapon art uses palette 6,
independently of the hearthstone on palette 5.

## Original PNG files

The red healing and blue mana flasks are original 16×16 drawings with exactly
three visible colors and binary transparency. Each compiles to four 2bpp tiles
and one RGB555 palette. On native GBC background layers index zero displays the
menu's parchment color; the exported PNG retains alpha for reuse.

- `references/generated/environment_v025/potions/assets/minor_healing_potion_native.png`
- `references/generated/environment_v025/potions/assets/minor_mana_potion_native.png`
- Corresponding `_8x.png` files are pixel-preserving enlargements.
- `assets/manifest.json` records dimensions, native IDs and tile checksums.

Regenerate with `python3 tools/build_peon_potion_assets.py`. Run native checks
with `PYTHONPATH=/workspace/toolchains/pyboy-preview python3
tools/validate_peon_class_potions.py --section all`. The source, normal play and
diagnostic reports are saved separately in the same new potion evidence folder.
The diagnostic checks explicitly use private RAM/state fixtures for exhausted
slots, PP-Up flags, imported move order and full-health guards. Normal play uses
fresh class selection, naming, ordinary shop buttons, real enemy actions and
32 KiB battery restart; it does not edit a player's save.

## Final native validation

The full potion suite passes on candidate ROM SHA-256
`8b19628e4df259b96c4874b1220f238d7d166e6c05d136d7448c6ee9c77aaae8`.
All three fresh class routes pass native potion use, full-resource rejection,
25-copper shop purchase, exact icon VRAM/RGB555 checks and independent 32 KiB
battery restart. Shaman and Warlock spend and refill their actual starting
spell charges; Warrior's mana refusal spends neither item nor enemy turn.
Warrior uses the real armored scorpid for its potion checks because its melee
strike can defeat the level-one tutorial boar before taking damage. Caster
routes use the tutorial boar. Nine explicitly labeled private diagnostic
branches pass the charge/action-order/PP-Up and healing boundaries.

Reports are `source_validation.json`, `normal_validation.json`,
`diagnostic_validation.json` and `all_validation.json` under the potion evidence
directory. Each records the same final ROM checksum and a passing result.
