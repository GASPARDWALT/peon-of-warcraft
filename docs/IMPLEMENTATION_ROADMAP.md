# Peon of Warcraft implementation status

The current playable release is **v0.2.9**. Its exact-ROM manifest and native
reports certify the delivered binary. Shared mana/rage, actual two-to-three
member parties, class-specific reusable recruitment items, six additional
animated roles and successive enemy packs are implemented. The seven-region
layout now uses real partial-cliff collisions and 76 bounded Continue landing
entries. See [current build scope](V0_2_9_PLAYABLE_BUILD.md),
[stability validation](QA_STABILITY_V029.md), [resource storage](RESOURCE_STORAGE_V029.md)
and [party/capture design](TEAM_RECRUITMENT_V029.md).

Remaining major work includes independent hero stat curves and further ordinary
balance tests near Sen'jin, a complete equipment system, wider Classic quest
progression, larger world coverage and physical Chromatic/cartridge testing.
The native battle still has one active fighter and four actions; true multi-save
and simultaneous multi-actor combat are not implemented.

## Historical v0.2.5 baseline

This describes the actual v0.2.5 scope. Native ROM behavior and exact-hash
validation determine completion; large concepts and prepared PNGs alone do
not. See `V0_2_5_ENVIRONMENT.md` for play, saves and explicit prototype limits.
The v0.2.4/earlier sections below are historical milestones.

| Area | Current playable behavior | Remaining work |
| --- | --- | --- |
| Title/audio | Native portal title, seven four-channel themes, effects and golden level-up particles | Physical audio playtest; Warcraft recordings are not streamed |
| New character | Bonk/blackout/eye-opening, Thrall and three masters; the chosen master asks a name; `Péon <name>` persists | Expanded cinematic and save/character selection presentation |
| Classes | Shaman, Warrior and Warlock intros, kits, character sheets and class-specific trainers; eleven lessons per class through level 20; protected basics and two trained-action slots | Ordinary progression to higher lessons, separate class stat curves, proper mana/rage/cooldowns and distinct body sets |
| World | Seven geographic Valley sectors connected in the requested directions; five native IDs25–29 append after the preserved original maps; eighteen terrain arrays distinct; Hana'zua/Zureetha/Sarkoth/imps moved and their old locations retired | Fixed camera screens, more geographic detail, full Durotar/Echo Isles and Orgrimmar interior |
| Villages | Nine usable doors, six residences/three inns, four distinct Orc/Troll room layouts; healing/binding/Hearthstone and original-door returns | Room IDs remain shared within each race; professions and Hearthstone cooldown policy |
| Dialogue/font | Role portraits, eighteen-column text and original readable 128-glyph 8×8 font; native glyph/VRAM/pixel verification; box geometry and name limit retained | Individual portraits for every named NPC and richer narrative reactions |
| Quests | Finite starter chain, cactus harvests, four-familiar prerequisite, Sarkoth report, one-time XP/copper/items, three-state glyphs and full-pouch recovery | Call of Earth, Thazz'ril's Pick, Sen'jin/Orgnil reports, journal, full Classic counts and respawn policy |
| Combat | Four actions, unlimited basic melee, charged class attacks, native status/drain/stage effects and animations, persistent enemy deaths and two successive road scorpids | More normal-play balance/progression; six actions require save-safe design; wound/curse/burn share one status and AoE is one-target |
| Warlock pet | Friendly native imp follower indoors/outdoors/Continue; battle backview and1 HP Firebolt after a completed live round; native victory/XP/death handling | Pet health/mana, commands, summon costs, scaling, threat and equipment |
| Artwork | All47 native environment blocks redrawn within192 tile slots; original transparent buildings/vegetation/props/potions/imp/mailbox/font; three-phase native fires | Further individualized actors and terrain variety within measured tile/OAM budgets |
| Gear | Active weapon bonuses, quest upgrades, native rarity/icons and class starter mace/axe/staff records | Independent armor/shield/totem stats and complete loot/equipment progression |
| Supplies/vendors | Six/twelve/twenty-stack bags;20 HP healing,5 charge mana,10 charge water, outside-combat bread; guarded purchases/refusals and one enemy turn for successful combat use | Shared mana/rage, full Classic stock/prices, selling/buyback and reputation |
| Loot | Finite kills independently roll 1/6 for one potion; caster 2:1 heal/mana, Warrior heal only; dead/flee/loss/full-bag safeguards | Equipment loot tables, additional sensible consumables and ground/drop-recovery policy |
| Map | Earned Select/Start atlas opens seven-sector Valley overview with sector fog, projected player and live targets; existing Den zoom/regional pages; building/cave projections and legacy discovery bridge | Per-cell fog, broader world atlas and additional quest points |
| Menus/HUD | Fixed seven-entry menu and Character/Bags/Inventory frames across classes; live actions/HP/quantities/rarity; fixed 34×8 world face/life overlay | Fuller equipment/vendor screens and a larger persistent HUD; crowded scenes can briefly hide the current overlay |
| Mail | Visible Horde mailboxes near Den/Sen'jin/Razor inns; local interaction leaves persistent state unchanged | Actual letters, attachments or network backend |
| Mak'gora Proofs | Placeholder removed from Character; no earned proof/duel progression | Duels, rewards/persistence and removal of remaining badge/obedience dependencies |
| Saves | One actual battery slot; earlier IDs/record sizes/event indices retained, new class/lesson/sector reserved bits, old floors remain walkable; current scenery/NPC/cactus refresh and v0.2.4 upgrade | Multi-save and broader older-release migration coverage |
| Chromatic | Valid native CGB-only/MBC3+RTC+RAM+battery header and emulator validation | Supported-cartridge flashing, hardware SRAM/RTC and physical playtesting |

## Next implementation order

1. Human-playtest v0.2.5 in all three classes for paths, supplies, enemy attrition, quest pacing, text and companion readability.
2. Add enough native quests/encounters to support later lessons without diagnostic level fixtures; Call of Earth and Thazz'ril's Pick are suitable next slices.
3. Improve the existing seven geographic areas against the annotated decoration reference; plan a camera migration separately if literal fixed screens remain desired.
4. Extend the Sen'jin/Orgnil reports and add individualized named-NPC art and regional details within native budgets.
5. Design real resource/equipment storage before shared mana/rage, armor slots, six actions or pet stats; document save migration before implementation.
6. Add a first Mak'gora challenge after deciding proof rewards and removing unwanted badge/obedience rules.
7. Decide local mail semantics before letters/attachments; mailboxes currently only create atmosphere.
8. Validate actual Chromatic loading, SRAM and RTC. Multiplayer and multiple simultaneous combat actors remain outside this prototype.

Each milestone must compile, pass appropriate ordinary-input checks, document
save impact and include genuine ROM captures. `PEON_DESIGN_RULES.md` governs
native dimensions, vocabulary and separation of concepts from implemented art.

## v0.2.5 validation boundary

The packager requires sixteen exact-ROM native reports: source, environment
routes, retained quests, seven-sector atlas, UI, old-save upgrade, three class
suites, four potion reports, loot, companion and font. Static reports verify
all 47 native blocks/192 tiles, five appended maps/old-floor retention, binary
transparent art, atlas projections and128 fixed-cell font glyphs. The release
manifest records the exact SHA and checked report hashes.

Ordinary controls cover three class selections, real names/kits/training,
combat/rewards/inn recovery and cold saves; all nine geographic edges with
reciprocal returns; nine building entrances, four room restarts, three cactus
harvests and 512 fire frames; moved quest givers, live atlas points/fog, native
text pixels, potions, finite loot and imp rounds. Higher-level lesson/spell,
full-bag/RNG/exhausted-charge and pet-finisher cases use labelled private
fixtures. They do not claim natural level 20 progression or hardware play.

Build with `sh tools/rebuild_peon_v025.sh --build`; its `--validate` mode runs
all required checks. Exact implementation boundaries are in
`V0_2_5_ENVIRONMENT.md`, `VALLEY_SEVEN_ZONE_LAYOUT_V025.md`,
`VALLEY_ATLAS_V025.md`, `PLAYABLE_CLASSES_V025.md`, `CLASS_SPELLS_V025.md`,
`CLASS_POTIONS_V025.md`, `RARE_POTION_LOOT_V025.md`, `WARLOCK_PET_V025.md`
and `READABLE_FONT_V025.md`.

## v0.2.4 completed validation

The packaged native candidate is
`704022c22c441944d13e3ff65950a971e5c7ead614a1ff0e1bba476c340bea2d`.
Required reports pass on that exact SHA-256: ordinary naming/input and ten
quest-route battles, actual quest-marker pixels, one-time rewards, nine door
returns, four room battery cold restarts, a harvested-cactus previous-audio
save upgrade, level-up audio/particles, poison recovery, inventory/refusal
cases, trainer purchases and legacy move/charge repair, spell/status cases,
and battle item turn costs. Temporary RAM fault fixtures are labelled
separately from ordinary gameplay. Physical console tests remain outstanding.

Map IDs/dimensions, original movement collisions, all previous event IDs,
item/music/sound IDs and SRAM/WRAM layouts are unchanged. New quest/reward
state occupies four previously unused reserved event bits. Earlier archives
and published evidence remain untouched. Shared room allocations remain;
removing duplicate terrain arrays did not create nine independent room IDs.

Build with `sh tools/rebuild_peon_v024.sh --build`; `--validate` runs the native
checks into the new evidence tree. Implementation boundaries are detailed in
`DEEP_POLISH_WORLD.md`, `DEEP_UI_POLISH.md`, `PLAYER_HUD.md`,
`DEEP_COMBAT_POLISH.md`, `DEEP_QUEST_POLISH.md` and `V0_2_4_PLAYABLE.md`.

## Historical Valley visual preview after v0.2.3

`releases/valley-preview/` contains the compatible playable preview and a separate
art/audio gallery. See `VALLEY_PREVIEW_PLAYABLE.md` for controls and save transfer.

- Native ochre cliffs, faceted boulders, Horde banners, palisades and brighter
  paths; the existing scrolling regions remain in use.
- Den provisioners, Tough Bread, locked Warrior/Warlock masters, a short guard
  patrol and two persistent hostile cave guards.
- Actual player portrait/life HUD with a compact crowded-view fallback; current
  regional atlas player position and active quest objectives.
- Original native boar and Lightning Bolt effects, with WAV previews. WoW sound
  recordings were not available from the cloud and have not been auditioned.
- Native-input emulator checks and a v0.2.3 battery-save upgrade, including
  access to the new merchant alcove, pass on the packaged ROM.

The next map milestone is the user's seven-screen Valley layout: preserve its
mountain barriers, connect readable trails, place Hana'zua in zone 4 and Sarkoth
in zone 5, and align the cave and fortified exit with zones 6 and 7. The exact
drawn path reference is still pending. This geography and a combined Valley
overview are not implemented in the preview. Mana and physical Chromatic tests
also remain outstanding.

## Historical audio and level-up preview

`releases/warcraft-audio-preview/` extends the Valley preview with nineteen
original native sound effects, a short golden level aura for quest/combat XP,
and three refined four-channel ambiences. Existing event/map/item/save IDs stay
unchanged. See `WARCRAFT_AUDIO_PREVIEW.md` for reachable hooks and limitations.

Three transparent tree proposals are prepared in the new gallery; background
tile allocation and placement are still separate map work. Verified Classic
data suggests Vile Familiars, Sarkoth's report-to-Gornek follow-up, Thazz'ril's
Pick and a compact Call of Earth ritual as the next progression work. These
recommendations are recorded in `ORC_LEVEL_1_6_REVIEW.md`, not implemented by the
audio preview. Unavailable recordings/videos are not claimed as auditioned or
viewed references.
