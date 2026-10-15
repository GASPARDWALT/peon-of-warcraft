#!/usr/bin/env python3
"""Build restored world artwork and illustrated masters without regeneration.

World/combat graphics, movement, collision and save formats are retained.
Native packets are versioned build inputs.
"""
from build_peon_art_repair_v0212 import main


if __name__ == '__main__':
    main('references/generated/v0219', (
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
        'gfx/world_redraw_v0217',
        'gfx/class_portraits_v0218',
        'gfx/welcome_scenes_v0218',
        'gfx/selection_labels_v0218',
        'gfx/class_portraits_v0219',
        'gfx/world_readability_v0219',
        'gfx/large_masters_v0219',
    ))
