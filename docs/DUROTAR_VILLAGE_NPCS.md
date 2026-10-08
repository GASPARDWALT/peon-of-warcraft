# Durotar settlement NPCs

The settlement pass populates four existing maps with eighteen interactable NPCs:
six in Sen'jin Village, six in Razor Hill, three on Durotar Road and three at
Orgrimmar Gate. Existing warp coordinates, discovery flags and each map's
first NPC position `(8,10)` are preserved. NPC approach tiles are reserved by
the terrain generator; standing NPCs keep the main road open.

## Sen'jin Village

| NPC | Classic entry | Position | Implemented role |
| --- | --- | --- | --- |
| Master Gadrin | 3188 | 8,10 | Village welcome and north-road directions |
| Master Vornal | 3304 | 6,12 | Shaman and cavern story hint |
| Bom'bay | 10578 | 14,10 | Dialogue and directions to Shul'kar's inn |
| K'waii | 3186 | 16,13 | Five Spring Waters for 25 copper |
| Sen'jin Watcher | 3297 | 6,16 | Friendly/hostile creature guidance |
| Vel'rin Fang | 3194 | 14,16 | Village/Echo Isles flavor dialogue |

## Razor Hill

| NPC | Classic entry | Position | Implemented role |
| --- | --- | --- | --- |
| Gar'Thok | 3139 | 8,10 | Main-route directions |
| Innkeeper Grosk | 6928 | 6,12 | Directions to the enterable Razor Hill inn |
| Jark | 3164 | 16,10 | Five Spring Waters for 25 copper |
| Orgnil Soulscar | 3142 | 8,16 | Burning Blade cavern hint |
| Thotar | 3171 | 16,16 | Hunter flavor and creature advice |
| Razor Hill Grunt | 5953 | 14,8 | Rest/vendor directions |

Lar Prowltusk (Classic entry 3140) guides the Durotar Road junction. A generic
Horde scout and patrol explain the coast and supplies. Three generic grunts
at Orgrimmar Gate explain that the city interior remains outside this build.

## Sources and adaptation limits

Names, roles and settlement spawn coordinates were checked against
[CMaNGOS Classic DB](https://github.com/cmangos/classic-db/blob/master/Full_DB/ClassicDB_1_12_1_z2815.sql.gz),
specifically `creature_template` and `creature`. K'waii and Jark both use
`VendorTemplateId = 1100`; `npc_vendor_template` 1100 includes item 159,
Refreshing Spring Water. Its verified base offer remains five waters for
25 copper, as in the existing Duokna implementation.

Dialogue is newly written in English and shortened for an eighteen-column
Game Boy text box. It is not a verbatim export of WoW quest dialogue. These
exact native-map positions and generic road/gate guards are prototype
adaptations. Exterior NPCs no longer restore health or charges for free.
This settlement pass does not add class training, full vendor stock,
reputation discounts, buyback, new quests, the Echo Isles or the Orgrimmar
interior.

Native art roles use reserved legacy sprite indices without inserting IDs:
`SPRITE_LINK_RECEPTIONIST` is the troll guard, `SPRITE_CLERK` the troll
villager/merchant and `SPRITE_SAGE` the troll caster, using `PAL_NPC_TREE`.
`SPRITE_OFFICER`, `SPRITE_GENTLEMAN` and `SPRITE_BLACK_BELT` are the orc
guard, merchant and questgiver roles, using `PAL_NPC_GREEN`. These identifiers
are compatibility adapters; the rendered art is supplied by the village asset
pass. Multiple named NPCs share a role sheet rather than each having an
individual animation atlas.

## Enterable settlement buildings

Nine settlement doors are visitable: six houses and three inns across the Den,
Sen'jin Village and Razor Hill. The houses share two compact,
twelve-by-ten-tile layouts: `PeonTrollHut` for Darkspear huts and `PeonOrcHut`
for Horde houses. Each contains one friendly resident at `(6,4)` who gives
short flavor dialogue and points the player toward an inn. These generic
Darkspear Resident and Horde Attendant roles are prototype additions, not
claimed as named Classic NPCs. They do not heal the player.

The exit at `(5,7)` uses Crystal's existing backup-warp mechanism to return
to the particular exterior door used to enter. Sharing a layout preserves
distinct entrance/return locations without adding nine separate map scripts.
Existing exterior village NPCs remain in place. Houses do not introduce
personal storage, additional quests or class training. The three inns use
`PeonOrcInn` or `PeonTrollInn` and separately implement explicit rest and
Hearthstone binding; those functions are documented and tested by the inn pass.

## Deep polish: preparation on the road

K'waii and Jark now use the same four-row shop presentation as the Den:
Spring Water, Minor Potion, Tough Bread, Cancel. Water remains the default.
Five waters cost the verified 25 copper; one Minor Potion and five Tough Bread
cost the retained prototype 25 copper. The added village stock is an adaptation,
not a claim that these named Classic vendors sold every one of these items.
Water restores ten Lightning Bolt charges, a potion restores twenty HP and
bread restores ten HP outside battle. The offer text explains the actual effect.

Each purchase first confirms, checks money and receives the entire quantity.
Copper and the transaction sound follow only a successful receipt. Cancelling,
insufficient money and a full bag leave the inventory and wallet unchanged.
Adding to an existing stack remains possible when all six initial stack slots
are occupied. The presentation does not add buyback, selling or new item IDs.

Gadrin, Vornal and Orgnil react to the saved Burning Blade Medallion state;
Vornal reminds an apprentice with an active quest to report to Zureetha, then
acknowledges completion and points to Kento's even-level lessons. These short
English lines are new writing. They do not activate hidden follow-up quests.
The shared orc residence also identifies Razor Hill and directs its visitors to
Grosk; its backup-warp exit remains tied to the actual entrance used.

The current services validator is `tools/validate_peon_services_polish.py`.
It writes fresh reports and native captures under
`references/generated/deep_polish/services/`; published older reports are not
updated in place. A passed report identifies the exact candidate ROM SHA.
