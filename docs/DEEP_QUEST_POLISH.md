# Valley quest progression and reward recovery

This patch builds on the published Warcraft audio preview (`1435e70`). Game
text remains English. It adds no party members, inventory allocation, map IDs,
respawn counters, save slots or new SRAM layout.

## Added playable links

Zureetha now offers **Vile Familiars** before **Burning Blade Medallion**.
The compact objective is four existing finite familiars: the two red imps at
the cavern entrance and the two imps inside. Classic's twelve-kill objective
is deliberately reduced to the four actual encounters available in this ROM.
A reminder displays the native count `Familiars: X/4.`. Kills already made
before acceptance count; nothing is respawned or erased.

The giver shows one quest at a time. Accepting familiars shows a gray `?`;
killing all four shows yellow `?`; turning them in gives 40 XP and 50 copper
once. The conversation ends after that reward. A subsequent conversation
offers the medallion with a yellow `!`, then the existing gray/yellow question
states. The last newly won familiar plays the ready sound only if the quest
is active, and never again after turn-in.

A published save which already accepted or finished the medallion bypasses
the new prerequisite. Its progress and four finite enemy flags are retained.
It receives no retroactive automatic familiars reward.

After Hana'zua's Sarkoth turn-in, he asks the player to report that he is alive
to Gornek. Gornek accepts this report after his existing Cutting Teeth/Sting
of the Scorpid chain is complete. Reporting gives 25 XP and 50 copper once,
without another quest item. Gornek's native marker and atlas objective show
that report as ready; repeated conversations cannot repeat any XP or money.

## Corrected reward failure

Gornek previously committed the map reward and then tried to give a club and
small pouch. A full pocket at either item could permanently strand that
optional reward because the next conversation skipped the whole handoff.

The map, XP and copper remain committed once. The club and pouch are now
independently retryable. A new saved club bit prevents repeated club handoffs;
the existing small-bag flag records the pouch. A published partial reward
which already has the club is recognized from its inventory, avoiding a second
club. Full ITEM and KEY_ITEM pockets are handled separately by the unchanged
native inventory functions. Unclaimed gear keeps Gornek's yellow `?` visible,
even if the Sarkoth report was already completed. Make room and return.

## Save constraints

Four symbols consume previously unused reserved event bits:

| Symbol | Decimal ID | Purpose |
| --- | ---: | --- |
| `EVENT_PEON_FAMILIARS_ACCEPTED` | 314 | Quest accepted |
| `EVENT_PEON_FAMILIARS_DONE` | 315 | Reward committed |
| `EVENT_PEON_SARKOTH_REPORT_DONE` | 316 | Report reward committed |
| `EVENT_PEON_GEAR_CLUB_GRANTED` | 317 | Partial equipment reward committed |

Every existing event ID is unchanged. The subsequent `const_next 600` remains
unchanged, as do `NUM_EVENTS`, the event array size and all SRAM allocations.
Gornek's marker keeps its existing object index and coordinates. Its fixed
hide-event becomes `-1`; the native callback derives visibility from the
existing quest states and pending reward state. Other actors, warps, cactus
coordinates and finite battle retirement flags keep their IDs.

## Verification

`tools/validate_peon_deep_quests.py` supports `--section normal`,
`--section diagnostic`, or `--section all`, and an optional `--expected-sha`.
All new evidence goes to `references/generated/deep_polish/quests/`.

The normal suite plays a fresh character with ordinary buttons and read-only
inspection. It completes the two Gornek quests, four actual familiar fights,
Sarkoth/report and the cavern boss route; checks native marker graphics in
VRAM, hardware OAM and actual RGB555 screen pixels; rewards and repeat
conversations; writes a real battery save; restarts the emulator cold; then
walks through defeated actors and proximity triggers without a new fight.

Explicit fault diagnostics are reported separately. They set pre-kill/old
quest flags and artificial full pockets only in a disposable fresh ROM copy,
then use ordinary giver interactions to test recovery. They do not constitute
proof that those synthetic starting states were reached through gameplay.
No user's save is opened. No CPU result substitution or emulator savestate
loads are used by either section.

The normal and diagnostic sections both passed against the final ROM
`704022c22c441944d13e3ff65950a971e5c7ead614a1ff0e1bba476c340bea2d`.
The normal run won ten native battles, verified six marker presentations in
actual hardware OAM/RGB555 pixels, and saved/reloaded the new event bits with a
32,768-byte battery file. All four familiar actors and cavern boss triggers
remained retired after cold restart. The recorded XP/copper deltas matched the
amounts above; repeated turn-ins left XP, copper, HP, status and charges intact.
The separate diagnostic section passed all four pre-kill/legacy/full-pocket
cases. Each report includes the exact ROM hash and distinguishes gameplay from
synthetic starting fixtures.

## Limits

This is a compact adaptation of the Classic chains, not a full reproduction
of WoW quest text, twelve-mob respawns or the Call of Earth ritual. The latter,
Thazz'ril's Pick and report quests toward Sen'jin/Razor Hill remain future
work. Physical Chromatic cartridge testing is still required.
