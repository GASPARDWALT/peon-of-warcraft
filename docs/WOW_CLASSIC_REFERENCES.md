# Classic reference data used for v0.2

Sources were checked using publicly accessible Git repositories. Direct Wowhead
and wiki HTTP requests were unavailable in this cloud environment. Source data
was not substituted with guessed vendor prices.

- [Questie v8.8.2 Classic database](https://github.com/Questie/Questie/blob/v8.8.2/Database/Classic/classicQuestDB.lua):
  788 Cutting Teeth, Gornek (3143), ten Mottled Boars;
  789 Sting of the Scorpid, ten tails, prerequisite 788;
  4402 Galgar's Cactus Apple Surprise, Galgar (9796), ten apples, prerequisite 788;
  792 Vile Familiars and 794 Burning Blade Medallion establish the cavern theme.
- [CMaNGOS Classic DB](https://github.com/cmangos/classic-db/blob/master/Full_DB/ClassicDB_1_12_1_z2815.sql.gz):
  Duokna (3158), General Goods, sells Refreshing Spring Water (159).
  Item BuyCount = 5, BuyPrice = 25 copper, SellPrice = 1 copper per unit.
  Galgar is entry 9796. Worn Mace (36) BuyPrice = 38 copper, SellPrice = 7;
  Small Brown Pouch (4496) has six slots and BuyPrice = 500 copper.

The ROM's shortened quests, custom bag progression, equipment damage bonuses,
rare-drop probability and starter story are adaptations. They should not be
presented as canonical Classic values. Duokna's single verified offer is used
instead of inventing a complete merchant stock. Ordinary NPC dialogue is newly
written around the verified quest names/objectives.

## Valley camp preparation (2026-10-08)

The retained CMaNGOS Classic SQL dump was checked again for Duokna's food:
item 4540, **Tough Hunk of Bread**, quality 1, BuyCount 5, BuyPrice 25 copper,
SellPrice 1 per unit. The `npc_vendor` record explicitly associates creature
3158 (Duokna) with item 4540. The ROM short name is `TOUGH BREAD`, internally
`PEON_CAMP_BREAD = ITEM_95`; existing item IDs are not shifted.

The prototype purchase matches that five-for-25-copper offer. Its immediate
capped 10-HP bag heal outside combat is an adaptation of Classic food
regeneration, not a claim to reproduce spell 433's healing over time. Two
additional camp merchant roles are generic prototype NPCs, not asserted
Classic named vendors. Minor Potions retain the existing prototype price.
