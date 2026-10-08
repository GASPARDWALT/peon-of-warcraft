# Durotar v0.2.2 encounters and quests

The new encounters are visible, finite world actors. Yellow-outlined tigers and
coastal crawlers require A and confirmation; red-outlined raptors, harpies,
Sarkoth and cavern enemies also engage on the four adjacent approach tiles.
Defeated actors disappear immediately and remain absent after map transitions
and a real battery-save restart. At level 4 a red Road scorpid pack becomes
visible at (16,16): two consecutive native 1v1 fights without healing between
them. If the second fight is lost, the first kill remains saved and does not
repeat. Only finishing the pack hides it and awards its 40 copper. This is not
a simultaneous multi-enemy battle. Victory alone records a kill. Running away or
losing leaves the actor alive. Defeat returns the apprentice to the bound inn,
falling back to The Den when unbound, with one HP and harmful status cleared;
it does not heal the party. Overworld poison collapse uses the same destination
rule. Ordinary victories yield 20–35 copper without
repeated weapon drops. Inns provide deliberate health and charge recovery.

## Quest progression

Each giver offers one quest, with a persistent marker: yellow ! available,
gray ? accepted but incomplete, yellow ? ready, then no marker after turn-in.
A and the marker itself both open the appropriate giver's conversation.
Successful first turn-ins also award quest XP through the shared native
progression helper, preserving wounds, statuses and spell charges. Proof
recovery, full-bag retries and repeated thanks grant no XP. The exact XP curve
and per-quest awards are documented by the progression implementation.

| Quest | Giver and world tile | Objective | One-time reward |
| --- | --- | --- | --- |
| Cactus Apple Surprise | Galgar, Valley (8,10) | Harvest the three marked cacti | Leather Bag, 50 copper |
| Sarkoth | Hana'zua, Valley (10,19) | Kill Sarkoth (16,20), return his claw | Two Healing Potions, 100 copper |
| Burning Blade Medallion | Zureetha Fargaze, Valley (6,11) | Kill Yarrog (14,3) in the cavern, return his medallion | Green Spirit Mace, 150 copper |

Harvested cacti visibly disappear, and the saved harvest flags apply the same
terrain changes on subsequent map loads. Rewards are retryable when bags are
full: completion and copper are only recorded after successful delivery. A boss
killed before accepting its quest still counts. If its proof could not fit in
the quest pouch, the giver can recover it after space is made. A completed quest
cannot deliver the reward again. Spirit Mace improves Nature damage by 20%; it
must be equipped through Bags. Its exact bonus is supplied by the native item
and battle equipment implementation, not by the quest script.

## Encounter placement

| Map | Actor | Tile | Behavior | Level / copper |
| --- | --- | --- | --- | --- |
| Valley | Sarkoth | 16,20 | Hostile | 4 / 35 |
| Cavern | Vile Familiar | 8,10 | Hostile | 2 / 20 |
| Cavern | Strong Familiar | 12,8 | Hostile | 3 / 30 |
| Cavern | Felstalker | 5,6 | Hostile | 3 / 25 |
| Cavern | Burning Blade Cultist | 5,3 | Hostile | 3 / 25 |
| Cavern | Yarrog Baneshadow | 14,3 | Hostile | 4 / 35 |
| Road | Tiger | 5,5 | Neutral | 3 / 20 |
| Road | Raptor | 18,8 | Hostile | 3 / 25 |
| Road | Harpy | 5,22 | Hostile | 3 / 25 |
| Road coastal branch | Crawler | 18,23 | Neutral | 3 / 20 |
| Road | Scorpid pack | 16,16 | Hostile, visible from level 4 | Two level 4 fights / 40 total |

The Den's encounters and early quest chain are maintained separately. World
navigation keeps all prior exterior warps, nine building entrances, cactus
positions and existing NPC coordinates. The southern Valley fork now clearly
leads from Hana'zua into Sarkoth's basin. The Road gains an eastern beach branch
for the crawler, while retaining its main north/south canyon route. More
campfires, Horde banners and short palisades identify camps and canyon exits.
Native art
remains at 192 background tiles; the two new inn furniture blocks reuse those
tiles. Every walkable bare-ground block uses ID 38 because Crystal treats block
ID zero as impassable before consulting its collision table.

## Classic references and prototype adaptations

The names and objective relationships are based on WoW Classic quest 790
(Sarkoth: bring Sarkoth's claw to Hana'zua) and quest 794 (Burning Blade
Medallion: bring the medallion to Zureetha Fargaze). The medallion drops from
Yarrog Baneshadow. References were verified in the public Questie v8.8.2 data:

- [Classic quests](https://github.com/Questie/Questie/blob/v8.8.2/Database/Classic/classicQuestDB.lua): IDs 790 and 794.
- [Classic NPCs](https://github.com/Questie/Questie/blob/v8.8.2/Database/Classic/classicNpcDB.lua): Hana'zua 3287, Sarkoth 3281, Zureetha 3145, Yarrog 3183.
- [Classic items](https://github.com/Questie/Questie/blob/v8.8.2/Database/Classic/classicItemDB.lua): Sarkoth's Mangled Claw 4905, Burning Blade Medallion 4859.

These are shortened original English conversations for the 18-column GBC text
box. Geography, reward amounts, enemy levels, Spirit Mace and the reduced
prerequisite chain are explicit prototype adaptations, not exact Classic data.
Classic's Vile Familiars quest (792) asks for twelve kills before the medallion
quest; this build uses a short finite cavern and directly offers the boss quest.

## Save scope and limitations

New state occupies previously unused event bits; existing item indexes, party
layout and the single real Crystal save slot remain intact. Saves from v0.2.1
have the new flags unset and can start these quests. There is no time-based
respawn in v0.2.2, no full Classic spawn population, no Echo Isles crossing and
no full Orgrimmar interior. Physical Chromatic testing remains separate from
normal-button emulator validation.
