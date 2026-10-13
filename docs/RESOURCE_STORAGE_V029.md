# v0.2.9 resource storage and native validation

This module and its native hooks are integrated in the v0.2.9 candidate. They are absent from the published v0.2.8 ROM. The frozen candidate07 resource regression passes for ROM SHA-256 `4530c718bf299ec9e1c8de8c52895906a81024345bd60717cd5c99dbd30b8a93`; [validation.json](../references/generated/resources_v029/runtime/validation.json) records the exact ROM hash, ordinary play evidence and separately labelled diagnostic fixtures. A later build must rerun this regression against its own frozen ROM hash.

`engine/battle/peon_resources_v029.asm` keeps the original 48-byte party record. Byte 28 (`MON_POKERUS`) is the unique cured marker `$80`; bytes 29–30 (`MON_CAUGHTDATA`) hold the unsigned current resource in **big-endian** order. Mana maximum is derived from class/level; rage maximum is 100. The five unsaved working bytes occupy exactly `$CFFB..$CFFF`, following TEAM's `$CFF2..$CFFA` and the text cache's `$CFD8..$CFF1`.

Resource classes are MACHOP in hero slot zero (class event bits), ONIX for Earth Spirit/Shaman, GEODUDE for Imp/Warlock and MACHAMP for Orc Recruit/Warrior. MACHOKE remains Yarrog. Indices outside the first three and other species are not converted. The guard also requires the Peon tileset and completed class initiation.

Shaman maximum is `48 + 12 × level`; Warlock maximum is `60 + 15 × level`, with level clamped to 1–100 and the resulting pool capped at 999 to fit the fixed three-digit UI. These are prototype balance curves, not exact Classic racial/Intellect formulas. The first initialization fills caster mana or starts Warrior rage at zero. Once `$80` exists, repeated map setup, Continue or trainer visits **do not refill the resource**. Current values are only clamped if above the derived maximum. Normal heals at the inn may explicitly refill the party's mana and clear rage.

## Farcall-safe APIs

Native `farcall` replaces A with the bank number; `ReturnFarCall` preserves BC/DE/F but leaves A equal to C. Passing or reading A as a farcall result is unsafe. The `InAV029` variants are private same-bank CALL entry points.

| Public helper | Input | Reliable output |
| --- | --- | --- |
| `PeonResourceModeEnabledV029` | None | Carry if resource mode is enabled |
| `PeonResourceClassForIndexV029` | C = index | Carry managed; B = class, C unchanged; class also at `wPeonResourceClassV029` |
| `PeonEnsureResourceForIndexV029` | C = index | Carry managed; B = class, C unchanged; class also at `wPeonResourceClassV029` |
| `PeonGetResourceForIndexV029` | C = index | Carry managed; BC = current, DE = max; class in `wPeonResourceClassV029` |
| `PeonRestoreResourceForIndexV029` | C = index, DE = restoration amount | Carry only when a living caster actually regains mana; no inventory change |
| `PeonRefillResourceForIndexV029` | C = index | Carry managed; full mana or zero rage |
| `PeonEnsurePartyResourcesV029` | None | Void, initialize eligible records without appending members |
| `PeonRefillPartyResourcesV029` | None | Void, refill eligible current records |
| `PeonCanAffordBattleMoveV029` | Selected `wCurPlayerMove` | B = 0 unmanaged or 1 managed; carry = managed and affordable |
| `PeonSpendBattleResourceV029` | Actual `wCurPlayerMove` | B = 0 unmanaged, 1 authorized, 2 defensive shortage; carry means bypass native PP |
| `PeonPrintMoveResourceCostV029` | Highlighted `wCurPlayerMove` | Carry handled; five-cell `15/MP`, `15/RG` or `--/--` |
| `PeonPrintResourceForIndexV029` | C = index, DE = destination in `wTilemap` | Carry drawn; exactly nine regular-font cells `MP###/###` or `RG###/###` |
| `PeonDrawCharacterResourceV029` | None | Hero slot-zero readout at (10,7), nine cells |
| `PeonDrawBattleResourceV029` | None | Current active battle actor's readout at (1,9), nine cells |
| `PeonCheckResourceMovesUsableV029` | None | B=0 unmanaged; B=1 managed, C=1 usable / C=0 none; legacy PP unchanged |
| `PeonResourceWalkingStepV029` | Completed native player step after incrementing `wStepCount` | Void; preserves BC/DE/F and the caller bank; standard farcall A clobber applies |
| `PeonTryUseMinorManaV029` | Battle active actor, or TEAM field target | Carry restored; no item consumption in helper |
| `PeonTryDrinkWaterV029` | TEAM target, outside combat only | Carry restored; no item consumption in helper |
| `PeonTryUseMinorHealingV029` / `PeonTryEatMeatV029` | Active actor in battle or TEAM field target | Carry restored; synchronization uses the selected party record |
| `PeonResourceTagIsMetadataV029` | `wCurPartyMon` | Carry if this actual supported actor's `$80` byte is our metadata |

Public entry points select WRAM1 for party records/event flags and restore the caller's exact SVBK afterward. The Get API only guarantees its values when carry is set. Its class transient is valid only on that same successful call.

Availability is checked before a player commits a move; insufficient mana/rage returns to move selection without consuming a turn. Spending occurs after native inability/charging/continuous-action guards. Missed or resisted casts still cost mana; an actor prevented from acting by sleep, freeze or flinch does not cast and does not pay. PP bytes remain in their original record positions as inert legacy data. The managed usability scan bypasses the old mace-charge refill and does not replenish battle or saved PP. Free basic attacks remain available; native PP checks remain intact for unmanaged actors and opponents.

The character card always describes hero record zero; a battle ally's HP must not replace the hero's HP there. The battle info panel displays the active actor's current/max pool on row nine, its move type on row ten and the highlighted cost on row eleven. These readouts preserve the original box dimensions and move-list coordinates. TEAM has three separate nine-cell readout rows. No additional world OAM gauge is introduced by this module.

Automatic outside-combat recovery occurs on every fourth **completed player walking step**: living casters regain two mana and living Warriors lose five rage, bounded by zero and their current maximum. The existing native `wStepCount` schedules this; NPC movement, waiting, menus, readouts, map loads and Continue do not trigger ticks. This is a custom step-based approximation and does **not** implement Classic's timed five-second rule. A failed movement into a wall does not count as a completed step.

Rage gains are prototype constants: eight on a successful free Warrior basic hit, five on direct enemy damage taken, capped at 100. Paid Heroic Strike does not also earn the free attack's gain. The original vanilla damage/level conversion was not reproduced. Water restores 60 mana and the minor mana potion 40 in the prototype's scale. Healing potion restores 20 HP and Tough Jerky ten HP. Water/meat refuse combat; resource restoration refuses dead/full/Warrior targets. These are explicit prototype amounts, not a claim of equal Classic item units.

## Original semantics that change

The complete read/write inventory is in [storage_audit.json](../references/generated/resources_v029/storage_audit.json). Two native gameplay guards are necessary:

1. `GiveExperience` tests **any** nonzero Pokerus byte when doubling stat experience, including cured `$80`. The resource tag must be treated as zero in this path. Skipping viral spread alone is insufficient.
2. `LevelUpHappinessMod` compares the old caught-location byte with the current landmark. That byte is now the resource's low byte; it must not grant a false at-home happiness bonus to a managed actor.

`InitBattleMon` and `InitEnemyMon` explicitly skip the three Pokerus/CaughtData bytes before copying level/status/stats, so resource data is not accidentally imported into the battle struct. HP/move/PP synchronization does not overwrite these metadata fields. `ApplyPokerusTick` skips low-nibble-zero markers; `_CheckPokerus` detects only an active low nibble. The existing Peon victory path skips viral acquisition/spread. The marker is deliberately `$80`, never active `$81`.

Native creation writes zero metadata, and capture/gift adapters write catch information. **Resource initialization must run after the last catch/gift metadata write**, never before it. TEAM's starter Imp follows this order. Naming and OT/nickname buffers are separate from these three bytes; deterministic role naming does not rename or overwrite the resource.

The original capture time/level/landmark/caught gender are no longer meaningful for resource-tagged actors. Original Pokémon stats screens could interpret `$80` as an immunity dot or resource bits as caught gender; Seer/trade/daycare/breeding/PC workflows have their own interpretations. These workflows are excluded from the prototype's authored maps and menus; retaining their unused source does not establish compatibility with them. This is not a general-purpose Crystal party-storage extension.

Existing v0.2.8 one-hero saves can receive the marker once without moving record addresses, saved IDs or event indices. **Format compatibility does not mean safe downgrade:** opening a tagged v0.2.9 save in v0.2.8 would re-enable the old nonzero-Pokerus stat-experience behavior. Forward migration, actual cold battery restart, no refills on repeated initialization and full record comparisons must be tested on the integrated native ROM before publishing.

TEAM's field target picker changes the full graphics state, so every field success/refusal/cancellation redraws `PeonInventory.redraw_frame` (frame, font, palette and item icon). Refusal reasons are printed after restoring that frame and its body, preserving the selected inventory entry. Battle supplies target the current active party member and retain the native one-action item flow.

## Verified on frozen candidate07

`tools/validate_peon_resources_v029.py --rom <frozen-ROM> --symbols <matching-SYM> --expected-sha256 <ROM-SHA256> --diagnostics` uses private battery files. Ordinary routes forbid emulator RAM writes and save-state loads. They select each of the three classes through the intro, buy supplies and lessons with real copper, fight the real boar/scorpid, use the actual Bags/TEAM target picker, turn in the first quest, revisit the master, rest at the inn and reopen an actual 32,768-byte battery save.

The ordinary checks verify real 15-mana Lightning Bolt, 25-mana Shadow Bolt and 15-rage Heroic Strike payments, zero-rage refusal without a turn or HP/PP/item loss, one enemy reply per successful battle potion, combat refusal of food/water, field cancellation/full-target refusal, and unchanged legacy PP bytes. Completed-step snapshots verify the exact four-step recovery schedule and prove it changes only the two resource bytes. Trainer waiting and repeated visits do not refill the pool or duplicate the kit; cold Continue preserves current resources and complete party records. The inn heals all present members, refills caster mana and clears rage.

Twelve settled move panels verify every one of the four actual move rows, including `MACE STRIKE`, `MELEE STRIKE` and `WAND STRIKE`. The nine-cell resource and five-cell price readouts are checked against the frozen ROM's regular-font packet, actual VRAM tiles/attributes and 10,752 rendered RGB555 pixels. Battle color setup publishes palette0 directly while `wAttrmap` retains palette7 staging; the harness checks both paths explicitly. Forty-five read-only resource-draw observations prove only the nine destination tile cells can change, while adjacent fields, attribute staging, both graphics banks, portraits and palette buffers remain intact. The native heading clears all nine cells before printing numbers so omitted leading blanks cannot leave the previous `TYPE/` label visible.

Separately labelled diagnostics alter only a disposable emulator instance to exercise zero mana, zero legacy PP, sleep-prevented casting and a ground-immunity cast. These verify no charge when the actor cannot act, one charge for an executed immune cast, and a usable free weapon with no mana or PP. Diagnostic fixtures are not presented as normal progression. Independent team/migration validation owns the genuine v0.2.8-to-v0.2.9 upgrade, recruitment and active companion switching.

Candidate01/02 captures are retained in folders labelled `preliminary_...`; they document earlier harness retries and visual failures and are excluded from the final visual proof. Native resources do not establish RTC accuracy on a physical cartridge or hardware performance on a Chromatic; those need the actual console/cart firmware.
