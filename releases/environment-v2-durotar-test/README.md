# Durotar environment v2 — native GBC test

Playable test ROM: `peon_environment_v2_durotar_test.gbc`.
SHA-256: `7cd599fc9c19ac6f8e3f579051aa60b8036dc60069f07b357d7be419cf107425`.

Start opens the existing title menu; choose NEW GAME with A. The dedicated ROM
starts in PeonEnvironmentTest with an existing native Peon test avatar.
Move with the D-pad and inspect the guide/chest with A.

Three areas (12 × 10 native blocks each):
- Test: dirt, red sand, cracked earth, connected paths and cactus collisions.
- Annex: full 64 × 64 hut/cave entrances, palisades, banner, brazier and animated fire.
- Cave: terrain transitions, a joined dirt/transition/red-sand strip, rocks and bones.

Passages use the existing directional carpet/door behavior:
- Test east edge (21,9): RIGHT to Annex.
- Annex west edge (2,9): LEFT to Test.
- Annex hut (10,7) and cave (18,7): UP to the shared inspection room.
- Inspection-room exits (6,17) and (18,17): DOWN to their respective entrances.
The Annex chest at (13,13) can be inspected from (13,14), facing UP; it gives one
Potion while the bag contains none. It adds no new saved event field.

Build: `python3 tools/build_peon_environment_v2.py`.
Existing graphics: `python3 tools/build_peon_environment_v2.py --no-import`.
Normal title/intro build: add `--normal`.

25 ordinary-control checks passed on this exact binary. Native scene captures
and detailed reports: `references/generated/map_tests/runtime/`.
Import/source inventories, exclusions, engine changes and next The Den step:
`docs/ENVIRONMENT_V2_DUROTAR_TEST.md`.

Header: CGB-only, 2 MiB, MBC3 + RTC + 32 KiB RAM + battery.
Physical ModRetro cartridge and real RTC/battery behavior are untested.
The supplied transition edges retain their original visible color/texture seams;
this fixture exposes them for review before constructing The Den.
