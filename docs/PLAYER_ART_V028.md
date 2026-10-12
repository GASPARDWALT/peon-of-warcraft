# Native Orc apprentice artwork, v0.2.8

The three playable classes now share an original young Orc silhouette: green
skin, pointed ears, a broad jaw, small tusks, worn clothes and modest equipment.
Their faces and equipment are drawn with explicit native pixel clusters rather
than shrinking a large illustration. The Shaman carries a crude mace, wooden
shield and belt totem; the Warrior carries a simple two-handed axe without a shield;
the Warlock wears a short cloth hood and apprentice robe and casts with a wand.
They have no heroic helmet, cape or giant shoulder armor.

The actual engine sizes remain 16×16 world sprites, 56×56 front/Character art
and 48×48 rear combat art. Each class has twelve independently authored world
frames (four directions × idle/two steps) and three combat poses. Accessories
remain on the same anatomical side instead of swapping hands through a
mirrored render. The face is visible in front/profile, and rear combat art
faces the enemy in three quarters.

`tools/build_peon_player_classes_v028.py` writes its native input sheets and
raw tile bytes to `gfx/peon_classes_v028/`. It keeps the established tile
ordering: row-major world and Character portraits, column-major battle
pictures. All four binaries retain their existing byte sizes; no species,
sprite, move, event or saved actor field is added. The existing RGB555 skin,
leather and outline palettes remain shared by the three classes. The Warlock
has a brown novice robe; purple belongs to the class-selection background.

Reusable RGBA PNGs are in `references/generated/polish_v028/classes/`.
Every native frame is exported separately with binary alpha (0 or 255), along
with transparent contact sheets and APNG motion previews. The enlarged PNGs
use nearest-neighbor pixels. GIF reviews have an explicit paper background;
they are source-art previews, not emulator screenshots. In total the source
set contains 54 native transparent frames and 18 motion previews, plus their
enlarged images and sheets.

The same generator also emits two reusable 16×16 weapon icons under
`gfx/peon_classes_v028/item_icons/`: `wand.2bpp` and `axe.2bpp`, each exactly
four row-major tiles (64 bytes), with matching indexed PNG and RGB555 palette.
Their transparent native/enlarged PNGs are in `classes/item_icons/`. These are
the actual class weapon silhouettes, so Bags can display a wand for Warlock
and a two-handed axe for Warrior instead of reusing the Shaman mace.

The Warlock's rear release pose aligns the wand tip at local `(16,4)`, physical
`(32,52)` with the established rear anchor `(16,48)`. Its anticipation pose
uses local `(7,5)` and its idle pose `(6,15)`. This keeps the ranged launch above
the enemy health display. The actual spell choreography is handled separately
by the battle animation code.

The class graphics upload helpers suspend `hBGMapMode` before selecting VRAM
bank 0, restore the original VRAM bank and then restore the caller's map mode.
World, front and Character art use Crystal's normal VBlank tile transfer. The
visible battle backpose uses a complete general-DMA transfer during VBlank,
with interrupts briefly deferred from the preceding visible scanlines. A
whole rear picture changes together instead of displaying mixed limbs from
two poses. This also prevents a map transfer from replacing the upload's
VRAM bank or DMA descriptor. The class-selection preview's background color follows
its blue/red/purple body tint; the saved-character page retains paper.

`tools/validate_peon_class_graphics_v028.py --expected-sha HASH` verifies three
normal class routes, real movement, Character/menu/door restores, actual
combat poses and cold native battery Continue. Its read-only checks compare
the exact native VRAM bytes, RGB555 framebuffer pixels and the four OAM tile
offsets `(0,0), (8,0), (0,8), (8,8)` for every direction and step. It verifies
that class uploads preserve enemy art, fonts, HUD, rank emblem and companions
and restore the caller's VRAM bank and background map mode. Normal tests
never edit RAM, inject poses, load emulator states or open a user's save.

Source inspiration includes the supplied class-master sheet and the accessible
WoW Shadow Bolt and novice wooden staff icons. The external references are
retained in `classes/source/`; they are references only and are not copied into
the new sprites. `asset_manifest.json` records the reference URLs and each
native binary's size, hash and palette. A source preview does not establish
in-game rendering: the separate `validation.json` records the tested ROM hash
and actual runtime frames after root builds the candidate.
