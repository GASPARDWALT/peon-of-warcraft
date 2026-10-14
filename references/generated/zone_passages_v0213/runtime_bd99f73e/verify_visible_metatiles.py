"""Read-only full visible tile/attribute comparison with the native packet."""
from pathlib import Path

ROOT = Path('/workspace/peon-of-warcraft')


def check(session):
    # The session uses the actual frozen map number, not a scripted fixture.
    from validate_peon_villages import MAPS
    name, width, height = MAPS[session.map()]
    folder = ROOT / 'gfx/zone_passages_v0213'
    meta = (folder / (name + '_meta.bin')).read_bytes()
    palettes = (folder / (name + '_palmap.bin')).read_bytes()
    priorities = (folder / (name + '_priority.bin')).read_bytes()
    player_x, player_y = session.position()
    origin_x, origin_y = player_x * 2 - 8, player_y * 2 - 8
    bank, blocks_address = session.sym['wOverworldMapBlocks']
    p = session.p
    base = 0x9c00 if p.memory[0xff40] & 8 else 0x9800
    scroll_x, scroll_y = p.memory[0xff43] // 8, p.memory[0xff42] // 8
    in_world_cells, engine_border_cells = 0, 0
    for y in range(18):
        for x in range(20):
            world_x, world_y = origin_x + x, origin_y + y
            if not (0 <= world_x < width * 4 and 0 <= world_y < height * 4):
                engine_border_cells += 1
                continue
            in_world_cells += 1
            block_x, tile_x = divmod(world_x, 4)
            block_y, tile_y = divmod(world_y, 4)
            block = p.memory[bank, blocks_address + (block_y + 3) * (width + 6) + block_x + 3]
            logical = meta[block * 16 + tile_y * 4 + tile_x]
            expected_attribute = (palettes[logical // 2] >> ((logical % 2) * 4)) & 15
            expected_attribute |= 128 if priorities[logical // 8] & (128 >> (logical % 8)) else 0
            address = base + ((scroll_y + y) % 32) * 32 + (scroll_x + x) % 32
            actual_tile, actual_attribute = p.memory[0, address], p.memory[1, address]
            expected_tile = logical & 127
            if logical >= 224:
                expected_tile = logical & 255
            assert actual_tile == expected_tile and actual_attribute == expected_attribute, (
                name, 'native visible metatile mismatch', x, y, world_x, world_y,
                logical, expected_tile, actual_tile, expected_attribute, actual_attribute)
    return {'all_in_world_visible_tile_ids_exact': True,
            'all_in_world_visible_palette_bank_priority_attributes_exact': True,
            'compared_native_world_cells': in_world_cells,
            'engine_filled_border_cells': engine_border_cells,
            'all360_visible_cells_exact': in_world_cells == 360,
            'viewport_origin_world_tiles': [origin_x, origin_y],
            'source': str(folder.relative_to(ROOT)),
            'method': 'Read-only native live padded map block, frozen metatile packet and PPU comparison.'}
