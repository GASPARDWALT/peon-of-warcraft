#!/usr/bin/env python3
"""Build detailed world artwork without running historical art generators.

The v0.2.15 renderer, its nine-tile packets and save layout stay unchanged.
Both versioned world and combat packets are frozen native build inputs.
"""
from build_peon_art_repair_v0212 import main


if __name__ == '__main__':
    main('references/generated/v0216', (
        'gfx/native_actor_restore_v0213',
        'gfx/rock_roster_v0213',
        'gfx/canonical_decor_v0213',
        'gfx/zone_passages_v0213',
        'gfx/large_masters_v0213',
        'gfx/peon_lightning_horizontal_v0213',
        'gfx/peon_resource_hud_v0213',
        'gfx/readable_interiors_v0212',
        'gfx/shaman_proportions_v0214',
        'gfx/quieter_ground_v0214',
        'gfx/world_actors_v0215',
        'gfx/world_actors_v0216',
        'gfx/combat_heroes_v0216',
    ))
