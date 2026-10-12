#!/usr/bin/env python3
"""Author rounded Horde interiors and wall-only banners for v0.2.8.

The 47 published metatile meanings remain stable. Five solid-wall metatiles
append indices 47..51 and a foot-door metatile52 without a saved-ID change. All world map arrays, existing
collision rows, map dimensions, event positions, doors, plants and opening-palm
geometry are preserved. Source previews are compiler views, not screenshots.
"""
from collections import deque
from io import BytesIO
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess

from PIL import Image, ImageDraw

import build_peon_environment_v026 as previous
import build_peon_environment_v025 as art
import build_peon_valley_zones_v025 as zones
import build_peon_wayfinding_v025 as paths
from peon_horde_emblem_v028 import horde_emblem_indices, emit as emit_emblem

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/polish_v028/environment'
BASE = 'e996663'
INTERIORS = ('PeonOrcHut', 'PeonTrollHut', 'PeonOrcInn', 'PeonTrollInn')
EDITED_ROOMS = INTERIORS + ('GrommashHold',)
APPENDED_NAMES = ('round_hut_wall_nw', 'round_hut_wall_ne',
                  'round_hut_wall_sw', 'round_hut_wall_se', 'round_hut_wall',
                  'round_hut_foot_door')
NAMES = list(art.NAMES[:47]) + list(APPENDED_NAMES)


def baseline(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def warm_wall_tile():
    # Large quiet hide panels, leather ties and one light seam: a small room
    # needs a legible contour rather than repeated tiny outdoor rock caps.
    image = Image.new('L', (8, 8), 2)
    d = ImageDraw.Draw(image)
    # Short leather crease: highlight and shadow communicate volume without
    # the older regular polka-dot surface or adding a second wall pattern.
    d.line((1, 3, 3, 3), fill=1)
    d.line((2, 4, 4, 4), fill=3)
    return art.Tile(image, 5, Image.new('L', (8, 8), 255), 'warm_hide_wall')


def corner_wall(tile, horizontal=False, vertical=False):
    canvas = art.Canvas()
    for y in range(4):
        for x in range(4):
            canvas.put(tile, x, y)
    # Two 8x8 cells form each diagonal bevel. Outside the room is dark, never
    # drawn as walkable floor; all four movement cells remain WALL.
    d = ImageDraw.Draw(canvas.indices)
    d.polygon([(0, 0), (23, 0), (0, 23)], fill=3)
    d.line((0, 23, 23, 0), fill=1)
    d.line((0, 24, 24, 0), fill=3)
    d.line((4, 23, 23, 4), fill=1)
    if horizontal:
        canvas.indices = canvas.indices.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if vertical:
        canvas.indices = canvas.indices.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    canvas.mask = Image.new('L', (32, 32), 255)
    canvas.palettes = Image.new('L', (4, 4), 5)
    return canvas


def build_blocks():
    # This calls only the old drawing functions, never an old builder main()
    # or output writer. The current published art stays the source for nature,
    # all exterior doors, fire allocation and actual directional roads.
    blocks, den, library = previous.build_blocks()
    emblem = horde_emblem_indices()
    for i in range(4):
        pixels = emblem.crop((i % 2 * 8, i // 2 * 8,
                              i % 2 * 8 + 8, i // 2 * 8 + 8))
        library[f'emblem_{i}'] = art.Tile(pixels, 6, Image.new('L', (8, 8), 255), f'emblem_{i}')
    wall = warm_wall_tile()
    library[wall.name] = wall
    # No emblem on rugs. A narrow stitched red runner is deliberately quiet.
    blocks[5] = art.array([['cloth'] * 4 for _ in range(4)], library)
    # The cloth symbol now hangs against the same hide/timber wall as rooms.
    # It is not a freestanding pole or a glyph repeated along the floor.
    w = wall.name
    blocks[6] = art.array([
        [w, 'crossbar', 'crossbar', w],
        [w, 'emblem_0', 'emblem_1', w],
        [w, 'emblem_2', 'emblem_3', w],
        [w, 'cloth_foot_l', 'cloth_foot_r', w],
    ], library)
    # Packed earth and a single plain woven floor replace checkerboard stones
    # and repeated bed-blanket patches on the ground.
    floor = art.tile('quiet_room_floor', 5, fill=0, opaque=True)
    library[floor.name] = floor
    blocks[7] = art.array([[floor.name] * 4 for _ in range(4)], library)
    blocks[45] = blocks[7]
    # A bowl on two flared tripod legs matches the inn references more closely
    # than a straight candle-stick pole. Logs provide the existing diagonal
    # dark timber/metal silhouette; no extra tile or animation is allocated.
    blocks[34] = art.array([
        ['empty', 'fire_l', 'fire_r', 'empty'],
        ['empty', 'ember_l', 'ember_r', 'empty'],
        ['empty', 'bowl_l', 'bowl_r', 'empty'],
        ['empty', 'log_r', 'log_l', 'empty'],
    ], library)
    # Keep the Orc blankets red while sharing one cloth pattern with banners.
    # Their pillow and bed feet retain a proper outlined furniture silhouette.
    blocks[40] = art.array([
        ['empty', 'pillow', 'pillow', 'empty'],
        ['empty', 'cloth', 'cloth', 'empty'],
        ['empty', 'cloth', 'cloth', 'empty'],
        ['empty', 'bone_foot_l', 'bone_foot_r', 'empty'],
    ], library)
    # Darkspear wall talisman uses the existing continuous bone tips rather
    # than two nearly identical bespoke pattern variants.
    blocks[46] = art.array([
        ['bone_tip_l', 'crossbar', 'crossbar', 'bone_tip_r'],
        ['post', 'skull_0', 'skull_1', 'post'],
        ['post', 'skull_2', 'skull_3', 'post'],
        ['bone_foot_l', 'empty', 'empty', 'bone_foot_r'],
    ], library)
    blocks += [corner_wall(wall), corner_wall(wall, horizontal=True),
               corner_wall(wall, vertical=True),
               corner_wall(wall, horizontal=True, vertical=True),
               art.array([['post', 'crossbar', 'crossbar', 'post'],
                          ['post', w, w, 'post'], ['post', w, w, 'post'],
                          ['post', 'crossbar', 'crossbar', 'post']], library)]
    # Reuse the exact established dark arch and step: this additional door
    # metatile uses zero additional patterns and affects only house interiors.
    inside_door = art.Canvas()
    for y in range(4):
        for x in range(4):
            inside_door.put(floor, x, y)
    old_door = blocks[4].crop((16, 16, 32, 32))
    for j, item in enumerate(old_door.tiles()):
        inside_door.put(item, 2 + j % 2, 2 + j // 2)
    blocks.append(inside_door)
    assert len(blocks) == 53
    return blocks, den, library


def room_layout(name):
    if name == 'GrommashHold':
        data = bytearray(baseline('maps/GrommashHold.blk'))
        data[1 * 8 + 6] = 34  # Previously solid right standard: fire basin.
        return bytes(data)
    data = [51] * 30
    data[0], data[5], data[24], data[29] = 47, 48, 49, 50
    # Short chamfered corners read as a circle on a 6x5-block Crystal grid.
    # The original traversable 4x3 center remains the exact same footprint.
    for y in (1, 2, 3):
        for x in (1, 2, 3, 4):
            data[y * 6 + x] = 7 if 'Orc' in name else 45
    data[3 * 6 + 2] = 52  # Same foot exit(5,7), with an actual visible arch.
    if name.endswith('Inn'):
        bed = 40 if 'Orc' in name else 43
        table = 41 if 'Orc' in name else 44
        for x, y in ((1, 1), (1, 3), (4, 3)):
            data[y * 6 + x] = bed
        data[1 * 6 + 4] = 34  # Fully visible fire-basin alcove beside bunks.
        data[2 * 6 + 4] = table  # Original BGEVENT_READ at (8,4).
        data[2 * 6] = 34  # Second warm basin, replacing a blocked wall panel.
        data[3] = 6  # One hanging banner on the north wall.
    elif 'Orc' in name:
        data[3] = 6
        data[2 * 6 + 2] = data[2 * 6 + 3] = 5
    else:
        data[3] = 46  # One Darkspear wall talisman, not a floating floor prop.
    if not name.endswith('Inn'):
        data[2 * 6] = data[2 * 6 + 5] = 34
    return bytes(data)


def collision_rows():
    source = baseline('data/tilesets/peon_collision.asm').decode()
    source += ''.join(f'\ttilecoll WALL, WALL, WALL, WALL ; {47+i:02x} {name}\n'
                      for i, name in enumerate(APPENDED_NAMES[:5]))
    source += '\ttilecoll WARP_PANEL, WARP_PANEL, WARP_PANEL, WARP_PANEL ; 34 round_hut_foot_door\n'
    return source


def geometry_checks(room_arrays):
    rows = [line.split('tilecoll', 1)[1].split(';', 1)[0].replace(' ', '').split(',')
            for line in collision_rows().splitlines() if 'tilecoll' in line]
    assert len(rows) == 53 and all(row == ['WALL'] * 4 for row in rows[47:52])
    assert rows[52] == rows[16] == ['WARP_PANEL'] * 4
    rooms = {}
    for name in INTERIORS:
        new = room_arrays[name]
        old = baseline(f'maps/{name}.blk')
        assert len(new) == len(old) == 30
        walk = {(x, y) for y in range(10) for x in range(12)
                if rows[new[y // 2 * 6 + x // 2]][(y % 2) * 2 + x % 2] != 'WALL'}
        # All old traversable cells still work, even old battery coordinates.
        old_walk = {(x, y) for y in range(10) for x in range(12)
                    if rows[old[y // 2 * 6 + x // 2]][(y % 2) * 2 + x % 2] != 'WALL'}
        assert old_walk <= walk, (name, 'Old saved room coordinate was blocked')
        start = (5, 6)  # standing inside, one movement cell before warp(5,7)
        assert start in walk
        seen, queue = {start}, deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                cell = (x + dx, y + dy)
                if cell in walk and cell not in seen:
                    seen.add(cell); queue.append(cell)
        source = (ROOT / f'maps/{name}.asm').read_text()
        actors = paths.events(name, 'object_event', source)
        assert actors and all(tuple(actor['xy']) in seen for actor in actors), (name, actors)
        assert (5, 7) in seen and new[3 * 6 + 2] == 52
        for actor in actors:
            x, y = actor['xy']
            assert any(cell in seen for cell in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
        if name.endswith('Inn'):
            assert (2, 4) in seen, (name, 'Bedroll event has no south interaction cell')
            assert (7, 4) in seen, (name, 'Table event has no west interaction cell')
        rooms[name] = {'blocks': [6, 5], 'old_walkable_cells': len(old_walk),
                       'walkable_cells': len(walk), 'reachable_cells': len(seen),
                       'old_saved_coordinates_remain_walkable': True,
                       'all_npc_cells_and_interaction_cells_reachable': True,
                       'warp_5_7_and_facing_approach_preserved': True,
                       'sha256': digest(new)}
    for name in zones.DIMS:
        if name not in EDITED_ROOMS:
            assert (ROOT / f'maps/{name}.blk').read_bytes() == baseline(f'maps/{name}.blk'), name
    old_hold, new_hold = baseline('maps/GrommashHold.blk'), room_arrays['GrommashHold']
    assert len(new_hold) == len(old_hold) == 48
    assert [i for i, (a, b) in enumerate(zip(old_hold, new_hold)) if a != b] == [14]
    assert rows[old_hold[14]] == rows[new_hold[14]] == ['WALL'] * 4
    assert (ROOT / 'constants/map_constants.asm').read_bytes() == baseline('constants/map_constants.asm')
    # Agent peers may intentionally restyle strings, so compare event rows,
    # not the complete map script which contains interactive dialogue.
    for name in INTERIORS + ('GrommashHold',):
        now = (ROOT / f'maps/{name}.asm').read_text()
        old = baseline(f'maps/{name}.asm').decode()
        for kind in ('warp_event', 'coord_event', 'bg_event', 'object_event'):
            assert paths.events(name, kind, now) == paths.events(name, kind, old), (name, kind)
    return rooms


def emit_review(blocks, room_arrays):
    for folder in ('props', 'maps', 'before'):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    for name, ident in (('horde_wall_banner', 6), ('orc_bunk', 40), ('darkspear_bunk', 43),
                        ('orc_table', 41), ('darkspear_table', 44), ('round_hide_wall_nw', 47),
                        ('round_hide_wall_ne', 48), ('round_hide_wall_sw', 49),
                        ('round_hide_wall_se', 50), ('stitched_hide_wall', 51),
                        ('plain_red_runner', 5), ('round_hut_foot_door', 52),
                        ('inn_fire_basin_tripod', 34)):
        im = art.rgba(blocks[ident])
        if 47 <= ident <= 50:
            # Preserve dark outlines/ties. Only the exterior clipped corner
            # becomes transparent in reusable source art, never in the ROM.
            alpha = Image.new('L', (32, 32), 255)
            ImageDraw.Draw(alpha).polygon([(0, 0), (22, 0), (0, 22)], fill=0)
            if ident in (48, 50):
                alpha = alpha.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if ident in (49, 50):
                alpha = alpha.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            im.putalpha(alpha)
        im.save(OUT / 'props' / f'{name}_native.png')
        im.resize((256, 256), Image.Resampling.NEAREST).save(OUT / 'props' / f'{name}_8x.png')
    # Standalone cloth art omits the native solid wall backing so it can be
    # reused on another wall, HTML preview or concept without a brown square.
    banner = art.Canvas()
    for j in (1, 2, 5, 6, 9, 10, 13, 14):
        banner.put(list(blocks[6].tiles())[j], j % 4, j // 4)
    reusable = art.rgba(banner)
    reusable.save(OUT / 'props/horde_cloth_banner_transparent_native.png')
    reusable.resize((256, 256), Image.Resampling.NEAREST).save(
        OUT / 'props/horde_cloth_banner_transparent_8x.png')
    flame_images = []
    for phase in range(3):
        basin = art.Canvas()
        for j, item in enumerate(blocks[34].tiles()):
            basin.put(item, j % 4, j // 4)
        for j, item in enumerate(art.flame_tiles(phase)):
            basin.put(item, 1 + j, 0)
        image = art.rgba(basin)
        image.save(OUT / 'props' / f'inn_fire_basin_phase_{phase}_native.png')
        image.resize((256, 256), Image.Resampling.NEAREST).save(
            OUT / 'props' / f'inn_fire_basin_phase_{phase}_8x.png')
        flame_images.append(image)
    flame_images[0].save(OUT / 'props/inn_fire_basin_transparent.apng',
                         save_all=True, append_images=flame_images[1:],
                         duration=300, loop=0, disposal=2, blend=0)
    for name in INTERIORS + ('GrommashHold',):
        width, height = zones.DIMS[name]
        data = room_arrays.get(name, (ROOT / f'maps/{name}.blk').read_bytes())
        canvas = Image.new('RGB', (width * 32, height * 32))
        for pos, ident in enumerate(data):
            image = art.rgba(blocks[ident], paths.palettes(name), False).convert('RGB')
            canvas.paste(image, (pos % width * 32, pos // width * 32))
        canvas.save(OUT / 'maps' / f'{name}_compiler.png')
        canvas.resize((width * 128, height * 128), Image.Resampling.NEAREST).save(
            OUT / 'maps' / f'{name}_compiler_4x.png')
    # Shared wall banners are the only metatile with all four emblem patterns.
    emblem_keys = {tile.key for tile in blocks[6].tiles() if tile.name.startswith('emblem_')}
    # Canvas tiles have coordinate names, so inspect the four exact center keys.
    emblem_keys = {list(blocks[6].tiles())[j].key for j in (5, 6, 9, 10)}
    uses = [i for i, block in enumerate(blocks) if emblem_keys & {tile.key for tile in block.tiles()}]
    assert uses == [6], ('Horde emblem appears outside the wall banner', uses)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-only', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    art.NAMES = NAMES
    blocks, _, library = build_blocks()
    reduction = art.reduce_shade_variants(blocks, library)
    bank, meta, budget = art.compile_tiles(blocks)
    assert len(bank) <= 192
    arrays = {name: room_layout(name) for name in EDITED_ROOMS}
    geometry = geometry_checks(arrays)
    sheet = Image.new('P', (128, 96))
    sheet.putpalette([255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0] + [0] * 756)
    attributes = [7] * 256
    for i, item in enumerate(bank):
        sheet.paste(item.pixels, (i % 16 * 8, i // 16 * 8))
        attributes[art.native_id(i)] = item.palette | (8 if i >= 96 else 0)
    packed = bytes(attributes[i] | attributes[i + 1] << 4 for i in range(0, 256, 2))
    frames = b''.join(bytes(art.encode_2bpp(tile.pixels))
                      for phase in range(3) for tile in art.flame_tiles(phase))
    assert frames == baseline('gfx/tilesets/peon_environment_fire.bin')
    assert len(meta) == 53 * 16 and len(packed) == 128
    if not args.review_only:
        sheet.save(ROOT / 'gfx/tilesets/peon.png')
        (ROOT / 'gfx/tilesets/peon_palette_map.bin').write_bytes(packed)
        (ROOT / 'data/tilesets/peon_metatiles.bin').write_bytes(meta)
        (ROOT / 'data/tilesets/peon_collision.asm').write_text(collision_rows())
        for name, array in arrays.items():
            (ROOT / f'maps/{name}.blk').write_bytes(array)
    emit_emblem()
    emit_review(blocks, arrays)
    source = OUT / 'source'
    source.mkdir(exist_ok=True)
    reference = Path('/tmp/peon_horde_v028_ref.jpg')
    if reference.exists():
        shutil.copyfile(reference, source / 'horde_symbol_reference.jpg')
    manifest = {'passed': True, 'baseline_commit': BASE, 'review_only': args.review_only,
                'native_inputs_written': not args.review_only,
                'native_patterns': len(bank), 'pattern_budget': 192, 'metatile_count': 53,
                'old_47_collision_rows_preserved': True,
                'new_wall_metatile_ids': list(range(47, 52)), 'shade_reduction': reduction,
                'new_foot_door_metatile_id': 52, 'foot_door_collision_matches_legacy_threshold16': True,
                'rooms': geometry, 'world_and_opening_palm_map_arrays_preserved': True,
                'grommash_hold_only_solid_right_standard_becomes_fire_basin': True,
                'all_map_ids_dimensions_warps_and_actor_coordinates_preserved': True,
                'floor_crest_removed': True, 'emblem_appears_only_in_wall_banner_metatile_6': True,
                'three_inn_corner_bunks_and_two_fire_basins': True,
                'two_wall_alcove_fire_basins_per_hut': True,
                'innkeeper_table_bed_events_accessible': True,
                'fire_patterns_and_animation_ids_unchanged': True,
                'png_maps_are_compiler_views_not_runtime': True,
                'source_art_rgba_alpha_binary': True, 'save_format_changed': False,
                'art_reference_paths': ['references/zones/the_den/the_den_primary_reference.png',
                                        'references/zones/Grommash_Hold/Grommash_Hold_Cataclysm_inside.webp'],
                'horde_reference_url': 'https://wow.zamimg.com/images/wow/icons/large/inv_misc_tournaments_symbol_orc.jpg'}
    manifest_name = 'review_manifest.json' if args.review_only else 'manifest.json'
    (OUT / manifest_name).write_text(json.dumps(manifest, indent=2) + '\n')
    (OUT / 'budget_review.json').write_text(json.dumps({**budget, 'reduction': reduction}, indent=2) + '\n')
    print(json.dumps({key: value for key, value in manifest.items()
                      if key not in ('shade_reduction', 'rooms')}, indent=2))


if __name__ == '__main__':
    main()
