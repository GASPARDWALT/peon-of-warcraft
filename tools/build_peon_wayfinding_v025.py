#!/usr/bin/env python3
"""Add readable, save-safe footpaths to the retained v0.2.4 world.

Only existing FLOOR blocks become beaten-earth road shapes.  No movement
collision, actor position, event, warp, map number or map dimension changes.
The immutable published source makes repeated runs byte-for-byte stable.
PNG output is a compiler reconstruction, never an emulator screenshot.
"""
from collections import deque
from io import BytesIO
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/environment_v025/paths'
BASELINE = '6d2a0be'
DIMS = {
    'PeonOpening': (8, 6), 'GrommashHold': (8, 6), 'TheDen': (12, 10),
    'ValleyOfTrials': (16, 12), 'DurotarRoad': (12, 14),
    'SenjinVillage': (12, 10), 'RazorHill': (12, 10),
    'OrgrimmarGate': (12, 10), 'BurningBladeCavern': (10, 10),
    'PeonTrollHut': (6, 5), 'PeonOrcHut': (6, 5),
    'PeonOrcInn': (6, 5), 'PeonTrollInn': (6, 5),
}
REGIONS = ('TheDen', 'ValleyOfTrials', 'DurotarRoad', 'SenjinVillage',
           'RazorHill', 'OrgrimmarGate', 'BurningBladeCavern')
FLOOR = ('FLOOR',) * 4
WALL = ('WALL',) * 4
ROAD_IDS = {2, 16, *range(17, 27)}
# Coordinates below are 32x32 map blocks, not 16x16 movement cells.
BRANCHES = {
    'TheDen': [(8, 3), (8, 4), (3, 6), (2, 6), (2, 7)],
    'ValleyOfTrials': [(3, 5), (4, 4), (3, 4), (11, 5), (4, 7),
                       (6, 6), (7, 6), (8, 6)],
    'DurotarRoad': [(4, 5), (4, 9), (5, 9)],
    'SenjinVillage': [(2, 3), (3, 3), (4, 3), (7, 3), (7, 4), (8, 5)],
    'RazorHill': [(2, 3), (3, 3), (3, 4), (8, 3), (7, 3), (7, 4),
                  (8, 7), (7, 7), (3, 7)],
}
# Remove the former parallel/checkerboard Den lanes and the redundant Valley
# main-road dogleg.  Their movement cells stay FLOOR, using bare-soil ID 38.
# The Valley's southern quest fork remains at (5,7) and leads to Sarkoth.
RETIRED_ROADS = {
    'TheDen': [(5, 6), (6, 6), (7, 6), (8, 6), (3, 7), (3, 8)],
    'ValleyOfTrials': [(6, 7), (7, 7), (8, 7), (9, 7)],
}
ROAD_SHAPES = {
    'NS': 17, 'EW': 18, 'NE': 19, 'NW': 20, 'SE': 21, 'SW': 22,
    'NSE': 23, 'NSW': 24, 'NEW': 25, 'SEW': 26,
}
OFFSETS = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}
DOOR_IDS = {4, 11, 29}


def original(path):
    return subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def collision_rows(source):
    return [tuple(p.strip() for p in m[1].split(',')) for m in
            re.finditer(r'^\s*tilecoll\s+([^;\n]+)', source, re.M)]


def events(name, kind, source=None):
    source = source or (ROOT / f'maps/{name}.asm').read_text()
    return [{'xy': [int(m[1]), int(m[2])], 'arguments': m[3].strip()}
            for m in re.finditer(rf'^\s*{kind}\s+(\d+),\s*(\d+),\s*(.+)',
                                 source, re.M)]


def build_maps():
    maps = {name: bytearray(original(f'maps/{name}.blk')) for name in DIMS}
    coll = collision_rows(original('data/tilesets/peon_collision.asm').decode())
    for name, additions in BRANCHES.items():
        width, _ = DIMS[name]
        for x, y in RETIRED_ROADS.get(name, []):
            assert maps[name][y * width + x] in ROAD_IDS
            assert coll[maps[name][y * width + x]] == coll[38] == FLOOR
            maps[name][y * width + x] = 38
        roads = {(i % width, i // width) for i, b in enumerate(maps[name])
                 if b in ROAD_IDS}
        for x, y in additions:
            assert coll[maps[name][y * width + x]] == FLOOR, (name, x, y)
        roads.update(additions)
        for x, y in sorted(roads):
            if maps[name][y * width + x] == 16:
                continue  # All four saved transition quadrants remain intact.
            connected = ''.join(k for k in 'NSEW'
                                if (x + OFFSETS[k][0], y + OFFSETS[k][1]) in roads)
            maps[name][y * width + x] = ROAD_SHAPES.get(connected, 2)
    # This decorative cavity has never had a warp.  It is the closed northern
    # prototype boundary, not the Burning Blade entrance.  Both IDs are WALL.
    assert maps['OrgrimmarGate'][2 * 12 + 6] == 15
    assert coll[15] == coll[33] == WALL
    maps['OrgrimmarGate'][2 * 12 + 6] = 33
    return {name: bytes(data) for name, data in maps.items()}


def validate(maps):
    old_cols = collision_rows(original('data/tilesets/peon_collision.asm').decode())
    new_cols = collision_rows((ROOT / 'data/tilesets/peon_collision.asm').read_text())
    result = {}
    for name, data in maps.items():
        width, height = DIMS[name]
        previous = original(f'maps/{name}.blk')
        assert len(data) == len(previous) == width * height
        assert 0 not in data
        for i, (a, b) in enumerate(zip(previous, data)):
            assert old_cols[a] == new_cols[b], (name, i, a, b, 'collision changed')
        old_source = original(f'maps/{name}.asm').decode()
        for kind in ('warp_event', 'coord_event', 'bg_event', 'object_event'):
            assert events(name, kind, old_source) == events(name, kind), (name, kind)

        def collision(p):
            x, y = p
            if not (0 <= x < width * 2 and 0 <= y < height * 2):
                return 'WALL'
            return new_cols[data[y // 2 * width + x // 2]][(y % 2) * 2 + x % 2]

        warps = events(name, 'warp_event')
        actors = events(name, 'object_event')
        start = tuple((warps or actors)[0]['xy'])
        assert collision(start) != 'WALL', (name, start)
        reached = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for p in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if p not in reached and collision(p) != 'WALL':
                    reached.add(p)
                    queue.append(p)
        assert all(tuple(w['xy']) in reached for w in warps), (name, 'warp inaccessible')
        for kind in ('object_event', 'bg_event'):
            if name in ('PeonOpening', 'GrommashHold'):
                continue  # These actors include staged cinematic placements.
            for event in events(name, kind):
                x, y = event['xy']
                assert any(p in reached for p in
                           ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))), (
                               name, kind, event['xy'], 'approach disconnected')
        doors = []
        for warp in warps:
            x, y = warp['xy']
            block = data[y // 2 * width + x // 2]
            if block in DOOR_IDS:
                assert (x % 2, y % 2) == (1, 1), (name, warp)
                approaches = [list(p) for p in
                              ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                              if p in reached]
                doors.append({'movement_xy': [x, y], 'block_id': block,
                              'local_open_quadrant': 'bottom-right',
                              'reachable_approaches': approaches})
        roads = {(i % width, i // width) for i, b in enumerate(data) if b in ROAD_IDS}
        if name in BRANCHES:
            connected = {next(iter(roads))}
            queue = deque(connected)
            while queue:
                x, y = queue.popleft()
                for dx, dy in OFFSETS.values():
                    p = x + dx, y + dy
                    if p in roads and p not in connected:
                        connected.add(p)
                        queue.append(p)
            assert connected == roads, (name, 'disconnected painted road', roads - connected)
        result[name] = {
            'baseline_sha256': sha(previous), 'current_sha256': sha(data),
            'changed_blocks': sum(a != b for a, b in zip(previous, data)),
            'added_path_blocks': [list(p) for p in BRANCHES.get(name, [])],
            'retired_redundant_path_blocks': [list(p) for p in RETIRED_ROADS.get(name, [])],
            'old_movement_collisions_exactly_preserved': True,
            'event_coordinates_arguments_and_actor_order_preserved': True,
            'reachable_movement_cells': len(reached),
            'warp_count': len(warps), 'painted_path_block_count': len(roads),
            'doors': doors,
        }
    assert sum(len(m['doors']) for m in result.values()) == 9
    assert len({m['current_sha256'] for m in result.values()}) == len(result), 'Duplicate map bytes'
    return {
        'baseline_commit': BASELINE, 'all_checks_passed': True, 'maps': result,
        'total_changed_blocks': sum(m['changed_blocks'] for m in result.values()),
        'total_added_path_blocks': sum(len(v) for v in BRANCHES.values()),
        'total_retired_redundant_path_blocks': sum(len(v) for v in RETIRED_ROADS.values()),
        'nine_real_hut_door_quadrants_preserved': True,
        'thirteen_distinct_map_arrays_preserved': True,
        'valley_cave_warp_movement_xy': [24, 4],
        'valley_exit_warp_movement_xy': [28, 12],
        'orgrimmar_fake_cave_removed': True,
        'seven_fixed_screens_implemented': False,
        'rendered_images_are_compiler_reconstructions': True,
    }


def palettes(name, before=False):
    def read(path):
        text = original(path).decode() if before else (ROOT / path).read_text()
        values = [tuple(int(n) for n in m[1].replace(' ', '').split(',')) for m in
                  re.finditer(r'^\s*RGB\s+([^;\n]+)', text, re.M)]
        assert all(len(row) == 12 for row in values)
        return [[tuple((n << 3) | (n >> 2) for n in row[i:i + 3])
                 for i in range(0, 12, 3)] for row in values]
    if name in REGIONS:
        i = REGIONS.index(name)
        return read('gfx/tilesets/peon_regions.pal')[i * 8:(i + 1) * 8]
    if name.startswith('Peon') and name.endswith(('Inn', 'Hut')):
        i = 0 if 'Troll' in name else 1
        return read('gfx/tilesets/peon_interiors.pal')[i * 8:(i + 1) * 8]
    return read('gfx/tilesets/peon_bg.pal')


def render(name, data, before=False, *, dimensions=None, palette_name=None):
    width, height = dimensions or DIMS[name]
    sheet_path = 'gfx/tilesets/peon.png'
    meta_path = 'data/tilesets/peon_metatiles.bin'
    attr_path = 'gfx/tilesets/peon_palette_map.bin'
    sheet = Image.open(BytesIO(original(sheet_path))) if before else Image.open(ROOT / sheet_path)
    meta = original(meta_path) if before else (ROOT / meta_path).read_bytes()
    attrs = original(attr_path) if before else (ROOT / attr_path).read_bytes()
    pals = palettes(palette_name or name, before)
    canvas = Image.new('RGB', (width * 32, height * 32))
    for pos, block in enumerate(data):
        for j, tid in enumerate(meta[block * 16:block * 16 + 16]):
            i = tid if tid < 96 else tid - 32
            tile = sheet.crop((i % 16 * 8, i // 16 * 8, i % 16 * 8 + 8, i // 16 * 8 + 8))
            pal = (attrs[tid // 2] >> (tid % 2 * 4)) & 7
            tile.putpalette([v for c in pals[pal] for v in c] + [0] * 756)
            canvas.paste(tile.convert('RGB'), ((pos % width) * 32 + j % 4 * 8,
                                             (pos // width) * 32 + j // 4 * 8))
    return canvas


def draw_annotations(name, im):
    overlay = im.resize((im.width * 2, im.height * 2), Image.Resampling.NEAREST)
    d = ImageDraw.Draw(overlay)
    for i, warp in enumerate(events(name, 'warp_event'), 1):
        x, y = (v * 32 for v in warp['xy'])
        d.rectangle((x, y, x + 31, y + 31), outline='#80ffff', width=2)
        d.text((x + 2, y + 2), f'W{i}', fill='#ffffff', stroke_width=1, stroke_fill='#000000')
    for x, y in BRANCHES.get(name, []):
        d.rectangle((x * 64, y * 64, x * 64 + 63, y * 64 + 63),
                    outline='#ffed85', width=2)
    wanted = {
        'TheDen': [('Vendor camp', 8, 6), ('Class camp', 6, 12)],
        'ValleyOfTrials': [('Hana\'zua', 10, 19), ('Sarkoth', 16, 20),
                           ('Cave', 24, 4), ('Exit', 28, 12)],
    }
    for label, x, y in wanted.get(name, []):
        d.text((x * 32 + 3, y * 32 + 3), label, fill='#ffffff',
               stroke_width=2, stroke_fill='#13100d')
    caption = Image.new('RGB', (overlay.width, 42), '#19140f')
    d = ImageDraw.Draw(caption)
    d.text((8, 5), 'COMPILER RECONSTRUCTION: cyan = actual warps; amber = added footpaths', fill='#eee2c3')
    d.text((8, 22), 'Existing scrolling map; the requested seven fixed screens are not migrated.', fill='#eee2c3')
    output = Image.new('RGB', (overlay.width, overlay.height + caption.height))
    output.paste(overlay, (0, 0)); output.paste(caption, (0, overlay.height))
    return output


def previews(maps):
    for subdir in ('maps', 'before', 'annotated'):
        (OUT / subdir).mkdir(parents=True, exist_ok=True)
    for name, data in maps.items():
        im = render(name, data)
        im.save(OUT / 'maps' / f'{name}.png')
        im.resize((im.width * 2, im.height * 2), Image.Resampling.NEAREST).save(
            OUT / 'maps' / f'{name}_2x.png')
        old = render(name, original(f'maps/{name}.blk'), before=True)
        old.save(OUT / 'before' / f'{name}_v024.png')
        if name in REGIONS:
            draw_annotations(name, im).save(OUT / 'annotated' / f'{name}_paths_and_real_warps.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true',
                        help='Validate current map bytes without changing them or rendering PNGs.')
    parser.add_argument('--refresh-previews', action='store_true',
                        help='Validate current bytes and redraw previews, without rewriting maps.')
    args = parser.parse_args()
    expected = build_maps()
    if args.check_only or args.refresh_previews:
        maps = {name: (ROOT / f'maps/{name}.blk').read_bytes() for name in DIMS}
        assert maps == expected, 'Current maps differ from the deterministic path plan'
    else:
        maps = expected
        # Validate before any mutation, then emit only maps whose bytes changed.
        validate(maps)
        for name, data in maps.items():
            path = ROOT / f'maps/{name}.blk'
            if path.read_bytes() != data:
                path.write_bytes(data)
    report = validate(maps)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    if not args.check_only:
        previews(maps)
    print(json.dumps({k: v for k, v in report.items() if k != 'maps'}, indent=2))


if __name__ == '__main__':
    main()
