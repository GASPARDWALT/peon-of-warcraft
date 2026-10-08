# Native atlas player and quest objectives

This patch uses the currently playable compact maps. It does not reproduce the
requested seven-screen Valley layout: final mountain passages and paths still
need the user's traced topology and a separate saved-coordinate migration.

The green 8×8 peon head is a readable map symbol, rather than the full 16×16
overworld sprite. Its center projects the player's current movement cell onto
the exact existing map thumbnail transform. Browsing another zone does not
display a player there. Inside the cave, the cave page uses true cave coordinates.
Inside a shared hut or inn, the outdoor page represents the player at that
interior's exact return door; walking indoors does not pretend to move outdoors.

Yellow `!` symbols appear only for accepted, unfinished actions: the sleeping
peon, each unharvested cactus, living Sarkoth, and living Yarrog. For the
medallion quest, the Valley page marks the actual cave entrance while the
discovered cave page marks Yarrog. Existing questgiver icons retain yellow `!`,
gray `?`, and yellow `?` states. No map points appear before the map is earned
or on an undiscovered page.

The overlay uses three native 8×8 OBJ tiles in bank 0 `$8000..$802f`, separate
from the atlas's signed BG tiles. Temporary OBJ palettes 6/7 are restored when
the menu closes, including the red exterior imps. At most nine icons are used;
the player has first OAM priority if nearby symbols overlap at thumbnail scale.
No persistent layout or quest flag is added or changed by the renderer.

Closing reloads Crystal's canonical standard font and text-space glyph, which
can differ from an earlier overworld font cache. Validation therefore checks
the reloaded font bytes against their native source, and checks unchanged active
terrain, allocated NPC graphics, tile attributes and visible BG palettes.
Unused text/portrait palette caches are not claimed to be byte-identical.

`geometry_manifest.json` records actual map dimensions, world objective cells,
projection lookup tables and exterior door ownership. The generated source is
`gfx/pack/peon_atlas_geometry.asm` and the native head is
`gfx/pack/peon_atlas_avatar.{png,2bpp}`. Public avatar PNGs have binary alpha.

Run `PYTHONPATH=/workspace/toolchains/pyboy-preview python
tools/validate_peon_atlas_player_objectives.py` after the shared ROM build.
`validation.json` identifies that ROM by SHA-256. Names beginning `normal_`
are captures from ordinary controls and quest progression. Names beginning
`diagnostic_` explicitly cover isolated event/coordinate fixtures and emulator
state reloads. All `_4x.png` images are nearest-neighbor magnifications of the
actual 160×144 ROM output. Hardware Chromatic validation remains separate.
