# Peon of Warcraft — working rules

## User artwork is the source of truth

- Import the user's supplied PNG sprites directly when the request is to implement them. Preserve the original files and record crop coordinates and source hashes.
- Follow the stated layout: base Peon, Shaman, Warrior, Warlock; world front/back/left/right at 16×16, combat front at 56×56, combat back at 48×48.
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
- Check GBC tile/palette allocation and OAM limits before changing the rendering path. Report real hardware constraints concretely; do not use them to justify an unrelated redesign.
- Use bounded, relevant emulator checks and report what was actually observed. A successful build or gallery pixel check does not prove in-game visual quality.

## Respect the user's time and usage

- Investigate the source files and minimal integration path first. Avoid new image generation, repeated broad tests and unnecessary approval rounds.
- If the exact source is unavailable, complete independent diagnosis and request only the missing original file or repository path. Do not publish another cosmetic-only release as if the requested sprites were implemented.
