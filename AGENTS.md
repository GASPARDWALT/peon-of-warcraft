# Peon of Warcraft — working rules

## User artwork is the source of truth

- On 2026-10-14 the user explicitly rejected primitive circles, schematic cactus/palms and code-drawn decorative substitutes. NEVER propose or ship those substitutes. Use the supplied decor PNGs as the active sources; keep their complete silhouettes. If a native budget blocks an exact import, report the measured limit rather than inventing simpler art.
- The user prefers the earliest readable Peon, Boar and Imp character models over the v0.2.12 conversions. Restoring those archived native actor assets is explicitly authorized; retain the current approved buildings, interiors and working quest/gameplay code. Do not run their old broad generators.
- On 2026-10-14 the user requested matching Shaman head/body proportions and quieter terrain with texture only in patches. Keep those changes in derived native packets; preserve supplied props, pillars, structures, palettes, collisions and warps. Sparse ground grains must come from the supplied dirt PNG, not newly drawn shapes.

- Import the user's supplied PNG sprites directly when the request is to implement them. Preserve the original files and record crop coordinates and source hashes.
- Follow the stated layout: base Peon, Shaman, Warrior, Warlock; supplied world front/back/left/right sources at 16×16, combat front at 56×56, combat back at 48×48. The user's latest request authorizes derived world bodies at 24×24 for readability; preserve the original 16×16 files and the 16px movement/collision grid.
- World v0.2.15 enlarges existing complete silhouettes with nearest sampling and recovers supplied NPC source colors through per-tile hardware palettes. It adds no invented drawing detail. Preserve its 9-tile streamed frame packets, transparent-tile masks and palette attributes. Never replace missing canonical Kolkar/Crawler sources with new schematic art: their existing native historical sources are explicitly documented.
- On 2026-10-15 the user requested actual additional detail in the enlarged WORLD models, then larger and more detailed main battle characters. For v0.2.16, sample the approved dedicated world views directly at 24px rather than enlarging already reduced 16px images. Preserve the distinction between world and combat references, retain originals, and record lossy palette conversion honestly. Keep the working horizontal Lightning Bolt unchanged.
- The later 2026-10-15 correction explicitly requests ALL world characters to gain actual pixels and detail. For v0.2.17, this authorizes new native24x24 cell drawings guided by the supplied designs and Pokémon world proportions. The new JSON cels are declared authored artwork, never claimed extracted or enlarged original pixels. Keep all original PNGs and the v16 combat/quest/map/save behavior. Native actors use complete nine-tile frames; do not replace them with old16px fallbacks.
- The small rock must start with weapon-free STRIKE and earth/rock attacks, retaining native party PP and level-8/12 evolutions. MACE STRIKE remains free of mana; do not relabel its hero weapon action as the rock's action. Existing saves may only receive the narrowly recognized old rock starter correction, preserving other moves, PP, names and party data.
- Admit whole world actors within 40 OAM objects and 10 per scanline, prioritizing the player and nearby speakers. In dense scenes distant actors may be culled; the optional world resource HUD may be omitted when complete bodies exhaust its capacity. Do not change persistent object/save fields to implement visual scaling.
- Do not generate replacement art, reinterpret supplied sprites, or silently simplify their silhouettes, equipment or detail. Generated proposals are not a substitute for an authorized import.
- On 2026-10-13 the user explicitly authorized developing missing or damaged PNGs from the supplied artwork, retaining its design logic. Complete those gaps in separate derived files; keep valid supplied sprites and all original files intact. Do not ask again for that authorization.
- A visible conversation image is not proof of access to its original file. If its bytes are unavailable, identify that specific blocker immediately. Do not recreate it and claim it is an extraction.
- Measure actual dimensions, alpha, recoverable pixel grid and per-tile colors from the original file. Keep source PNGs intact; put any necessary hardware conversion in separate derived files.

## Finish the requested game change

- Existing user choices and approvals persist. Do not ask repeatedly to validate artwork or decisions already selected.
- When asked for a playable change, integrate it in the actual ROM, rebuild, and show captures from that exact ROM. Clearly distinguish an art gallery from implemented game graphics.
- Preserve saves, previous releases, unrelated user changes and working gameplay.
- Check every class, direction and affected battle pose so old graphics cannot reappear during movement, attacks or native menus.
- Before running an asset builder, inspect whether it redraws or overwrites imported art. In particular, `tools/rebuild_peon_v028.sh` regenerates prior art and must not overwrite a user-sprite import.
- Current safe build: `python3 tools/build_peon_v0217.py`. It freezes historical generator targets and versioned native packets, and rejects an unexpected generator in the Make plan. Keep native generated packets versioned as build inputs. The v17 authoring importer compiles explicit indexed cell rows; it must not resize or overwrite a reference PNG.
- `references/generated/user_player_v0211` and the native `peon_sprite_redesign_v030` packets contain procedural replacement art. They are historical artifacts, never current hero fallback sources. Approved large raster masters are a separate, explicitly lossy import; do not label them recovered user-native sprites.
- Check GBC tile/palette allocation and OAM limits before changing the rendering path. Report real hardware constraints concretely; do not use them to justify an unrelated redesign.
- Use bounded, relevant emulator checks and report what was actually observed. A successful build or gallery pixel check does not prove in-game visual quality.

## Respect the user's time and usage

- Investigate the source files and minimal integration path first. Avoid new image generation, repeated broad tests and unnecessary approval rounds.
- If the exact source is unavailable, complete independent diagnosis and request only the missing original file or repository path. Do not publish another cosmetic-only release as if the requested sprites were implemented.
