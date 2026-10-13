# Codex prompt — Import Environment Pack v2 into pokecrystal

Use `peon_of_warcraft_environment_pack_v2_art_quality/` as the canonical environment-art source. This pack supersedes the older procedural environment pack.

## Do not redraw the assets
Preserve the supplied pixels, transparency, dimensions and filenames. Never use bilinear filtering.

## Start with an engine audit
Before modifying code:
1. Verify the current ROM builds.
2. Identify the repository's graphics conversion rules for tilesets, 2bpp graphics, palettes, metatiles/blocks, collision tables, map blockdata, map headers, connections, warps and events.
3. Report the exact files to modify.
4. Create a dedicated branch or logical commit sequence.

## Import model
The source art follows this design:
- hardware tile unit: 8×8
- terrain/metatile concept: 32×32 (4×4 hardware tiles)
- transparent props/buildings: multiples of 8
- ground is opaque
- each 8×8 region has a reduced GBC-style palette

For every imported 32×32 terrain asset:
1. Split into sixteen 8×8 cells.
2. Deduplicate identical cells.
3. Convert through pokecrystal's normal PNG/2bpp pipeline.
4. Create the appropriate 4×4 block/metatile definition.
5. Assign collision and palette data.

For transparent props/buildings:
- choose deliberately between background blocks, object sprites, or map-object composition based on engine limits;
- do not force large buildings into movable object sprites;
- preserve alpha only in the reference source; convert to the engine-appropriate representation.

## Work biome by biome
Do not import every folder at once.

### Milestone 1 — Durotar / Valley tileset test
Import only `durotar_valley/` and build a small `PeonTilesetTest` map containing:
- dirt and red-sand variants
- cracked ground
- straight/vertical/corner/cross paths
- terrain transitions
- rock and cactus collisions
- palisade wall/gate collisions
- cave entrance warp
- hut entrance warp
- banner and brazier decoration

Compile, launch, and save screenshots to:
`references/generated/map_tests/durotar_tileset/`

### Milestone 2 — The Den
After the test map works, create The Den as the first real map. It replaces the Pokémon bedroom as the first controllable location after the opening sequence.
Required spaces:
- player spawn
- central fire
- Kento Brandenhoof / Shaman trainer
- first quest NPC with state-driven marker
- friendly guards and peons
- exit toward Valley of Trials
- room for crates, bedrolls, training objects and a Horde banner

### Milestone 3 — Valley of Trials
Create the main early exploration area with:
- a clear primary route
- side branches
- neutral boar locations
- hostile scorpid sightlines
- copper/herb/chest locations
- route to cave entrance
- side route to Sarkoth's Roost
- return connection to The Den

### Milestone 4 — Cave entrance/interior
Use the cave entrance asset as a warp landmark. Build the interior using a separate cave tileset or the closest existing pokecrystal cave pipeline.

### Milestone 5 — Sen'jin
Import `senjin_village/`:
- beach sand
- boardwalks
- shallow/deep water
- shore pieces
- palms, huts, totems, canoe and fishing props

### Milestone 6 — Razor Hill
Import `razor_hill/`:
- compact dirt and roads
- timber floors
- palisades/gates
- huts, inn, watch post, stable and training objects

### Milestone 7 — Echo Isles
Import `echo_isles/`:
- grass/sand/dark-earth
- jungle trails
- shore/water
- palms, trees, ruins, totems and bridge

## Shared interactables
Use `shared_interactables/` for:
- chest states
- copper/silver resource nodes
- herbs
- cactus apples
- quest supply bag
- camp furniture
- fire/brazier animations

Quest markers must be tied to quest state, not baked permanently into maps.

## Engine constraints
If the supplied art exceeds the active tileset/palette/block limits:
1. report the exact limit;
2. prioritize walkable terrain, required transitions and collision-critical structures;
3. document postponed decorative assets;
4. do not silently replace them with crude placeholders.

Keep the ROM compiling after every milestone and commit each biome/map separately.
