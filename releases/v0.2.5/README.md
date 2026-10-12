# Peon of Warcraft v0.2.5 — Seven Valley areas and three classes

[Playable ROM ZIP](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/v0.2.5/peon_of_warcraft_v0_2_5.zip) · [Transparent PNGs, native captures and offline browser gallery](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/main/releases/v0.2.5/peon_of_warcraft_v0_2_5_assets.zip)


This is a native 2 MiB Game Boy Color ROM built on v0.2.4. The adventure
remains in English. Shaman, Warrior and Warlock can now start the same playable
chapter, with one character actor, four prepared actions and one real 32 KiB
battery save. The release includes the connected Valley geography, complete
native scenery redraw, class abilities, usable supplies and a Warlock imp.

## Valley geography and scenery

The seven areas now follow the user's directional layout:

`1 The Den → east → 2 Valley → north → 3 Crossroads → west → 4 Hana'zua → south → 5 Sarkoth → east → 1`.

From zone 3, go north into zone 6 and enter Burning Blade Cavern. From zone 2,
go east through zone 7's fortified gate and continue into Durotar Road.
Hana'zua, Zureetha, Sarkoth and the two outdoor level-three familiars have
moved into those areas. Their old Valley actors, markers and hostile triggers
are retired; the old cave opening is closed. The existing cavern returns to
the real entrance in zone 6. Galgar and the three harvestable cacti stay in
zone 2, while Den shops, masters and established building doors remain usable.

Five compact maps append IDs 25–29; each is 5×5 native blocks, or 160×160 pixels.
The Den and original Valley area retain their saved dimensions, and the game
still uses Crystal's scrolling camera. This implements seven geographic areas
and their connections, not seven fixed 160×144 camera screens. Existing saved
walkable cells remain walkable; only six declared canyon-wall blocks open for
the new north/west passages. The tileset's 47 collision rows stay unchanged.

All 47 environment blocks are redrawn in original native pixel art: red-hide
and ivory-bone Orc buildings, Troll thatch and timber, readable doorways,
rock arches, layered cliffs, sandstone boulders, dry trees, coastal palms,
cacti, scrub, Horde banners, palisades, towers, campfires, braziers and furniture.
Actual building openings align with their passable bottom-right movement
quadrant. The closed northern Orgrimmar boundary no longer looks like an
accessible cave. Three-phase campfire/brazier animation changes two reserved
background tiles while the remaining 190 tile slots stay intact.

The standard font is also redrawn for readable capitals, lowercase,
punctuation, digits and `Péon`. Characters remain fixed 8×8 glyphs; borders,
cursor icons, text-box dimensions and eighteen-column wrapping remain stable.
The background art retains the 192-tile budget. Native PNG cutouts have binary
transparency; fully opaque floor tiles are labelled as terrain. Transparent
PNG previews compile into tiles and palettes, not large unrestricted objects.

## Classes, abilities and supplies

The chosen master asks for the character's name. The persisted name is `Péon `
plus up to five entered characters; there is no companion-renaming prompt.
Existing Peon saves without a Warrior/Warlock class bit continue as Shamans.

| Class | Initial actions | Starter supplies | Trainer |
| --- | --- | --- | --- |
| Shaman | Unlimited Mace Strike, Lightning Bolt | 2 healing potions, 1 mana potion, reusable Earth Totem | Kento Brandenhoof |
| Warrior | Unlimited Melee Strike, Weapon Strike | 2 healing potions | MoCMoc Zogzog |
| Warlock | Unlimited Melee Strike, Shadow Bolt | 2 healing potions, 1 mana potion, friendly imp | Xasthur |

Each class trainer sells eleven lessons through level 20. Two basic actions
remain protected and two slots hold selected learned skills. Other class
masters refuse training. Owned lessons can be prepared without buying them
again, but doing so preserves/caps their charges rather than granting a free
refill. Equipment and starter consumables are not handed out on repeat visits.

Warriors learn techniques such as Heroic Strike, Rend, Defensive Stance,
Hamstring and Shield Block. Warlocks learn Drain Life, Corruption, Fear,
Immolate and later shadow skills. Shaman lessons retain Flame Shock,
Healing Wave and the established elemental progression. Ability effects,
levels and prices are adapted for this ROM. Fear lowers accuracy; wound/curse/
burn effects share one native status slot; Cleave and Hellfire hit one target.
The chapter does not provide ordinary progression all the way to level 20.

Mana is currently **charges for each prepared spell**, not a shared mana bar.
Warrior techniques also use charges; there is no rage pool. Healing potions
restore up to 20 HP for any class. Mana potions restore up to five charges of
each prepared magical action for Shaman/Warlock, and water restores up to ten.
The unlimited melee action is excluded even in reordered older spellbooks.
Full-health/full-charge/invalid uses consume neither supplies nor a combat turn.
Each successful potion, water or Shaman totem use costs an enemy action.
Bread restores up to ten HP outside combat. Vendors sell single healing/mana
potions for 25 copper and five waters for 25 copper; potion prices are prototype
balance, not a complete Classic economy.

A newly defeated finite enemy has an independent **1/6** potion-drop chance.
Successful caster drops are two parts healing to one part mana; Warrior drops
are healing only. A dead enemy cannot be farmed by revisiting its tile.
Fleeing/loss produces no drop. Optional loot is skipped safely when the bag
cannot receive it, while quest-claw/medallion recovery remains available.

The Warlock's red imp follows the actual native movement trail, including
indoors and after Continue. It appears in front of the Warlock in combat and
fires an animated Firebolt for **1 HP** after a completed round while both
combatants live. It adds neither a fifth action nor another enemy turn and
spends no spell charges. Pet commands, separate health/mana, summon costs and
talent scaling are not implemented. Horde mailboxes beside the Den, Sen'jin
and Razor inns are local empty-post interactions; no mail/network backend is
implied. The Den's optional cook is absent for Warlocks to reserve the follower
slot, and one former neutral boar becomes the Den mailbox.

## Download, map and saves

Extract `peon_of_warcraft_v0_2_5.gbc` from the playable ZIP and open it in a
Game Boy Color emulator. D-pad moves, A talks/interacts/confirms, B cancels,
and Start opens the fixed Character/Bags/Map/Save/Hearth/Options/Exit menu.
After Gornek's scorpid quest, Select or Start → MAP opens the earned atlas.
The Valley page shows all seven sectors in their geographic arrangement,
with undiscovered sectors hidden, the player's actual projected position and
live quest objectives. Left/Right browse pages; the Den zoom remains available.
Fog is per sector, not per individual terrain cell. Indoor projections use
the building's exterior doorway; the cavern projects through zone 6.

Visit an innkeeper to heal and choose a home. Hearthstone returns there;
travel itself does not heal. Poison still damages the character while walking.
After defeat, dismiss the dialogue and ask the innkeeper to recover from the
one-HP return. In combat, use BAGS for supplies; the Earth Totem is Shaman-only.

Back up your existing battery save before changing ROMs. Copy it beside the
new ROM using the basename and extension your emulator expects. PyBoy uses
`peon_of_warcraft_v0_2_5.gbc.ram`; many others use
`peon_of_warcraft_v0_2_5.sav`. Continue uses the same real slot. Save and restart
to verify the copy locally. Transfer battery saves, not emulator savestates.
Existing map numbers, inventory/character records and SRAM/WRAM sizes remain
stable; class, lesson and sector-discovery state uses reserved event bits.
Continue refreshes current terrain/actors and reapplies harvested-cactus state.

## PNGs and offline gallery

Extract the assets ZIP and open `environment_v025/index.html` in a browser.
It needs no server or external network dependencies. Its labelled filters
separate final-ROM captures, genuine v0.2.4 comparisons, compiler reconstructions,
transparent artwork, controlled diagnostics and the unintegrated art concept.
An illustration or compiled terrain sheet is not presented as gameplay.

Useful exact source filenames include:

- `references/generated/environment_v025/props/the_den_horde_hide_and_tusks.png`
- `references/generated/environment_v025/props/orc_hut.png`
- `references/generated/environment_v025/props/troll_hut.png`
- `references/generated/environment_v025/props/deadthorn_tree.png`
- `references/generated/environment_v025/props/coastal_palm.png`
- `references/generated/environment_v025/props/cactus_red_blooms.png`
- `references/generated/environment_v025/props/sandstone_boulder.png`
- `references/generated/environment_v025/props/cave_mouth.png`
- `references/generated/environment_v025/props/campfire.png`
- `references/generated/environment_v025/potions/assets/minor_healing_potion_native.png`
- `references/generated/environment_v025/potions/assets/minor_mana_potion_native.png`
- `references/generated/environment_v025/pet/assets/horde_mailbox_native.png`
- `references/generated/environment_v025/pet/assets/warlock_imp_back_native.png`
- `references/generated/environment_v025/pet/assets/friendly_imp_world_native_sheet.png`
- `references/generated/environment_v025/font/peon_readable_glyphs_transparent.png`

ZIP paths begin at `environment_v025/`. Native cutouts have pixel-preserving
enlargements. `blocks/` contains all 47 background blocks; `zone_layout/maps/`
contains the final eighteen terrain arrays. Earlier road-only/preliminary
captures, failed traces, user saves and non-final candidate reports are excluded
from the release archives without deleting their source evidence.

## Validation and remaining scope

The packager requires **sixteen native reports** to pass on the exact packaged
ROM SHA-256, plus static source/art/geometry/font checks. The release manifest
records their hashes. Ordinary-input suites cover all three class intros,
names/kits/training/boar victories/cold saves; all nine geographic links and
returns; nine doors and four room cold restarts; cactus harvesting/persistence;
the relocated quest chain, cave ownership and enemy retirement; actual atlas
fog/player/objective pixels; fixed menus and native font VRAM/pixels; potions,
loot and the imp's movement/round/victory/save behavior. Fire animation is
observed for 512 native frames. The upgrade suite copies a genuine v0.2.4
battery save into the new ROM and checks character progress and harvested terrain.

Separate labelled RAM/state fixtures cover later trainer gates, spells/status
effects, exhausted or reordered charges, full bags, RNG tails and pet finishing
blows. They do not claim ordinary level-20 progression or edit user saves.
Historical baseline captures retain their separately checked v0.2.4 hash.

Fixed camera screens, six actions, independent armor slots, separate class
stat-growth curves, full mana/rage/cooldowns, pet commands, mail services,
selling/buyback, multi-save and the complete Durotar/Orgrimmar world remain
future systems. Room IDs remain shared within each race. The fixed HUD may
temporarily hide in exceptionally crowded views to preserve NPC rendering.
Actual Chromatic cartridge flashing, SRAM, RTC and physical playtesting remain
outstanding; emulator success is not a console test.

Detailed implementation boundaries are in `VALLEY_SEVEN_ZONE_LAYOUT_V025.md`,
`VALLEY_ATLAS_V025.md`, `PLAYABLE_CLASSES_V025.md`, `CLASS_SPELLS_V025.md`,
`CLASS_POTIONS_V025.md`, `RARE_POTION_LOOT_V025.md`, `WARLOCK_PET_V025.md` and
`READABLE_FONT_V025.md`. Horde-building research and inspected reference hashes
are recorded in `ENVIRONMENT_V025_REFERENCES.md` and `research/source_manifest.json`;
class spell pages have their own `classes/wowhead_references.json`. Original
native art/effects are used rather than imported Warcraft artwork or recordings.

Build with `sh tools/rebuild_peon_v025.sh --build`. Its `--validate` mode runs
the required native checks. After they pass, package with
`python3 tools/package_peon_v025.py --expected-sha <tested SHA-256>`.
Do not run an older world/path-only builder over the final seven-area maps.

ROM SHA-256: `8b19628e4df259b96c4874b1220f238d7d166e6c05d136d7448c6ee9c77aaae8`
