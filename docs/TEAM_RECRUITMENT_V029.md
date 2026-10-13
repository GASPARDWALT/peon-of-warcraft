# Native team and class recruitment v0.2.9

The original party record remains 48 bytes and the six physical slots remain in the save. The playable Peon roster admits two members initially and three after the Sarkoth report to Gornek. The hero stays in record zero; CHARACTER, training, quest experience and equipment keep their existing owner. The preferred starting actor is transient and resets on cold Continue.

Warlocks receive a real level-matched Red Imp in record one after the new-character initialization flags are set. Cold Continue upgrades a genuine one-member legacy Warlock once, without changing the hero, name, kit, money or position. Populated legacy parties are preserved. A fainted imp cannot assist or follow. Its passive Firebolt remains one HP per complete round; it does not fire an additional passive bolt while the imp is the active fighter. Inn recovery recreates the follower without touching normal NPCs.

CHARACTER exposes R:TEAM. The three-row TEAM panel uses original transparent world sprites, bold actor names and regular body text. Field selection chooses the preferred initial fighter without exchanging saved records. Battle TEAM selection uses native TryPlayerSwitch, including trapping rules and the ordinary switch turn. Forced replacement after fainting uses the same panel and cannot cancel. Supplies outside battle select a party target through this panel; Inventory must completely reload its frame after the nested menu.

## Class pact quest

After the first Cutting Teeth turn-in, the selected Den master offers one recruitment task and then continues to provide normal level-based training. Repeated conversations do not grant another relic or another reward. Finishing the pact awards 50 prototype experience and 100 copper once.

| Selected class | Reusable relic | Native item ID | Eligible actor | Initial training node |
| --- | --- | --- | --- | --- |
| Shaman | Earth Relic | 5 | Earth Spirit / ONIX | Crossroads (3,5), object 1, level 2 |
| Warrior | Rally Horn | 2 | Orc Grunt / MACHAMP | Hana'zua Camp (3,6), object 1, level 2 |
| Warlock | Demon Skull | 4 | Red Imp / GEODUDE | Cave Approach (7,7), object 1, level 3 |

These item numbers are preserved but their native pocket is ITEMS. They cannot be tossed and are reusable. Full roster, wrong class, wrong actor family, trainer/link/tutorial encounters, zero HP or transformed targets are refused before a turn or item is spent. Kolkar centaurs and humanoid Orc Warlocks are deliberately not eligible recruits.

For v0.2.9, binding is limited to the five explicit neutral pact/training nodes listed here. The native loadwildmon command clears the transient CFFA discriminator; each neutral node sets its own object index afterward. Eligibility checks the actual group, map, species, and known node index as well as family and capacity. Hostile cave imps cannot be captured in this build, so capturing an ally never awards their kill quest credit, copper, or loot. A broader hostile capture system needs separate retirement/quest semantics.

A valid attempt uses Crystal's ordinary base Poké Ball catch threshold: catch rate, current/max HP, and the original sleep/freeze bonus and Random call. It keeps the historical max-HP truncation and ineffective burn/poison/paralysis bonus, rather than silently substituting a newer Pokémon formula. It uses no enhanced-ball multiplier. A failed valid roll spends one battle turn but no relic. Success copies the native captured HP/status/DVs/experience, assigns an automatic role name, initializes role actions, completes native caught data and only then initializes the shared resource metadata. It opens no ball animation, Pokédex page, creature naming prompt or storage box.

After reporting Sarkoth, an optional level-six Earth Spirit at Sen'jin (11,14), object 8, and Orc Grunt at (12,14), object 9, let Shaman and Warrior fill the third roster place using the same reusable class relic. Both points and their three talk approaches were checked against native floor/connectivity; full scene allocation remains a final ROM test.

Neutral training/pact nodes have no auto-aggro and no scripted potion, ration or copper drop. A KO removes the live object for the current visit without setting its retirement event; returning to the zone allows another attempt. Successful recruitment permanently retires that node. This explicit retry behavior prevents the only class quest target from being lost. Hostile enemies retain their separate persistent death behavior.

The atlas adds at most one quest OBJ: an accepted task points to the class target in the seven-sector Valley overview; a captured ally points with a yellow question mark to the selected master in The Den. Existing discovery/fog restrictions and all current marker actors remain unchanged.

## Integration and save contracts

- New transient bytes CFF2..CFFA: nine bytes, outside saved data; resources own CFFB..CFFF.
- Sequential reserved flags after Sector 7: starter imp, accepted, captured, rewarded, first Earth node retired, first Grunt node retired. All existing later IDs remain fixed by const_next 600.
- The neutral Imp retirement uses explicitly reserved flag 590. Optional Sen'jin Earth/Grunt retirement uses flags 591/592. None consume the following combat flags.
- Public farcalls take/return party index in C. ReturnFarCall overwrites A with C; carry and BC/DE are the reliable public outputs.
- Helpers temporarily select WRAM bank 1 and restore the caller's exact SVBK. Imp graphics guards preserve BC/DE asset/object pointers.
- Managed companion additions skip the native seen/caught Dex bookkeeping under the initialized-Peon/no-link guard. This guard intentionally does not require the current map tileset: cold Continue upgrades the party before loading the saved map. Starter migration therefore preserves both original saved Dex bitsets as well as the hero.
- Six original SRAM party records, checksums, original event IDs, item IDs and map/object indices stay stable. Valley nodes replace existing placeholder object 1. Optional Sen'jin allies append objects 8/9 after all seven original NPCs; neither changes old indices.
- New resources deliberately reuse Pokerus/caught metadata under the resource module's cured 0x80 sentinel. This is documented prototype metadata, not original location/Pokerus behavior.

## Validation status

The private hook patch passes git apply --check. The team, recruitment and modified atlas modules pass independent RGBDS 1.0.4 assembly. Full ROM linking, normal-button gameplay, probabilities, forced replacement, and cold-save upgrade remain required on the final integrated ROM. These source checks are not a runtime or physical cartridge pass.
