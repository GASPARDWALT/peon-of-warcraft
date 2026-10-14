#!/usr/bin/env python3
"""Build v0.2.13 using the established no-art-regeneration guard."""
from build_peon_art_repair_v0212 import main

if __name__ == '__main__':
    main('references/generated/v0213', (
        'gfx/native_actor_restore_v0213',
        'gfx/rock_roster_v0213',
        'gfx/canonical_decor_v0213',
        'gfx/zone_passages_v0213',
        'gfx/large_masters_v0213',
        'gfx/peon_lightning_horizontal_v0213',
        'gfx/peon_resource_hud_v0213',
        # Approved room packets retain their original compressed bytes too.
        'gfx/readable_interiors_v0212',
    ))
