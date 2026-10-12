# v0.2.8 class themes and decorative quest markers

Class selection has a fixed blue Shaman page, red Warrior page and violet
Warlock page. Native black regular text remains readable; only mentor names
use the bold font cache. The green-skin/brown-leather preview uses its own
palette5; its transparent background colour follows the class page.

The frame, names, heading and controls are built once. Cursor changes replace
only the description, cursor cells and preview with background publication
paused. This avoids both blank panels and temporary white cells from repainting
bold name attributes during the raster. Native spaces use palette colour1;
matching colours0/1 gives every blank and glyph cell the selected class tint.
The complete page uses Crystal's normal attribute/tile/palette publication.
The tint is limited to selection; accepted classes return to native world and
dialogue palettes. No new persistent RAM, save fields or class IDs are added.

The three existing variable marker sprites ($fd, $fe, $ff) are decorative on
TILESET_PEON. IsNPCAtCoord skips only these sprites there, for both movement
and A-button targeting. The real quest giver remains solid and talkable from
adjacent cells, including the floating marker cell immediately north of them.
The existing Warlock companion pass-through rule remains unchanged. Other
NPCs, map collision tiles and non-Peon variable sprites retain native behavior.

The saved quest state remains authoritative:

| Progress | Visible glyph |
| --- | --- |
| Quest available | Yellow ! |
| Accepted, objectives incomplete | Gray ? |
| Objectives complete, ready to turn in | Yellow ? |
| Finished with no next quest/reward | Existing marker retirement rule |

HUD and fullscreen menu-frame tile uploads now mask hBGMapMode before changing
VBK. Interrupts remain enabled for the engine's native Get2bpp upload. VBK is
restored before the original map publication mode, preventing VBlank's map
writer from redirecting pending graphics into the wrong VRAM bank.

Run the targeted ordinary-input validation against the exact compiled ROM:

```sh
PYTHONPATH=/workspace/toolchains/pyboy-preview python3 tools/validate_peon_markers_ui_v028.py --expected-rom-sha256 SHA256
```

The report and actual emulator captures go only into
`references/generated/polish_v028/ui_markers/`. The normal route checks all
three class themes, repeated cursor transitions, real NPC targeting from four
sides, walking into marker cells, Gornek/Lazy Peons/cactus quest states, actual
harvests and one-time rewards. It also observes native HUD/menu upload register
and bank preservation. There are no RAM edits, state loads or artificial quest
fixtures. A passing report is valid only for its recorded ROM SHA256.
