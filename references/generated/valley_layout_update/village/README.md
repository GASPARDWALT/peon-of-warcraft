# Camp population and supplies

This pass appends four actors to The Den, preserving the existing eleven actor
indices, coordinates, scripts, quest events and all warp coordinates. Duokna
now uses the existing native Orc Vendor graphics and portrait.

| Actor | Position | Actual service |
| --- | --- | --- |
| MoCMoc Zogzog | 3,13 | Warrior-master dialogue; Shaman route unchanged |
| Xasthur | 3,16 | Warlock-master dialogue; Shaman route unchanged |
| Horde Provisioner | 8,6 | Shared supply shop; original unnamed camp role |
| Camp Cook | 8,7 | Shared supply shop; original unnamed camp role |
| Duokna, existing | 14,9 | Shared shop with Water as the first/default choice |

Each shop offers Spring Water ×5/25c, Minor Potion ×1/25c, Tough Bread ×5/25c,
and Cancel. Water and bread base bundle prices and Duokna's Classic stock were
verified against the cached CMaNGOS Classic DB. Potion price is a prototype
price. All purchases confirm inventory capacity before charging copper;
insufficient funds and full bags leave items and money unchanged.

Bread aliases existing unused item95, heals up to ten HP only outside combat,
and is retained at full health. This instant effect adapts Classic timed food
regeneration; it is not Classic's exact 433HP/18s effect. The item helper,
name, description and native icon are integrated by the parent task.

The supply alcove opens one formerly blocked 2×2 terrain block, (4,3), as
plain floor. Separating merchants from the crowded middle prevents native
OAM clipping and live-object exhaustion. No other map outline is redesigned.

The existing Razor Hill guard remains actor6 at (14,8). Its horizontal radius
is one tile: (13,8), (14,8), (15,8). Doors and the main x12 lane remain open.
The patrol offers the same dialogue and does not attack the player.

The validator uses a temporary ROM copy, normal buttons and read-only hooks.
It checks actual allocated graphics, rendered portraits, native visible-OAM
rejection, class/inventory/quest preservation during master conversations,
purchases, cancel and insufficient funds, food with real combat injuries,
bounded movement, walked doors and battery save restart. The capacity-before-
charge rule is also checked in source; this normal route does not inject a full
bag fixture. No RAM writes or emulator save states are used.

The two merchants share one existing animation sheet rather than individual
new art. Warrior/Warlock rewards, training and class switching remain locked.
Full seven-region geometry awaits the user's definitive map trace.
See validation.json for the exact tested ROM SHA256 and outcomes.
