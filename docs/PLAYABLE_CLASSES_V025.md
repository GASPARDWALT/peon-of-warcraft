# Three playable class routes in v0.2.5

The Grommash Hold selection now accepts **Shaman**, **Warrior** and **Warlock**.
The selected master asks for the player's name. The actual persisted player
name is `Péon ` plus up to five chosen characters; no companion renaming prompt
is used. Each route arrives at The Den and uses the same finite quest chain,
hearthstone, inns, vendors, map discovery and save slot.

## Initial kits and actions

| Class | Story equipment | Initial actions | Supplies |
|---|---|---|---|
| Shaman | Crude Mace, Wooden Shield, Apprentice Totem | Mace Strike, Lightning Bolt | Earth Totem, 2 Heal Potions, 1 Mana Potion |
| Warrior | Crude Axe, Wooden Shield | Melee Strike, Weapon Strike | 2 Heal Potions |
| Warlock | Worn Staff | Melee Strike, Shadow Bolt | 2 Heal Potions, 1 Mana Potion |

The basic melee action remains unlimited. Mana potions restore the current
prepared spell-charge pools and do not work for Warriors. A Warrior's other
skills have their own charges in this prototype; there is no separate rage
resource. Initial axe/staff are real named key-item records with corresponding
native icons, rather than additional inventory or equipment slots.

Kento trains Shamans, MoCMoc Zogzog trains Warriors, and Xasthur trains Warlocks.
The other masters decline to train the selected class and cannot grant its kit.
Repeated trainer visits never recreate a character or restore charges for free.
Each trainer sells eleven lessons through level 20. The four native action
slots remain: two protected basics and two selectable trained skills. Owned
lessons can be prepared again without charging copper, with destination
charges retained and capped; this is not a free mana refill.

The character sheet displays the actual class, HP and prepared actions. All
classes retain the same seven Start-menu entries and fixed panel geometry.
The backpack's story-equipment header displays the axe or staff instead of
inventing a Shaman totem for the other classes. Their weapon palette uses a
separate BG palette from the hearthstone icon.

## Save compatibility

No native party, WRAM or SRAM record is enlarged. There is still one actual
character actor, four prepared actions and one real 32 KiB battery save.

`EVENT_PEON_SHAMAN` keeps its original numeric index and historical engine
meaning: it identifies a completed Peon intro. It is set for **all three**
routes so existing map/battle/menu gates keep working. New reserved bits
`EVENT_PEON_WARRIOR` (318) and `EVENT_PEON_WARLOCK` (319) distinguish the new
classes. An existing Peon save with neither new class bit remains a Shaman.
The 22 new lesson ownership bits occupy previously unused indices 320–341;
all earlier flag indices and the 2,048-bit allocation remain unchanged.

Axe and staff alias previously unused item IDs 6 and 56. Existing item IDs,
move indices, move record count and save layout remain unchanged. The class
implementation does not renumber map or object IDs. The separate Valley
layout appends five maps and moves quest actors while retaining their saved
quest/death flags; see [VALLEY_SEVEN_ZONE_LAYOUT_V025.md](VALLEY_SEVEN_ZONE_LAYOUT_V025.md).
The Shaman's established moves, names, affinity and
trainer ownership remain intact. New class affinities are applied only to
battle state, not to a larger or rewritten saved species record.

## Classic inspiration and explicit adaptations

Six English WoWhead Classic pages were fetched successfully on 12 October
2026: [Heroic Strike](https://www.wowhead.com/classic/spell=78/heroic-strike),
[Rend](https://www.wowhead.com/classic/spell=772/rend),
[Shadow Bolt](https://www.wowhead.com/classic/spell=686/shadow-bolt),
[Drain Life](https://www.wowhead.com/classic/spell=689/drain-life),
[Corruption](https://www.wowhead.com/classic/spell=172/corruption) and
[Fear](https://www.wowhead.com/classic/spell=5782/fear). The fetch metadata and
source hashes are in
`references/generated/environment_v025/classes/wowhead_references.json`.
No third-party artwork, sound files or full spell descriptions were imported.

Skill levels, copper prices, turn behavior and charges are adapted for this
ROM. Fear reduces accuracy instead of forcing a scripted enemy to flee.
Bleed/curse damage uses the original single ongoing-status slot. Cleave and
Hellfire hit one foe. Additional Warlock pets, Warrior rage, actual Classic cooldowns,
separate class stat-growth curves and distinct class body-animation sheets
are future work. The shared Peon body remains the apprentice presentation.
Warlocks now have a native red imp companion. It follows in the world and
adds one Fire damage after a completed battle turn while both combatants
remain alive. This is a small companion mechanic, not a full pet-control or
summoning system; see [WARLOCK_PET_V025.md](WARLOCK_PET_V025.md).

Full native effects, ability tables and animation details are in
[CLASS_SPELLS_V025.md](CLASS_SPELLS_V025.md).

## Reproducible validation

`tools/validate_peon_class_routes.py --section normal --expected-sha HASH`
uses ordinary buttons to create all three classes, enter an actual player
name, verify kits and wrong-master refusal, open the native character sheet,
pay for level-2 training, fight the first boar, return the quest for XP, rest
at an inn, revisit the trainer and cold-restart an actual 32 KiB save. The
normal route does not write game RAM or load emulator states.

`--section trainer` separately labels disposable level/money RAM fixtures for
22 later lesson gates: below-level and insufficient-copper refusal, purchase
cancellation, correct price, ownership, and protection of basic actions.
This does not claim ordinary gameplay progression to level 20.

`tools/validate_peon_class_spells.py` exercises native menu casts, affinity,
paired charges, status effects, drains and animations in its explicitly
labelled battle diagnostics. Results belong under
`references/generated/environment_v025/classes/` and are only accepted when
the reports pass against the exact packaged ROM hash.
