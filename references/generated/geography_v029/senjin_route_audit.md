# Sen'jin road audit for v0.2.9 planning

This is a read-only source and graph audit. **No native file changed, no build ran, and no new battle outcome was simulated.** Proposed changes below are not implemented. The source hashes and complete paths are in `senjin_route_audit.json`.

## What the existing route really does

DurotarRoad is 12×14 metatiles, or **24×28 walking cells** (16×16 pixels each), map 26/16. Entry from the Valley is **(4,14)**. Sen'jin warp is **(12,24)**, and Razor Hill is **(12,4)**. Sen'jin arrives at **(10,4)**, map 26/17.

All fresh hostile actors and their coordinate triggers can be avoided. A shortest safe route is **18 steps and zero fights**; the actual pale-road route is **24 steps and zero fights**. Thus the current two-scorpid pack does not guard the trip to Sen'jin. It sits east of the main road at **(16,16)**.

Safe shortest route:

(4,14) → (5,14) → (6,14) → (7,14) → (8,14) → (9,14) → (9,15) → (9,16) → (10,16) → (11,16) → (12,16) → (12,17) → (12,18) → (12,19) → (12,20) → (12,21) → (12,22) → (12,23) → (12,24)

Safe painted-road route:

(4,14) → (5,14) → (6,14) → (7,14) → (8,14) → (9,14) → (9,13) → (10,13) → (11,13) → (12,13) → (13,13) → (14,13) → (14,14) → (14,15) → (14,16) → (14,17) → (14,18) → (14,19) → (13,19) → (13,20) → (13,21) → (13,22) → (13,23) → (13,24) → (12,24)

The BFS uses the actual per-quadrant collision table, living actor occupancy and active coordinate triggers. Other destination warps are excluded. It assumes a fresh map, player level ≥4 and all retirement flags clear. No collision, battle or cartridge runtime claims are made beyond the source calculation.

| Encounter | Actor | Existing levels | Aggro | Saved retirement |
|---|---|---|---|---|
| Scorpid pack | (16,16) | 4, then 4 | Four adjacent cells, player ≥4 | DEAD=305; FIRST=306 |
| Raptor | (18,8) | 3 | Four adjacent cells | RAPTOR_DEAD=287 |
| Harpy | (5,22) | 3 | Four adjacent cells | HARPY_DEAD=288 |
| Tiger | (5,5) | 3 | Neutral; accept attack | TIGER_DEAD=286 |
| Crawler | (18,23) | 3 | Neutral; accept attack | CRAWLER_DEAD=289 |

The native species indexes are reused deliberately: scorpid `SANDSHREW`=27, raptor `TOTODILE`=158, harpy `SPEAROW`=21, tiger `MEOWTH`=52, crawler `KRABBY`=98. These are the custom Durotar adapters, not visual Pokémon to introduce into the game.

### Current pack persistence

- Loss/flee on member one: FIRST=0, DEAD=0; retry loads two members.
- Win one, then loss/flee on member two: FIRST=1, DEAD=0; retry loads only member two.
- Win two: FIRST=1, DEAD=1; actor disappears and revisits load zero members.

There is **no HealParty, HP reset or charge refill between the two fights**. Poison, HP and PP carry forward; legitimate native level-up HP increments can still occur. Each new kill rolls the existing rare-potion mechanism once, which does not heal automatically. The 40-copper pack reward occurs only after its final victory. Defeat leaves one HP, clears poison and returns to the bound home.

Sen'jin itself contains no hostile coordinate triggers. Its current inn door is **(15,5)** and is reachable from arrival without a fight. Healing belongs to the innkeeper's explicit rest action, not the road transition.

## Concrete changes to consider

### A. Put the existing pair on the clear main road

The southern main-road choke is the two-cell corridor at **(12,22)/(13,22)**. Adding those two pack trigger cells makes the painted-road journey encounter both level-four scorpids. The source graph confirms **two fights along the painted route**.

However, the western harpy pocket remains a valid alternative: **22 steps, one harpy fight**, then approach Sen'jin from the west. This is not a claim that the change forces two fights on every possible route.

The existing pack at (16,16) would be too far away to explain attacks from (12,22). Stage the visual actor near **(14,21)** and provide a clear road warning, or use a deliberate visible approach animation. A relocated NPC must be transiently hidden if an old Continue puts the player on its new coordinate; do not set DEAD merely to hide it. Keep all previously passable cells passable rather than sealing the harpy branch with new collision.

### B. Smallest extension for an uninterrupted third enemy

For a level-six milestone, follow the two existing scorpids with the existing harpy adapter at level four. Reuse **HARPY_DEAD=288** and the ordinary CANLOSE battle/reload/result pattern. Carry HP, status and charges straight through; do not call a rest helper. Commit the harpy flag and hide the harpy only on victory.

If the third fight is lost or fled, FIRST and pack DEAD stay set and HARPY_DEAD stays clear. The living harpy's own map actor is the retry location; the pack must not resurrect. A saved old harpy kill is skipped. This is a **mixed pair plus harpy**, not three scorpids or a multi-enemy battle. Set the last-talked actor safely before the third scene; avoid facing a pack object that was just deleted.

### C. A real two-or-three-scorpid pack

Reuse FIRST=306 and DEAD=305, and reserve two new aliases in the currently unused **349..599** event region only after root verifies the exact allocations. Do not insert numbered constants that shift later flags or extend SRAM.

- `SECOND`: the second member has permanently died.
- `TRIPLE_REQUIRED`: fixed once before member one, for example when starting at level ≥6.

TRIPLE_REQUIRED prevents a level-up or cold Continue changing the planned pack size mid-run. Legacy FIRST-only saves stay two-member packs. **Existing DEAD must always short-circuit the whole encounter**: an old completed two-member pack must not respawn because its new bits are clear.

On each victory, commit only that newly defeated member, roll its loot once, and immediately load the next living member with the same HP/status/PP. On a loss or flee, retain progress. Complete copper is awarded once at the final member. Suggested balance work: retain level 4/4 for the first road pair; simulate 5/5/6 for a later level-six triple independently for all three classes. Do not alter every scorpid globally to tune one road event.

## Save-safe art and paths

Preserve map IDs, dimensions, warps, actor IDs, species/item/event numbers and the 32 KiB save layout. Add red/ocher mountain silhouettes through existing wall art/palettes. Shape the pale route using FLOOR-to-FLOOR replacements along the recorded painted route. Keep the village arrival (10,4), inn door (15,5) and interior return doorway (5,7).

A strict two-fight minimum on every possible route requires addressing the live western alternative, not merely painting extra rocks. Add a second finite encounter on that branch or explicitly plan a save migration. Never silently convert formerly saved walking cells into walls.

## Native checks required before claiming this works

Run all three classes normally to Sen'jin. Test first/second/third loss and flee; cold batteries at each partial state; exact encounter loads; no HealParty between fights; no duplicate loot or completion copper; complete old saves skip all retired enemies. Check HP/status/PP at each next battle after legitimate level-ups. Continue from every moved-actor cell and each doorway. Recheck quest markers, follower, fonts, portraits, menus and collision.

Historical v0.2.3 evidence in `normal_pack_validation.json` showed an actual 4/4 pair with zero auto-heal, but this audit does **not** present those older battle numbers as v0.2.8/v0.2.9 balance results.

## Current collision sketch

`#` wall, `N` actor, `!` aggro, `W` other warp, `S` entry, `G` Sen'jin, `*` one computed safe route, `=` other painted road.

```text
               11111111112222
     012345678901234567890123
00   ########################
01   ########################
02   ##................######
03   ##................######
04   ####....####W.##########
05   ####.N..####..##########
06   ####..##..##==####..####
07   ####..##..##==####!.####
08   ####..##..##==...!N!####
09   ####..##..##==....!.####
10   ####....N.##==..##..####
11   ####......##==..##..####
12   ##......========########
13   ##......========########
14   ##..S*****##..==..######
15   ##....===*##..==!.######
16   ##..##...****.=!N!..####
17   ##..##......*.==!...####
18   ####....N.==*=====######
19   ####......==*=====######
20   ####..######*=..N=######
21   ####.!######*=..==######
22   ####!N!.####*=##==..####
23   ####.!..####*=##==N.####
24   ##..........G.####..####
25   ##............####..####
26   ########################
27   ########################
```
