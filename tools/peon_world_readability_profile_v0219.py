"""World-only OBJ palette contract for the restored complete v19 artwork.

Slots 0 and 4 remain native HUD/quest colors. Slot 3 reserves actual ivory
for animal eyes, tusks and bone, rather than turning all highlights tan.
The matching PEON-map palette upload is separate from battle palettes.
"""
from copy import deepcopy
from import_peon_world_redraw_v0217 import PALETTES as PRIOR_PALETTES

PALETTES = deepcopy(PRIOR_PALETTES)
PALETTES[3] = [(31, 31, 31), (25, 23, 17), (15, 9, 4), (1, 1, 1)]
