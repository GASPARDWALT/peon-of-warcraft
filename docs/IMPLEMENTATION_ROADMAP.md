# Peon of Warcraft implementation status

This file describes the actual v0.2.3 scope and the remaining work. Large concept images and prepared PNG animations do not count as playable systems. See `V0_2_3_PLAYABLE.md` for the downloadable chapter and explicit prototype adaptations.

| Area | Current playable behavior | Remaining work |
| --- | --- | --- |
| Title/audio | Native portal artwork, supplied-guide arrangement, seven original four-channel ambient/battle themes and native effects | Physical audio playtest; exact Warcraft recordings/MP3 are not streamed |
| New character | Bonk/blackout/eye-opening, Thrall and masters, Kento asks name, apprentice kit | Expand cinematic staging and character selection presentation |
| Classes | Shaman; eleven purchased lessons at even levels, two prepared spell slots after Mace Strike/Lightning Bolt | Warrior/Warlock art exists; their routes remain locked; higher lessons need a longer progression |
| World | Seven explorable compact regions; road, coast, cliffs, two cave chambers | Full Durotar geography, Echo Isles, Orgrimmar interior |
| Villages | Eighteen outdoor NPCs, nine doors, six residences and three inns; healing, binding and Hearthstone | Unique room layouts, full profession/vendor services, Hearthstone cooldown policy |
| Dialogue | Fourteen role portraits, eighteen-column text, `Péon <name>`, checked opening and class locks | Individual portraits for every named NPC; more narrative reactions |
| Quests | Six reduced-count quests, slower XP, cactus harvests, Sarkoth/medallion proofs and retryable one-time rewards; three-state markers | Full Classic prerequisites/counts, Sen'jin chains, journal and respawn design |
| Combat | Eleven enemy types and apprentice with three native combat poses; twelve real spell animations; bag totem/potions; persistent defeated actors; two consecutive scorpids from level four; poison and bound-inn defeat recovery; revised attrition measured in 99 native diagnostic chains | Longer progression, more encounters, human balance playtest; six actions need explicit save-safe design |
| Artwork | Transparent native sprites with larger humanoid silhouettes, front/back sets, building/prop cutouts, Den campfire and animation previews | Replace shared silhouettes with individual character designs as needed |
| Gear | One active weapon; green quest upgrades; existing rarity effects and 32 native item drawings; Mage/Warrior gear prepared separately | Independent armor/shield/totem slots and stat formulas; actual broader loot/catalog progression |
| Bags/vendors | Six/twelve/twenty stacks; capped potion/water use costs a battle turn; native icons; water x5/25c and prototype potion/25c | Selling, buyback, full stock and reputation prices |
| Map | Select/Start after Sting; region discovery fog; four atlas quest POIs; clearer rocks, fires, Horde banners and palisades | Per-tile exploration if desired; larger world atlas and more quest POIs |
| Menus | Parchment, red headings, gold frame, native rarity colors; clean return to world/battle | More individual equipment icons and full vendor layouts |
| Mak'gora Proofs | Warcraft label visible; zero earned | Duel encounters, persistence design, rewards, explicit removal of inherited badge dependencies |
| Saves | One battery slot; persistent quest/enemy state, inn/Hearthstone cold restart and v0.1.1/v0.2/v0.2.1/v0.2.2 upgrades tested; battle pose flag uses unsaved padding | Multi-save design and migration outside tested locations |
| Chromatic | Native CGB/MBC3/timer/RAM/battery header, emulator validation | Actual supported-cartridge flashing, hardware SRAM and RTC validation |

## Next implementation order

1. Playtest the published slice: route readability, input timing, combat balance and naming/text fit.
2. Extend Report to Sen'jin/Report to Orgnil with explicit prerequisites and more finite encounters so later even-level lessons become reachable naturally.
3. Add a small set of individualized NPC portraits and native sprites, using current role sheets as compatible fallbacks.
4. Build a real equipment/stat design before adding armor or claiming a complete Warcraft character sheet.
5. Add a first Mak'gora challenge only after deciding how proofs interact with rewards and removing unwanted Crystal badge/obedience gates.
6. Validate real Chromatic SRAM/RTC and cartridge loading. Keep multiplayer/large parties outside this prototype phase.

Each milestone must build, pass its relevant normal-input test, document save impact and include actual ROM captures. Use `PEON_DESIGN_RULES.md` for style, native dimensions, vocabulary and source-truth rules.
