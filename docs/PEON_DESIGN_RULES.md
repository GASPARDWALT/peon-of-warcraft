# Peon of Warcraft design rules

This is the implementation contract for adapting the Crystal engine to a
Warcraft Classic adventure. Engine identifiers can remain stable internally;
the playable presentation must use the rules below. The audit notes at the
end describe the source as inspected before the vocabulary cleanup, not a
claim that every proposed substitution already exists in the ROM.

## Setting, characters and geography

- Use English dialogue and WoW Classic-era Durotar as the reference. The user’s
  custom opening, apprentice story and three class masters remain deliberate
  additions: Kento Brandenhoof, MoCMoc Zogzog and Xasthur.
- The protagonist is a humble green-skinned orc peon, then a Shaman apprentice:
  crude one-handed mace, wooden shield and belt totem. No heroic helmet, cape
  or giant shoulder armor in the starting appearance.
- Kento asks the name after accepting the apprentice. Dialogue addresses the
  saved `Péon <name>`; never silently replace the player’s chosen name.
- Sen’jin is a Darkspear settlement with trolls, coastal huts and palms.
  Razor Hill is an orc outpost with guards, vendors and fortifications.
  NPC names/roles must come from verified Classic data or be explicitly
  generic prototype roles; original short dialogue must not be described as
  a verbatim WoW export.
- The main route links the Valley/Den western branch, Sen’jin to the south,
  Razor Hill to the north and Orgrimmar Gate farther north. Preserve this
  orientation in directions, atlas screens and path design. Echo Isles and
  the Orgrimmar interior must remain clearly outside the current build.
- Give every implemented zone a readable main path and distinct landmarks.
  Side areas may invite exploration, but walls, water, NPCs and decorations
  must not block a required route, entrance or return location.
- A building drawn with an active door must be enterable. Shared interiors
  are acceptable when the exit returns to the particular door used to enter.

## Art and native rendering

- Use the Pokémon Crystal level of pixel readability with Warcraft subjects:
  strong silhouettes, intentional single pixels and simple color clusters.
  Do not use recognisable Pokémon species, trainers, capture balls or consoles
  as playable Warcraft props.
- Export sprites as PNG with a genuinely transparent background. Keep native
  files separate from enlarged previews and large concept art. Put generated
  visual files below `references/generated/` with clear names.
- Current native limits are 16×16 overworld sprites, 56×56 battle fronts and
  48×48 battle backs. Overworld object palettes allow three visible colors
  plus transparency. A detailed concept sheet does not bypass these limits.
- Preserve equipment handedness in the player’s independent left/right
  frames. NPC role sheets may be shared, but document shared art rather than
  implying that every named NPC has a unique atlas.
- Ground and structural art must support navigation: Durotar ochre rock,
  cliffs, sparse brush/cacti, Darkspear timber/straw and Horde palisades.
  Distinct regional tints must keep sprites and exit tiles visible.
- Yellow-bordered boars are neutral and begin combat only on interaction.
  Red scorpids and red imps are hostile. Spell and melee effects must have
  short readable anticipation, impact and recovery without covering dialogue.

## Gameplay and economy

- The current single Crystal character/save allocation is the compatibility
  boundary. Adding fields, changing map/item indices or replacing storage
  requires an explicit migration design and cold-restart verification.
- Use CHARACTER, BAGS and MAP as the playable systems. Creature collection,
  catching, Pokédex completion, gym progression and Pokémon party swapping
  are not player-facing objectives.
- Mak’gora Proofs replace badge terminology in the design. They are a custom
  progression record for victories in future duels/challenges, not an existing
  WoW Classic inventory item. Do not award proofs for unrelated ordinary kills
  or imply that proof encounters already exist when none are scripted.
- Do not automatically inherit Crystal badge stat boosts, obedience checks or
  field-move gates from proof storage. If old badge bits are reused, each old
  dependency must be deliberately removed or replaced and verified.
- The current real equipment slot is the weapon. The wooden shield and totem
  are starter story equipment. Displaying armor slots must not imply functional
  armor calculations until they are implemented.
- Inventory capacity currently progresses through 6, 12 and 20 item stacks.
  Count stacks consistently, preserve existing contents on upgrades and refuse
  purchases safely when capacity is full. This is prototype progression, not
  the capacity of identically named Classic bags.
- Gray = poor, white = common, green = uncommon, blue = rare. A name copied
  from Classic must use its verified quality if the catalog claims accuracy;
  custom balance/rarity must be described as an adaptation.
- Vendor prices must be verified. The implemented offer is five Refreshing
  Spring Waters for 25 copper at Duokna, K’waii and Jark. Reputation discounts,
  buyback, selling and complete Classic stock are separate features.
- The mana model currently uses individual spell charges stored in Crystal PP.
  Refreshing Spring Water restores ten Lightning Bolt charges, capped at thirty.
  UI descriptions must match that behavior; do not claim a mana pool or a
  fifty-health heal for this item.
- The map is earned after Gornek’s second quest. Select and Start → MAP open
  the atlas. Fog currently hides entire undiscovered regions; visiting one
  reveals that region. Do not label this as tile-by-tile exploration.

## Dialogue and interfaces

- Keep every map dialogue row within eighteen rendered columns, including
  expansion of the longest saved player name. Use paragraphs for breathing
  room; do not shrink or clip text to fit a box.
- Check the actual width of each menu: item names allow twelve characters,
  but narrow start-menu labels need their own width budget. CHARACTER needs
  a menu wide enough for its nine letters plus the selection cursor.
- Use precise effects and quantities in item descriptions and rewards.
  Showing a renamed item while retaining a Pokémon-specific or inaccurate
  description is an incomplete conversion.
- Apply the same vocabulary to help descriptions, battle submenus, save
  summaries, empty-bag states and option-enabled help panels, not just titles.

## Vocabulary contract

| Legacy player-facing concept | Warcraft presentation | Implementation note |
| --- | --- | --- |
| Pokédex | CHARACTER | Inspect the peon and equipment; no collection count |
| Pokémon party | SELF / CHARACTER | A single apprentice in this build |
| Trainer card | CHARACTER | Health, level, class and equipment |
| Badges | MAK'GORA PROOFS | Fifteen-character title fits an eighteen-column panel |
| Pokégear / Town Map | MAP / DUROTAR MAP | Current region atlas, not all Azeroth |
| Pack | BAGS | Actual stack capacity and usable/equippable items |
| Pokémon moves | SPELLS / ATTACKS | Lightning Bolt, Mace Strike, enemy abilities |
| PP | CHARGES | Current mechanic; do not falsely label it a shared mana pool |
| Pokémon types | DAMAGE / SCHOOL | PHYSICAL, NATURE, FIRE and creature-family labels |
| Fainted | DEFEATED / KNOCKED OUT | Context-dependent; no creature catching |
| Gym leader | CHALLENGE MASTER | Reserved for future scripted proof encounters |
| Inherited ¥ money label | COPPER | Verified vendor price unit |
| PC storage / creature boxes | STASH, if implemented | Do not show an inactive stash as usable |

## Obtainable item audit and exact short descriptions

The route currently gives or sells only the following item IDs. Native names
already fit twelve characters. The two-row descriptions below are proposals
for the cleanup; each row fits eighteen columns. No extra item effects or
catalog size are implied by this table.

| ID | Current short name | Proposed description row 1 | Proposed description row 2 |
| --- | --- | --- | --- |
| `ITEM_19` | CRUDE MACE | A crude peon mace. | Starting weapon. |
| `ITEM_2D` | WOOD SHIELD | A wooden shield. | Apprentice gear. |
| `ITEM_32` | APP. TOTEM | An apprentice's | small belt totem. |
| `FRESH_WATER` | SPRING WATER | Restores ten | Lightning charges. |
| `ITEM_5A` | DUROTAR MAP | SELECT: zone map. | Explore to reveal. |
| `ITEM_64` | SMALL POUCH | Holds twelve | item stacks. |
| `ITEM_78` | LEATHER BAG | Holds twenty | item stacks. |
| `ITEM_87` | CRACKED MACE | Equip: melee | damage up 5%. |
| `ITEM_88` | WORN MACE | Equip: melee | damage up 10%. |
| `ITEM_89` | BARBED CLUB | Equip: melee | damage up 20%. |
| `ITEM_8D` | SHAMAN MACE | Equip: Nature | damage up 30%. |

Classic item 36, Worn Mace, is **white/common**, not gray. If the prototype
keeps `ITEM_87` gray, use a clearly custom short name such as `CRACKED MACE`
(twelve characters), and reserve `WORN MACE` for the white slot if desired.
Do not present the existing twelve-slot SMALL POUCH as Classic’s six-slot
Small Brown Pouch, or the twenty-slot LEATHER BAG as the eight-slot Brown
Leather Satchel. The current short labels describe custom prototype upgrades.

## Concrete cleanup findings from the inspected source

1. `FreshWaterDesc` still says `#MON` and fifty HP, while the reachable custom
   inventory consumes water to restore ten spell charges. Replace that text.
2. Equipment/bag descriptions at `TeruSama7Desc`, `TeruSama8Desc`,
   `TeruSama9Desc`, `TeruSama10Desc`, `TeruSama11Desc` and `TeruSama12Desc`
   still contain `?`. Give implemented items their actual effects/capacities.
3. The start-menu help panel can expose `Party <PKMN> status` when the menu
   account option is enabled. Replace it with `Character` / `equipment` and
   replace MAP's inherited `Your own status` with `Durotar` / `region atlas`.
4. Battle SELF still opens Crystal's party-switch/stat interface. Route it
   through the custom character view, or deliberately convert every reachable
   subpanel; a new top-level SELF label alone does not complete the conversion.
5. Depleted-spell battle text still says PP. Use CHARGES in the actual message
   and shorten/wrap it to preserve the battle text box.
6. No proof is awarded by the current opening, Gornek, Galgar, village NPCs or
   imp encounters. Original trainer-card badges are not in the intended menu
   route. A proof count/panel must accurately show this absence of progression.
7. Dormant original item tables still include balls, apricorns, Pokémon mail,
   Rare Candy, TM/HM and species-specific descriptions. They are not obtained
   on the supported peon route. Keep them inaccessible; if legacy inventory
   imports are supported later, explicitly filter/migrate such IDs instead of
   merely relabeling a capture mechanic as a Warcraft item.

Sources for canonical NPCs, vendor offers and item qualities are listed in
`docs/WOW_CLASSIC_REFERENCES.md` and `docs/DUROTAR_VILLAGE_NPCS.md`. ROM-level
validation must separately verify text fit, equipment effects, inventory
capacity, vendor refusal paths, region transitions and save/cold restart.

## v0.2.1 cleanup implemented

CHARACTER now fits its widened Start panel. Reachable help and SELF use the peon presentation. Spring Water and weapons have accurate descriptions; use during battle synchronizes charges and the weapon with the active combatant. Mak'gora Proofs are shown as zero earned: no duel progression is implemented yet. Gray loot is CRACKED MACE; white loot is WORN MACE.
