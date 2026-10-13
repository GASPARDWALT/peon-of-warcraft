#!/usr/bin/env python3
"""Compose small readable rooms from complete, unchanged supplied PNG crops.

This deliberately imports a subset of furnishings, rather than calling the
455-pattern source a complete room import. No source pixels are drawn, resized,
filtered or overwritten. Hardware color conversion is a separate output.
Only five interior maps can be applied; exterior assets are never outputs.
"""
from collections import Counter, deque
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'references/characters/razor_hill_inn_gbc/razor_hill_inn_interior_192x160.png'
GFX = ROOT / 'gfx/readable_interiors_v0212'
OUT = ROOT / 'references/generated/readable_interiors_v0212'
MAPS = {'PeonOrcHut': (6, 5), 'PeonOrcInn': (6, 5),
        'PeonTrollHut': (6, 5), 'PeonTrollInn': (6, 5), 'GrommashHold': (8, 6)}
# Each furniture rectangle includes the complete object and its native shadow.
CROPS = {'floor': (88, 56, 104, 72), 'north': (56, 0, 72, 16),
         'west': (0, 64, 16, 80), 'east': (176, 64, 192, 80),
         'south': (32, 144, 48, 160), 'northwest': (0, 0, 16, 16),
         'northeast': (176, 0, 192, 16), 'southwest': (0, 144, 16, 160),
         'southeast': (176, 144, 192, 160), 'bed': (16, 8, 48, 48),
         'bar': (16, 48, 80, 96), 'table': (120, 56, 160, 96),
         'hearth': (80, 80, 128, 120), 'doorway': (72, 128, 120, 160)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def palettes():
    result = []
    for line in (ROOT / 'gfx/tilesets/peon_bg.pal').read_text().splitlines():
        if 'RGB' in line:
            values = [int(v) for v in re.findall(r'\d+', line.split('RGB')[1].split(';')[0])]
            result.append(tuple(tuple((v << 3) | (v >> 2) for v in values[i:i+3])
                                for i in range(0, 12, 3)))
    return result


def distance(a, b):
    return 2 * (a[0]-b[0])**2 + 3 * (a[1]-b[1])**2 + 2 * (a[2]-b[2])**2


def native_tile(image, pals):
    colors = list(image.get_flattened_data())
    counts = Counter(colors)
    palette = min(range(7), key=lambda p: (sum(n * min(distance(c, d) for d in pals[p])
                                              for c, n in counts.items()), p))
    match = {c: min(range(4), key=lambda i: (distance(c, pals[palette][i]), i)) for c in counts}
    return bytes(match[c] for c in colors), palette


def encode(pixels):
    return bytes(v for y in range(8) for v in
                 (sum((pixels[y*8+x] & 1) << (7-x) for x in range(8)),
                  sum(((pixels[y*8+x] >> 1) & 1) << (7-x) for x in range(8))))


def events(name):
    text = (ROOT / f'maps/{name}.asm').read_text()
    actors = [(int(x), int(y)) for x, y in re.findall(r'object_event\s+(\d+),\s*(\d+),', text)]
    return text, actors


def original_collision(name):
    baseline = OUT / 'baseline'
    baseline.mkdir(parents=True, exist_ok=True)
    for suffix, path in [('map.blk', ROOT / f'maps/{name}.blk'),
                         ('coll.asm', ROOT / f'gfx/tilesets/peon_user_environment_v0211/{name}_coll.asm')]:
        target = baseline / f'{name}_{suffix}'
        if not target.exists():
            target.write_bytes(path.read_bytes())
    data = (baseline / f'{name}_map.blk').read_bytes()
    text = (baseline / f'{name}_coll.asm').read_text()
    rows = [tuple(v.strip() for v in line.split('peon_user_tilecoll')[1].split(';')[0].split(','))
            for line in text.splitlines() if 'peon_user_tilecoll' in line]
    return data, rows


def compose(name, source):
    width, height = MAPS[name]
    w, h = width * 32, height * 32
    canvas = Image.new('RGB', (w, h))
    records = []
    def stamp(label, xy):
        box = CROPS[label]
        canvas.paste(source.crop(box), xy)
        records.append({'object': label, 'source_rect': list(box), 'destination_xy': list(xy),
                        'native_scale': 1, 'source_pixels_changed': False})
    for y in range(0, h, 16):
        for x in range(0, w, 16):
            stamp('floor', (x, y))
    for x in range(16, w-16, 16):
        stamp('north', (x, 0)); stamp('south', (x, h-16))
    for y in range(16, h-16, 16):
        stamp('west', (0, y)); stamp('east', (w-16, y))
    for label, xy in [('northwest', (0, 0)), ('northeast', (w-16, 0)),
                      ('southwest', (0, h-16)), ('southeast', (w-16, h-16))]:
        stamp(label, xy)
    furniture = [('bed', (24, 16)), ('bar', (16, 56)),
                 ('table', (136, 48)), ('hearth', (112, 96))]
    doorway = (64, h-32)
    if name == 'GrommashHold':
        furniture = [('bed', (24, 16)), ('bar', (16, 128)),
                     ('table', (208, 48)), ('hearth', (192, 128))]
        doorway = (104, h-32)
    for label, xy in furniture:
        stamp(label, xy)
    furniture_rects = [(label, (x, y, x+CROPS[label][2]-CROPS[label][0],
                                y+CROPS[label][3]-CROPS[label][1]))
                       for label, (x, y) in furniture]
    door_rect = (doorway[0], doorway[1], doorway[0]+48, doorway[1]+32)
    for label, rect in furniture_rects:
        assert not (max(rect[0], door_rect[0]) < min(rect[2], door_rect[2])
                    and max(rect[1], door_rect[1]) < min(rect[3], door_rect[3])), (name, 'door overwrites furnishing', label)
    for i, (label, rect) in enumerate(furniture_rects):
        for other, other_rect in furniture_rects[i+1:]:
            assert not (max(rect[0], other_rect[0]) < min(rect[2], other_rect[2])
                        and max(rect[1], other_rect[1]) < min(rect[3], other_rect[3])), (name, 'furniture crops overlap', label, other)
    stamp('doorway', doorway)
    # Collision describes solid objects, not the shadow/floor in their crops.
    cells = [['FLOOR'] * (w//16) for _ in range(h//16)]
    for y in range(h//16):
        for x in range(w//16):
            if x in (0, w//16-1) or y in (0, h//16-1):
                cells[y][x] = 'WALL'
    solids = []
    for label, (x, y) in furniture:
        if label == 'bed': box = (x, y, x+32, y+40)
        elif label == 'bar': box = (x, y, x+64, y+40)
        elif label == 'table': box = (x+8, y+8, x+40, y+32)
        else: box = (x+8, y+8, x+40, y+32)
        solids.append({'object': label, 'world_rect': list(box)})
        # A movement cell is solid only if its centre lies in the object body.
        for cy in range(h//16):
            for cx in range(w//16):
                if box[0] <= cx*16+8 < box[2] and box[1] <= cy*16+8 < box[3]:
                    cells[cy][cx] = 'WALL'
    door_x = 5 if name != 'GrommashHold' else 8
    door_y = h//16-1
    cells[door_y][door_x] = 'WARP_PANEL' if name != 'GrommashHold' else 'FLOOR'
    cells[door_y-1][door_x] = 'FLOOR'
    return canvas, cells, records, solids, (door_x, door_y)


def compile_room(name, source, pals):
    image, cells, imports, solids, door = compose(name, source)
    width, height = MAPS[name]
    patterns, lookup, blocks, collisions = [], {}, [], []
    def tile_id(tile):
        if tile not in lookup:
            lookup[tile] = len(patterns); patterns.append(tile)
        i = lookup[tile]
        return i if i < 96 else i+32
    # IDs 0..66 retain existing collision meanings; active map IDs start at67.
    oldmap, oldrows = original_collision(name)
    border = Image.new('RGB', (32, 32))
    for y in (0, 16):
        for x in (0, 16): border.paste(source.crop(CROPS['south']), (x, y))
    border_tiles = [tile_id(native_tile(border.crop((x, y, x+8, y+8)), pals))
                    for y in range(0, 32, 8) for x in range(0, 32, 8)]
    blocks = [list(border_tiles) for _ in range(67)]
    collisions = list(oldrows[:67])
    collisions[1] = collisions[51] = ('WALL',)*4
    data = bytearray()
    native = Image.new('RGB', image.size)
    for by in range(height):
        for bx in range(width):
            block = []
            for ty in range(4):
                for tx in range(4):
                    x, y = bx*32+tx*8, by*32+ty*8
                    tile = native_tile(image.crop((x, y, x+8, y+8)), pals)
                    block.append(tile_id(tile))
                    native.paste(Image.frombytes('RGB', (8, 8), b''.join(bytes(pals[tile[1]][p]) for p in tile[0])), (x, y))
            row = tuple(cells[by*2+q//2][bx*2+q%2] for q in range(4))
            matches = [i for i in range(67, len(blocks)) if blocks[i] == block and collisions[i] == row]
            ident = matches[0] if matches else len(blocks)
            if not matches: blocks.append(block); collisions.append(row)
            data.append(ident)
    assert len(blocks) < 128, (name, 'metatile index overflow', len(blocks))
    count = len(patterns)
    image.save(OUT / f'{name}_source_composition.png')
    native.save(OUT / f'{name}_native.png')
    native.resize((native.width*4, native.height*4), Image.Resampling.NEAREST).save(OUT / f'{name}_native_4x.png')
    assert count <= 192, (name, 'native tile budget exceeded', count)
    attrs = [7] * 256
    sheet = Image.new('P', (128, 96))
    sheet.putpalette([255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0]+[0]*756)
    for i, (pixels, pal) in enumerate(patterns):
        sheet.paste(Image.frombytes('L', (8, 8), pixels), (i%16*8, i//16*8))
        attrs[i if i < 96 else i+32] = pal | (8 if i >= 96 else 0)
    outputs = {f'{name}.2bpp': b''.join(encode(p) for p, _ in patterns)+bytes((192-count)*16),
               f'{name}_meta.bin': bytes(t for b in blocks for t in b),
               f'{name}_palmap.bin': bytes(attrs[i] | attrs[i+1] << 4 for i in range(0, 256, 2)),
               f'{name}_priority.bin': bytes(32),
               f'{name}_coll.asm': ''.join('\tpeon_user_tilecoll '+', '.join(row)+f' ; {i:02x}\n'
                                          for i, row in enumerate(collisions)).encode()}
    sheet.save(GFX / f'{name}.png')
    _, actors = events(name)
    occupied = set(actors)
    seed = door if name != 'GrommashHold' else (8, 8)
    assert cells[seed[1]][seed[0]] != 'WALL'
    reached = {seed}; queue = deque([seed])
    def adjacent(xy):
        x, y = xy
        return ((x-1, y), (x+1, y), (x, y-1), (x, y+1))
    while queue:
        for x, y in adjacent(queue.popleft()):
            if 0 <= x < width*2 and 0 <= y < height*2 and (x, y) not in reached and (x, y) not in occupied and cells[y][x] != 'WALL':
                reached.add((x, y)); queue.append((x, y))
    for actor in actors:
        assert cells[actor[1]][actor[0]] == 'FLOOR', (name, 'actor on furniture', actor)
        assert any(p in reached for p in adjacent(actor)), (name, 'isolated actor', actor)
    if name != 'GrommashHold':
        # Preserve existing saved landings and the independent Hearth return.
        for required in ((5, 6), (5, 7), (5, 8), (6, 4)):
            assert cells[required[1]][required[0]] == 'FLOOR' and (required in reached or required in occupied), (name, 'protected landing blocked', required)
        if name.endswith('Inn'):
            for furnishing in ((2, 2), (9, 4)):
                assert any(p in reached for p in adjacent(furnishing)), (name, 'furnishing event isolated', furnishing)
    relocations = []
    for y in range(height*2):
        for x in range(width*2):
            before = oldrows[oldmap[y//2*width+x//2]][y%2*2+x%2]
            if before != 'WALL' and cells[y][x] == 'WALL':
                safe = min((p for p in reached if p != door), key=lambda p: (abs(p[0]-x)+abs(p[1]-y), p[1], p[0]))
                relocations.append({'old': [x, y], 'safe': list(safe)})
    return outputs, bytes(data), {'map': name, 'dimensions': list(image.size), 'patterns': count,
        'pattern_budget': 192, 'metatiles': len(blocks), 'imports': imports, 'solid_bodies': solids,
        'door': list(door), 'existing_npcs': [list(p) for p in actors], 'reachable_cells': len(reached),
        'all_npc_approaches_reachable': True, 'continue_relocations': relocations,
        'source_composition_sha256': sha(image.tobytes()), 'native_png_sha256': sha((OUT/f'{name}_native.png').read_bytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True); GFX.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert('RGB'); pals = palettes()
    source_hash = sha(SOURCE.read_bytes())
    results = []; graphics = []; attributes = []; header_lines = []; relocations = []
    for name in MAPS:
        outputs, data, report = compile_room(name, source, pals)
        results.append(report)
        for path, content in outputs.items(): (GFX/path).write_bytes(content)
        subprocess.run([str(ROOT/'tools/lzcompress'), '--', str(GFX/f'{name}.2bpp'),
                        str(GFX/f'{name}.2bpp.lz')], check=True)
        label = f'PeonReadable{name}'
        folder = f'gfx/readable_interiors_v0212/{name}'
        graphics += [f'SECTION "Readable interior {name} v0212", ROMX',
                     label+'GFXV0212::', f'INCBIN "{folder}.2bpp.lz"',
                     label+'MetaV0212::', f'INCBIN "{folder}_meta.bin"',
                     label+'CollV0212::', f'INCLUDE "{folder}_coll.asm"', '']
        attributes += [label+'PalMapV0212::', f'INCBIN "{folder}_palmap.bin"',
                       f'assert BANK({label}PalMapV0212) == BANK(_LoadOverworldAttrmapPals)',
                       label+'PriorityV0212::', f'INCBIN "{folder}_priority.bin"',
                       f'assert BANK({label}PriorityV0212) == BANK(_LoadOverworldAttrmapPals)', '']
        header_lines += [f'; {name}', f'\tdba {label}GFXV0212, {label}MetaV0212, {label}CollV0212',
                         f'\tdw TilesetHouseAnim, {label}PriorityV0212, {label}PalMapV0212']
        constants = {'GrommashHold': 'GROMMASH_HOLD', 'PeonOrcHut': 'PEON_ORC_HUT',
                     'PeonOrcInn': 'PEON_ORC_INN', 'PeonTrollHut': 'PEON_TROLL_HUT', 'PeonTrollInn': 'PEON_TROLL_INN'}
        for move in report['continue_relocations']:
            relocations += ['\tmap_id '+constants[name], '\tdb '+', '.join(map(str, move['old']+move['safe']))]
        (OUT / f'{name}.blk').write_bytes(data)
        if args.apply:
            (ROOT / f'maps/{name}.blk').write_bytes(data)
            text, _ = events(name)
            if name != 'GrommashHold':
                text = re.sub(r'(warp_event\s+)5,\s*(?:7|9),', r'\g<1>5, 9,', text)
                # Events follow the complete bed and table in the new room.
                text = re.sub(r'(bg_event\s+)2,\s*3,', r'\g<1>2, 2,', text)
                text = re.sub(r'(bg_event\s+)8,\s*4,', r'\g<1>9, 4,', text)
                (ROOT / f'maps/{name}.asm').write_text(text)
    (GFX/'graphics.asm').write_text('\n'.join(graphics))
    (GFX/'palettes.asm').write_text('\n'.join(attributes))
    (GFX/'headers.asm').write_text('\n'.join(header_lines)+'\n')
    (GFX/'continue_relocations.asm').write_text('; Append before the existing relocation-table terminator.\n'+'\n'.join(relocations)+'\n')
    (GFX/'background.pal').write_text((ROOT/'gfx/tilesets/peon_bg.pal').read_text())
    assert sha(SOURCE.read_bytes()) == source_hash, 'Supplied source changed during import'
    report = {'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': source_hash,
              'full_source_room_import': False, 'source_redrawn': False, 'native_scale': 1,
              'conversion': 'Each 8x8 cell selects one of the existing seven warm scene palettes; slot7 remains the font.',
              'excluded_source': 'Additional north beds, lower table, animal hide, loose barrels, banner repetitions and asymmetric full-room wall texture; these are not claimed as imported.',
              'external_facades_changed': False, 'external_warp_indices_changed': False,
              'saved_fields_changed': False, 'static_source_hearth': True, 'applied_maps': args.apply,
              'rooms': results}
    (OUT/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({r['map']: {'patterns': r['patterns'], 'reachable': r['reachable_cells']} for r in results}))


if __name__ == '__main__':
    main()
