# Peon of Warcraft implementation status

This file describes the actual v0.2.1 scope and the remaining work. Large concept images and prepared PNG animations do not count as playable systems.

| Area | Current playable behavior | Remaining work |
| --- | --- | --- |
| Title | Native portal artwork, Start, four-channel arrangement of the supplied MIDI and original Warcraft-inspired effects | More ambient tracks; exact source MP3 is not streamed |
| New character | Bonk/blackout/eye-opening, Thrall and masters, Kento asks name, apprentice kit | Expand cinematic staging and character selection presentation |
| Classes | Shaman with Mace Strike and Lightning Bolt | Warrior/Warlock art exists; their routes remain locked |
| World | Seven explorable compact regions; road, coast, cliffs, two cave chambers | Full Durotar geography, Echo Isles, Orgrimmar interior |
| Villages | Eighteen outdoor NPCs, names/services adapted from Classic; nine doors and two shared rooms | Unique NPC atlases/interiors; full profession and vendor services |
| Dialogue | Thirteen role portraits, eighteen-column text, `Péon <name>` | Individual portraits for every named NPC; more narrative reactions |
| Quests | Reduced-count Cutting Teeth, Sting, Galgar harvesting and Lazy Peons; map/bag rewards; repeatable cave encounters | Full quest prerequisites/counts, Sen'jin chains, journals, medallion progression |
| Combat | Direct peon/enemy introduction without trainer, ball or creature naming; native attack poses and Lightning/Firebolt effects; original poison mechanics | More foes, spells, attack timing and encounter balancing |
| Artwork | Transparent native sprites with larger humanoid silhouettes, front/back sets, building/prop cutouts, Den campfire and animation previews | Replace shared silhouettes with individual character designs as needed |
| Gear | One active weapon slot; gray/white/green/rare blue prototype weapons | Independent armor/shield/totem slots and stat formulas; broad Classic catalog |
| Bags/vendors | Six/twelve/twenty stacks; water consumption; verified five-water/25-copper offers | Selling, buyback, full stock, reputation prices, item icons per catalog entry |
| Map | Select/Start access after Sting; whole-region discovery fog; Foreman/Galgar quest markers | Per-tile exploration if desired; larger world atlas and more quest POIs |
| Menus | Parchment, red headings, gold frame, native rarity colors; clean return to world/battle | More individual equipment icons and full vendor layouts |
| Mak'gora Proofs | Warcraft label visible; zero earned | Duel encounters, persistence design, rewards, explicit removal of inherited badge dependencies |
| Saves | One battery slot; cold restart, inside-hut return and Den upgrades tested | Multi-save design and migration outside tested locations |
| Chromatic | Native CGB/MBC3/timer/RAM/battery header, emulator validation | Actual supported-cartridge flashing, hardware SRAM and RTC validation |

## Next implementation order

1. Playtest the published slice: route readability, input timing, combat balance and naming/text fit.
2. Extend the cave/medallion and Report to Sen'jin/Report to Orgnil quest chain with explicit prerequisites and persistent event bits.
3. Add a small set of individualized NPC portraits and native sprites, using current role sheets as compatible fallbacks.
4. Build a real equipment/stat design before adding armor or claiming a complete Warcraft character sheet.
5. Add a first Mak'gora challenge only after deciding how proofs interact with rewards and removing unwanted Crystal badge/obedience gates.
6. Validate real Chromatic SRAM/RTC and cartridge loading. Keep multiplayer/large parties outside this prototype phase.

Each milestone must build, pass its relevant normal-input test, document save impact and include actual ROM captures. Use `PEON_DESIGN_RULES.md` for style, native dimensions, vocabulary and source-truth rules.
