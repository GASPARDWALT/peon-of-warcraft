# Peon of Warcraft implementation status

This file describes the actual v0.2.4 scope and the remaining work. Large concept images and prepared PNG animations do not count as playable systems. See `V0_2_4_PLAYABLE.md` for the downloadable chapter, controls, save transfer and explicit prototype adaptations. The preview sections below are historical milestones, not the current feature boundary.

| Area | Current playable behavior | Remaining work |
| --- | --- | --- |
| Title/audio | Native portal artwork, supplied-guide arrangement, seven original four-channel ambient/battle themes, native effects and golden quest/combat level-up particles | Physical audio playtest; exact Warcraft recordings/MP3 are not streamed |
| New character | Bonk/blackout/eye-opening, Thrall and masters, Kento asks name, apprentice kit | Expand cinematic staging and character selection presentation |
| Classes | Shaman; eleven purchased lessons at even levels, two prepared spell slots after unlimited Mace Strike/charged Lightning Bolt; Kento safely normalizes older reordered move/charge pairs | Warrior/Warlock routes remain locked; higher lessons need a longer progression; four active actions remain the save boundary |
| World | Seven explorable compact regions; road, coast, cliffs, two cave chambers, nine native deadthorn trees, clearer Den trails and stone Valley exit boundaries; thirteen retained playable terrain arrays are distinct | Seven fixed Valley screens and complete Valley overview need final path references and a camera/location migration; full Durotar, Echo Isles and Orgrimmar interior remain future work |
| Villages | Nine doors, six residences and three inns; four distinct Orc/Troll room layouts; healing, binding, Hearthstone and originating-door returns | Room IDs remain shared within each race; full profession/vendor services and Hearthstone cooldown policy |
| Dialogue | Fourteen role portraits, eighteen-column text, `Péon <name>`, checked opening and class locks | Individual portraits for every named NPC; more narrative reactions |
| Quests | Existing six reduced-count quests plus four-familiar prerequisite and Sarkoth report to Gornek; quest XP/copper awarded once, cactus harvests, three-state markers and recoverable partial club/pouch rewards | Call of Earth, Thazz'ril's Pick, Sen'jin/Orgnil reports, journal, full Classic counts and respawn design |
| Combat | Eleven enemy types/apprentice with three poses, twelve native spell animations, unlimited turn-cost melee, charged spells, bag totem/potions, persistent defeated actors and consecutive scorpids from level four; battle exits clear transient state and Peon victories skip legacy evolution/virus/berry processing | Longer progression, more encounters and human balance playtest; six actions need explicit save-safe design; the normal completed route reaches approximately level seven |
| Artwork | Transparent native sprites with larger humanoid silhouettes, front/back sets, building/prop cutouts, Den campfire and animation previews | Replace shared silhouettes with individual character designs as needed |
| Gear | One active weapon; green quest upgrades; existing rarity effects and 32 native item drawings; Mage/Warrior gear prepared separately | Independent armor/shield/totem slots and stat formulas; actual broader loot/catalog progression |
| Bags/vendors | Six/twelve/twenty stacks; native icons; capped potion/water use costs a turn; food is outside combat; K'waii/Jark now offer potions/bread alongside water x5/25c; invalid use consumes nothing | Selling, buyback, full Classic stock and reputation prices; bread/potion prices are prototype balance |
| Map | Select/Start after Sting; regional discovery fog, refreshed native thumbnails, player position and live quest objectives including familiars/cave/Gornek report | Complete Valley overview, per-tile exploration if desired, larger world atlas and more quest POIs |
| Menus | Fixed seven-entry Shaman Start menu; fixed 20×18 Character/Bags/Inventory frames; actual prepared actions and HP maximum; quantities, selection, rarity and equipped status; browsing keeps fonts resident | More equipment icons and full vendor layouts; the character view does not imply functional armor or six actions |
| World HUD | One fixed 34×8 face/life ink footprint, live health and no large/miniature switching; hides during other interfaces or exceptionally crowded frames | A larger permanent panel needs a background renderer; shared mana is unimplemented |
| Mak'gora Proofs | No earned proofs or playable duel progression; the old zero placeholder no longer crowds Character | Duel encounters, persistence design, rewards and explicit removal of inherited badge dependencies |
| Saves | One battery slot; four reserved event bits add quest/reward state without layout changes; current terrain refresh preserves harvested cactus state; previous-audio save upgrade and four room cold restarts verified | Multi-save design, migration outside tested locations and broader older-release upgrade coverage |
| Chromatic | Native CGB/MBC3/timer/RAM/battery header, emulator validation | Actual supported-cartridge flashing, hardware SRAM and RTC validation |

## Next implementation order

1. Human-playtest v0.2.4 for route readability, combat attrition, quest pacing and native input timing; compare the packaged ROM with its emulator evidence.
2. Complete the user's seven-screen Valley path reference, then design camera/saved-location migration before changing map IDs, dimensions or topology.
3. Add a compact Call of Earth ritual and Thazz'ril's Pick with explicit prerequisites and finite encounter accounting; preserve existing owned totems and completed saves.
4. Extend Report to Sen'jin/Report to Orgnil and add enough reachable progression for higher even-level lessons.
5. Add individualized NPC portraits/sprites and additional regional vegetation using existing role art as explicit fallbacks.
6. Design independent equipment/stat storage before armor, six actions or a complete Warcraft character sheet; plan any required migration first.
7. Add a first Mak'gora challenge only after deciding proof rewards and removing unwanted badge/obedience dependencies.
8. Validate actual Chromatic cartridge loading, SRAM and RTC. Keep multiplayer, other fully functional classes and large parties outside this slice.

Each milestone must build, pass its relevant normal-input test, document save impact and include actual ROM captures. Use `PEON_DESIGN_RULES.md` for style, native dimensions, vocabulary and source-truth rules.

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
