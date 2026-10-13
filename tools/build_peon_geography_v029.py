#!/usr/bin/env python3
"""Prepare real, irregular mountain collision for the seven Valley zones.

Preview is the default. --apply is a separate explicit integration step after
the v0.2.8 checkpoint. IDs/dimensions, events, NPC positions and portal pairs
stay stable. New cliff modules compose existing 16x16 cliff/soil quadrants;
there are no new 8x8 graphics or palette allocations. Old exterior cells made
solid are enumerated with reachable safe landing suggestions for Continue.
"""
from collections import deque
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

import build_peon_valley_zones_v025 as zones
import build_peon_wayfinding_v025 as paths

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/geography_v029'
BASE = 'e996663'
TARGETS = tuple(zones.ZONE_NAMES.values())
FLOOR_IDS = {0, 8, 38}
MASK_NAMES = {1: 'nw', 2: 'ne', 3: 'north', 4: 'sw', 5: 'west',
              6: 'ne_sw', 7: 'nw_ne_sw', 8: 'se', 9: 'nw_se', 10: 'east',
              11: 'nw_ne_se', 12: 'south', 13: 'nw_sw_se', 14: 'ne_sw_se'}
SPAWNS = [
    {'kind': 'EarthSpirit', 'map': 'PeonValleyCrossroads', 'xy': [3, 5],
     'species': 'ONIX', 'level': 2, 'object_index': 1, 'behavior': 'neutral recruitment source'},
    {'kind': 'OrcGrunt', 'map': 'PeonHanazuaCamp', 'xy': [3, 6],
     'species': 'MACHAMP', 'level': 2, 'object_index': 1, 'behavior': 'neutral recruitment source'},
    {'kind': 'EarthSpiritFuture', 'map': 'PeonCaveApproach', 'xy': [7, 7],
     'species': 'ONIX', 'level': 2, 'object_index': None, 'behavior': 'optional later recruitment node'},
    {'kind': 'KolkarArcher', 'map': 'PeonValleyExit', 'xy': [3, 5],
     'species': 'PONYTA alias pending root integration', 'level': 7,
     'object_index': 2, 'behavior': 'hostile pack helper owned by combat agent'},
    {'kind': 'KolkarRaider', 'map': 'PeonValleyExit', 'xy': [7, 5],
     'species': 'RAPIDASH alias pending root integration', 'level': 8,
     'object_index': 3, 'behavior': 'hostile pack helper owned by combat agent'},
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def original(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def event_rows(name, kind):
    return paths.events(name, kind)


def actors(name):
    result = []
    for index, row in enumerate(event_rows(name, 'object_event'), 1):
        parts = [p.strip() for p in row['arguments'].split(',')]
        if parts[0] == 'SPRITE_NONE':
            continue
        result.append(row | {'index': index, 'sprite': parts[0], 'movement': parts[1],
                             'marker': parts[0].startswith('SPRITE_PEON_QUEST_')})
    return result


def neighbors(cell):
    x, y = cell
    return ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))


def body_footprint(actor):
    x, y = actor['xy']
    if actor['movement'] == 'SPRITEMOVEDATA_WALK_LEFT_RIGHT':
        return {(x - 1, y), (x, y), (x + 1, y)}
    if actor['movement'] == 'SPRITEMOVEDATA_WALK_UP_DOWN':
        return {(x, y - 1), (x, y), (x, y + 1)}
    return {(x, y)}


def additions(name):
    # Cell precision deliberately avoids moving the legacy large-map portals.
    # These small outer ledge indentations supplement the original escarpment.
    if name == 'TheDen':
        return {(x, y) for x in range(8, 16) for y in (2,)} | {
            (20, 2), (21, 2), (20, 3), (21, 3), (20, 8), (21, 8),
            (21, 9), (20, 12), (21, 12), (21, 13), (16, 16), (16, 17)}
    if name == 'ValleyOfTrials':
        return {(x, y) for x in range(2, 6) for y in range(2, 6)} | {
            (20, 2), (21, 2), (28, 2), (29, 2), (28, 3), (29, 3),
            (28, 10), (29, 10), (29, 11), (28, 14), (29, 14), (29, 15),
            (26, 14), (27, 14)} | {(x, y) for x in range(2, 10) for y in (20, 21)} | {
            (24, 20), (25, 20), (24, 21), (25, 21)}
    if name == 'PeonValleyCrossroads':
        return {(6, 2), (7, 2), (2, 6), (2, 7), (3, 7)}
    if name == 'PeonHanazuaCamp':
        return {(4, 2), (5, 2), (5, 3), (2, 7)}
    if name == 'PeonSarkothBasin':
        return {(7, 4), (7, 5), (2, 5), (2, 6)}
    if name == 'PeonCaveApproach':
        return {(2, 4), (2, 5), (7, 4), (7, 5)}
    if name == 'PeonValleyExit':
        return {(4, 2), (5, 2), (2, 6), (2, 7), (3, 7)}
    return set()


def protected_cells(name):
    keep = set()
    for row in event_rows(name, 'warp_event') + event_rows(name, 'bg_event') + event_rows(name, 'coord_event'):
        cell = tuple(row['xy'])
        keep.add(cell); keep.update(neighbors(cell))
    for actor in actors(name):
        for x, y in body_footprint(actor):
            keep.update((x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3)
                        if abs(dx) + abs(dy) <= 2)
    for spawn in SPAWNS:
        if spawn['map'] == name:
            x, y = spawn['xy']
            keep.update((x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3)
                        if abs(dx) + abs(dy) <= 2)
    return keep


def build_tables():
    # The v028 foundation is byte-exact; append modules rather than changing
    # any published block meaning. Mask bit order is NW, NE, SW, SE.
    foundation = (ROOT / 'data/tilesets/peon_metatiles.bin').read_bytes()[:53 * 16]
    assert len(foundation) == 53 * 16
    source = (ROOT / 'data/tilesets/peon_collision.asm').read_text().splitlines(True)
    first = []
    count = 0
    for line in source:
        first.append(line)
        if 'tilecoll' in line:
            count += 1
        if count == 53:
            break
    assert count == 53
    cliff, soil = foundation[16:32], foundation[38 * 16:39 * 16]
    meta = bytearray(foundation)
    collision = ''.join(first)
    for mask in range(1, 15):
        for cell in range(16):
            quadrant = (cell // 4 // 2) * 2 + (cell % 4 // 2)
            meta.append(cliff[cell] if mask & (1 << quadrant) else soil[cell])
        values = ['WALL' if mask & (1 << q) else 'FLOOR' for q in range(4)]
        collision += '\ttilecoll ' + ', '.join(values) + f' ; {52+mask:02x} geography_cliff_{MASK_NAMES[mask]}\n'
    rows = paths.collision_rows(collision)
    assert len(rows) == 67 and len(meta) == 67 * 16
    assert all(row == ('FLOOR',) * 4 for row in (rows[0], rows[8], rows[38]))
    return bytes(meta), collision.encode(), rows


def collide(data, name, rows, cell):
    width, height = zones.DIMS[name]
    x, y = cell
    if not (0 <= x < width * 2 and 0 <= y < height * 2):
        return 'WALL'
    return rows[data[y // 2 * width + x // 2]][y % 2 * 2 + x % 2]


def reached(data, name, rows, occupied=()):
    seed = tuple(event_rows(name, 'warp_event')[0]['xy'])
    assert collide(data, name, rows, seed) != 'WALL'
    seen, queue = {seed}, deque([seed])
    occupied = set(occupied)
    while queue:
        for cell in neighbors(queue.popleft()):
            if cell not in seen and cell not in occupied and collide(data, name, rows, cell) != 'WALL':
                seen.add(cell); queue.append(cell)
    return seen


def build_maps(rows):
    result, proposed = {}, {}
    for name in TARGETS:
        data = bytearray(original(f'maps/{name}.blk'))
        width, height = zones.DIMS[name]
        keep, requested = protected_cells(name), additions(name)
        wanted = set()
        skipped = []
        for cell in sorted(requested):
            x, y = cell
            block = data[y // 2 * width + x // 2]
            if cell in keep:
                skipped.append({'xy': list(cell), 'reason': 'NPC/quest/portal/aggro/anticipated-spawn approach protected'})
            elif block not in FLOOR_IDS:
                skipped.append({'xy': list(cell), 'reason': 'Existing road, decorative silhouette, structure or wall preserved'})
            else:
                wanted.add(cell)
        for block_pos in range(len(data)):
            bx, by = block_pos % width, block_pos // width
            mask = sum(1 << q for q in range(4)
                       if (bx * 2 + q % 2, by * 2 + q // 2) in wanted)
            if mask:
                data[block_pos] = 1 if mask == 15 else 52 + mask
        if name == 'PeonValleyExit':
            # Keep ivory vertical fortification only at the eastern gate.
            # The rest of the perimeter belongs to the red-annotated mountain.
            for pos, block in enumerate(data):
                x, y = pos % width, pos // width
                if block == 33 and x != 4:
                    data[pos] = 1
        result[name] = bytes(data)
        proposed[name] = {'requested_cells': [list(p) for p in sorted(requested)],
                          'protected_or_existing_decor_cells_skipped': skipped,
                          'actual_new_wall_cells': [list(p) for p in sorted(wanted)]}
    return result, proposed


def geometry_checks(maps, rows, proposed):
    report, spawns = {}, []
    for name, data in maps.items():
        width, height = zones.DIMS[name]
        old = original(f'maps/{name}.blk')
        visible = actors(name)
        occupied = set().union(*(body_footprint(a) for a in visible if not a['marker'])) if visible else set()
        future = [p for p in SPAWNS if p['map'] == name]
        occupied |= {tuple(p['xy']) for p in future}
        walk = reached(data, name, rows)
        with_bodies = reached(data, name, rows, occupied)
        for kind in ('warp_event', 'bg_event'):
            for row in event_rows(name, kind):
                cell = tuple(row['xy'])
                if kind == 'warp_event':
                    assert cell in walk and cell in with_bodies, (name, kind, cell, 'Portal route blocked')
                else:
                    assert any(p in with_bodies for p in neighbors(cell)), (name, kind, cell)
        for actor in visible:
            cell = tuple(actor['xy'])
            assert collide(data, name, rows, cell) != 'WALL', (name, actor)
            assert any(p in with_bodies for p in neighbors(cell)), (name, actor, 'Cannot interact')
        for spawn in future:
            cell = tuple(spawn['xy'])
            assert collide(data, name, rows, cell) == 'FLOOR', (name, spawn, 'Spawn is not floor')
            assert any(p in with_bodies for p in neighbors(cell)), (name, spawn, 'No ordinary approach')
            assert not any(tuple(w['xy']) == cell for w in event_rows(name, 'warp_event'))
            assert not any(cell in body_footprint(a) for a in visible if not a['marker'])
            spawns.append(spawn | {'cell_is_native_floor': True,
                                   'approaches_reachable_with_all_other_bodies': [list(p) for p in neighbors(cell) if p in with_bodies],
                                   'map_authored_object_slots': len(event_rows(name, 'object_event')),
                                   'placeholder_slot_replacement_avoids_index_shift': spawn['object_index'] == 1})
        dangerous = {tuple(r['xy']) for r in event_rows(name, 'coord_event')}
        portals = {tuple(r['xy']) for r in event_rows(name, 'warp_event')}
        all_actor_cells = {tuple(r['xy']) for r in visible}
        safe = {p for p in with_bodies if collide(data, name, rows, p) == 'FLOOR'
                and p not in dangerous and p not in portals and p not in all_actor_cells}
        assert safe
        changed = []
        for y in range(height * 2):
            for x in range(width * 2):
                cell = (x, y)
                before, after = collide(old, name, rows, cell), collide(data, name, rows, cell)
                if before == after:
                    continue
                assert before == 'FLOOR' and after == 'WALL'
                nearest = min(safe, key=lambda p: (abs(x - p[0]) + abs(y - p[1]), p[1], p[0]))
                changed.append({'xy': [x, y], 'old_collision': before, 'new_collision': after,
                                'safeLandingSuggested': list(nearest),
                                'landing_manhattan_distance': abs(x - nearest[0]) + abs(y - nearest[1]),
                                'landing_reachable_from_actual_portal': True,
                                'landing_is_floor_not_warp_actor_or_aggro': True})
        assert {tuple(c['xy']) for c in changed} == {tuple(p) for p in proposed[name]['actual_new_wall_cells']}
        mountain = {(x, y) for y in range(height * 2) for x in range(width * 2)
                    if data[y // 2 * width + x // 2] in (1, 33)
                    or (data[y // 2 * width + x // 2] >= 53
                        and collide(data, name, rows, (x, y)) == 'WALL')}
        connected = {p for p in mountain if p[0] in (0, width * 2 - 1)
                     or p[1] in (0, height * 2 - 1)}
        todo = deque(connected)
        while todo:
            for p in neighbors(todo.popleft()):
                if p in mountain and p not in connected:
                    connected.add(p); todo.append(p)
        assert {tuple(c['xy']) for c in changed} <= connected, (name, 'Floating new wall island')
        report[name] = {'map_id': zones.MAP_NUMBERS[name], 'blocks': [width, height],
                        'old_blocks_sha256': digest(old), 'proposed_blocks_sha256': digest(data),
                        'reachable_cells': len(walk), 'reachable_with_all_current_and_planned_bodies': len(with_bodies),
                        'all_portals_and_quest_npcs_have_actual_approaches': True,
                        'new_blocked_cells_requiring_continue_guard': changed,
                        'changed_block_count': sum(a != b for a, b in zip(old, data)),
                        'immutable_actor_event_warp_coordinates': True,
                        'all_new_walls_connected_to_actual_outer_mountain_rim': True,
                        'painted_roads_preserved': all(a == b for a, b in zip(old, data) if a in paths.ROAD_IDS)}
    return report, spawns


def emit_views(maps, meta):
    sheet = Image.open(ROOT / 'gfx/tilesets/peon.png').convert('L')
    attrs = (ROOT / 'gfx/tilesets/peon_palette_map.bin').read_bytes()
    folder = OUT / 'proposed'
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in maps.items():
        width, height = zones.DIMS[name]
        palettes = paths.palettes('ValleyOfTrials' if name in zones.NEW_NAMES else name)
        native = Image.new('RGB', (width * 32, height * 32))
        for pos, block in enumerate(data):
            for j, tid in enumerate(meta[block * 16:block * 16 + 16]):
                index = tid if tid < 96 else tid - 32
                raw = sheet.crop((index % 16 * 8, index // 16 * 8,
                                  index % 16 * 8 + 8, index // 16 * 8 + 8))
                pal = (attrs[tid // 2] >> (tid % 2 * 4)) & 7
                image = Image.new('RGB', (8, 8))
                for y in range(8):
                    for x in range(8):
                        image.putpixel((x, y), tuple(palettes[pal][(255 - raw.getpixel((x, y))) // 85]))
                native.paste(image, (pos % width * 32 + j % 4 * 8, pos // width * 32 + j // 4 * 8))
        native.save(folder / (name + '_proposed_native_pixels.png'))
        native.resize((width * 64, height * 64), Image.Resampling.NEAREST).save(
            folder / (name + '_proposed_2x.png'))


def make_patch(files):
    path = Path('/tmp/peon_v029_geography_hooks.patch')
    with tempfile.TemporaryDirectory(prefix='peon_geo_patch_') as folder:
        staging = Path(folder)
        subprocess.run(['git', 'init', '-q', str(staging)], check=True)
        (staging / '.gitattributes').write_text('*.blk binary\n*.bin binary\n')
        for name in files:
            dest = staging / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT / name).read_bytes())
        subprocess.run(['git', '-C', str(staging), 'add', '.'], check=True)
        for name, data in files.items():
            (staging / name).write_bytes(data)
        patch = subprocess.check_output(['git', '-C', str(staging), 'diff', '--binary', '--', 'maps', 'data'])
        path.write_bytes(patch)
        subprocess.run(['git', '-C', str(staging), 'restore', '--worktree', '.'], check=True)
        subprocess.run(['git', '-C', str(staging), 'apply', '--check', str(path)], check=True)
        subprocess.run(['git', '-C', str(staging), 'apply', str(path)], check=True)
        assert all((staging / name).read_bytes() == data for name, data in files.items())
    return {'path': str(path), 'sha256': digest(patch), 'bytes': len(patch),
            'git_binary_patch_apply_check_passed_in_temporary_fixture': True,
            'patch_never_applied_to_live_checkout': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Apply only after root has checkpointed v028.')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = ['data/tilesets/peon_metatiles.bin', 'data/tilesets/peon_collision.asm',
              'gfx/tilesets/peon.png', 'gfx/tilesets/peon_palette_map.bin'] + [f'maps/{n}.blk' for n in TARGETS]
    before = {name: digest((ROOT / name).read_bytes()) for name in inputs}
    meta, collision, rows = build_tables()
    maps, proposed = build_maps(rows)
    report, spawns = geometry_checks(maps, rows, proposed)
    files = {f'maps/{name}.blk': data for name, data in maps.items()}
    files.update({'data/tilesets/peon_metatiles.bin': meta, 'data/tilesets/peon_collision.asm': collision})
    patch = make_patch(files)
    emit_views(maps, meta)
    manifest = {'passed': True, 'baseline_ref': BASE, 'preview_only': not args.apply,
                'native_patterns_unchanged': 192, 'metatile_count_after_apply': 67,
                'new_mixed_cliff_metatile_ids': {str(mask): 52 + mask for mask in range(1, 15)},
                'zero_new_graphics_palette_or_sram_bytes': True,
                'ids_dimensions_npcs_quests_portals_roads_preserved': True,
                'continuelanding_guard_required_before_playable_release': True,
                'changed_collision_cell_count': sum(len(r['new_blocked_cells_requiring_continue_guard']) for r in report.values()),
                'maps': report, 'requested_contours_and_filtered_cells': proposed,
                'planned_spawn_sites': spawns, 'patch': patch,
                'screenshots_are_uncompiled_proposal_views_not_runtime': True,
                'native_files_written': args.apply}
    (OUT / 'proposed_geometry.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (OUT / 'safe_spawn_sites.json').write_text(json.dumps({'passed': True, 'sites': spawns}, indent=2) + '\n')
    (OUT / 'changed_collision_cells.json').write_text(json.dumps({name: r['new_blocked_cells_requiring_continue_guard']
                                                               for name, r in report.items()}, indent=2) + '\n')
    if args.apply:
        for name, data in files.items():
            (ROOT / name).write_bytes(data)
    else:
        assert all(digest((ROOT / name).read_bytes()) == value for name, value in before.items())
    print(json.dumps({'passed': True, 'preview_only': not args.apply,
                      'changed_collision_cells': manifest['changed_collision_cell_count'],
                      'native_patterns': 192, 'metatiles': 67, 'patch': patch['path'],
                      'native_files_written': args.apply}))


if __name__ == '__main__':
    main()
