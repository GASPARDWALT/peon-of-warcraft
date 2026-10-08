# v0.2.3 combat movement and balance

This patch keeps the existing Shaman chapter and native save layout. Its scope
is movement by the apprentice during battle and a modest adjustment to combat
attrition. Published v0.2.2 art, reports and downloads remain unchanged.

The design target is that two ordinary enemies at the apprentice's level are
survivable with little health left. A third should usually require recovery,
such as an appropriately timed potion. Different native RNG sequences,
critical hits and poison matter; an exact remaining-HP number is not promised.
The final `combat_balance/validation.json` records measured outcomes and the
method used, rather than treating a single lucky battle as balance evidence.
The complete 99-series matrix and measured outcomes are documented in
`V023_COMBAT_BALANCE.md`.

The existing complete quest test deliberately visits inns and gains several
levels before the road pack. It verifies progression and persistence, but
cannot establish equal-level attrition by itself. A shorter ordinary-button
route can reach the two level-four road scorpids at level four:

`New Character → Cutting Teeth → inn → Den scorpid → Gornek → inn → road pack`

The second kill can increase the apprentice's level. Measurements must
account for that maximum-health increase. Separate repeated-enemy diagnostics
must clearly identify any temporary battle fixtures or restored world state;
they do not represent a normal infinite respawn loop in the game.

The ordinary-button route won both level-four scorpids on the final ROM,
starting at 19/19 HP and finishing at 14/22 HP after reaching level five.
Subtracting the three HP gained with that level leaves 11/19 HP. This sample
is comparatively safe; it complements the broader attrition matrix rather
than establishing that every pair leaves the apprentice barely alive.

Movement must preserve the player's actual palette, front/back picture,
equipment and rank overlays, fonts, health and charge displays. Opening BAGS,
cancelling an action and returning to the battle menu must restore the normal
view. The mandatory `player_combat/validation.json` contains native-renderer
evidence and methods on the exact packaged ROM.

Starter money can buy two 25-copper, 20-HP potions, or Rockbiter training and
one potion. Inns deliberately restore health and charges. Ordinary enemies
remain finite, quest rewards are one-time, and victories do not heal for free.
The patch adds neither simultaneous group combat nor additional saved attack
slots. One real save and four prepared attacks remain; the reusable Earth
Totem stays a battle BAGS action.

All previous runtime checks must run again against the final v0.2.3 hash.
Save-upgrade tests include the published v0.2.2 ROM alongside v0.1.1, v0.2 and
v0.2.1. The v0.2.2 character already owns the reusable totem, so Kento must not
duplicate it. Older characters retain the one-time inventory-guarded handoff.
Physical Chromatic, cartridge flashing and RTC testing remain separate.
