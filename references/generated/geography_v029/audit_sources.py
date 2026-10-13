#!/usr/bin/env python3
"""Read-only reconstruction of native geography, not an emulator screenshot."""
from collections import deque
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import build_peon_valley_zones_v025 as zones
import build_peon_wayfinding_v025 as paths

OUT = Path(__file__).resolve().parent
NAMES = list(zones.ZONE_NAMES.values()) + ['DurotarRoad', 'SenjinVillage']


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def symbols():
    result = {}
    for line in (ROOT / 'pokecrystal.sym').read_text().splitlines():
        match = re.match(r'([0-9a-fA-F]+):([0-9a-fA-F]+)\s+(.+)', line)
        if match:
            result[match[3]] = tuple(int(match[i], 16) for i in (1, 2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    raw = (ROOT / 'pokecrystal.gbc').read_bytes()
    assert digest(raw) == args.expected_sha
    sym = symbols()

    def read(label, length, extra=0):
        bank, address = sym[label]
        offset = bank * 0x4000 + address - 0x4000 if bank else address
        return raw[offset + extra:offset + extra + length]

    native_meta = read('TilesetPeonMeta', 53 * 16)
    assert native_meta == (ROOT / 'data/tilesets/peon_metatiles.bin').read_bytes()
    native_attrs = read('TilesetPeonPalMap', 128)
    assert native_attrs == (ROOT / 'gfx/tilesets/peon_palette_map.bin').read_bytes()
    native_coll = read('TilesetPeonColl', 53 * 4)
    with tempfile.TemporaryDirectory(prefix='peon_geo_rom_') as tmp:
        begin, end = sym['TilesetPeonGFX'], sym['TilesetPeonMeta']
        assert begin[0] == end[0]
        compressed = read('TilesetPeonGFX', end[1] - begin[1])
        packed, decoded = Path(tmp) / 'tiles.lz', Path(tmp) / 'tiles.2bpp'
        packed.write_bytes(compressed)
        subprocess.run([str(ROOT / 'tools/lzcompress'), '-u', str(packed), str(decoded)], check=True)
        tiles = decoded.read_bytes()
    assert len(tiles) == 192 * 16 and tiles == (ROOT / 'gfx/tilesets/peon.2bpp').read_bytes()

    def palette(name):
        number = zones.MAP_NUMBERS[name]
        offset = (number - 14) * 64 if 14 <= number <= 20 else 64
        pal = read('PeonRegionBGPalettes', 64, offset)
        colors = []
        for i in range(0, len(pal), 2):
            value = int.from_bytes(pal[i:i + 2], 'little')
            channels = (value & 31, value >> 5 & 31, value >> 10 & 31)
            colors.append(tuple((v << 3) | (v >> 2) for v in channels))
        return colors

    def pixel_tile(tid, colors):
        index = tid if tid < 96 else tid - 32
        attr = (native_attrs[tid // 2] >> (tid % 2 * 4)) & 0xf
        assert index in range(192)
        bitmap = tiles[index * 16:index * 16 + 16]
        im = Image.new('RGB', (8, 8))
        for y in range(8):
            for x in range(8):
                value = ((bitmap[y * 2] >> (7 - x)) & 1) | (((bitmap[y * 2 + 1] >> (7 - x)) & 1) << 1)
                im.putpixel((x, y), colors[(attr & 7) * 4 + value])
        return im

    def collision(data, w, h, cell):
        x, y = cell
        if not (0 <= x < w * 2 and 0 <= y < h * 2):
            return 7
        block = data[y // 2 * w + x // 2]
        return native_coll[block * 4 + y % 2 * 2 + x % 2]

    maps = {}
    for name in NAMES:
        w, h = zones.DIMS[name]
        data = read(name + '_Blocks', w * h)
        assert data == (ROOT / f'maps/{name}.blk').read_bytes()
        colors = palette(name)
        native = Image.new('RGB', (w * 32, h * 32))
        for pos, block in enumerate(data):
            for cell, tid in enumerate(native_meta[block * 16:block * 16 + 16]):
                native.paste(pixel_tile(tid, colors), (pos % w * 32 + cell % 4 * 8,
                                                      pos // w * 32 + cell // 4 * 8))
        native.save(OUT / (name + '_rom_decoded.png'))
        mask = Image.new('RGBA', native.size)
        draw = ImageDraw.Draw(mask)
        for y in range(h * 2):
            for x in range(w * 2):
                block = data[y // 2 * w + x // 2]
                if block == 1:
                    draw.rectangle((x * 16, y * 16, x * 16 + 15, y * 16 + 15), fill=(230, 20, 20, 100))
                elif block == 33:
                    draw.rectangle((x * 16, y * 16, x * 16 + 15, y * 16 + 15), fill=(255, 244, 193, 115))
                elif block in paths.ROAD_IDS:
                    draw.rectangle((x * 16 + 1, y * 16 + 1, x * 16 + 14, y * 16 + 14),
                                    outline=(82, 255, 121, 185))
        overlay = Image.alpha_composite(native.convert('RGBA'), mask).convert('RGB')
        draw = ImageDraw.Draw(overlay)
        warps = zones.warp_events(name)
        event_bytes = read(name + '_MapEvents', 3 + len(warps) * 5)
        assert event_bytes[:2] == bytes(2) and event_bytes[2] == len(warps)
        warp_proof = []
        for index, warp in enumerate(warps):
            x, y = warp['xy']
            assert collision(data, w, h, (x, y)) == 0x7c
            native_warp = event_bytes[3 + index * 5:8 + index * 5]
            assert tuple(native_warp[:2]) == (y, x)
            assert native_warp[2] == warp['target_warp']
            assert native_warp[3] == 26 and native_warp[4] == zones.MAP_NUMBERS[warp['target_name']]
            draw.ellipse((x * 16 + 1, y * 16 + 1, x * 16 + 14, y * 16 + 14),
                         fill='#22efff', outline='#052538')
            draw.text((x * 16 + 3, y * 16 + 2), str(warp['index']), fill='#052538')
            warp_proof.append(warp | {'native_rom_event_bytes_verified': True,
                                     'cell_is_actual_native_warp_panel': True,
                                     'on_outer_map_edge': x in (0, w * 2 - 1) or y in (0, h * 2 - 1)})
        # Native coordinate events show actual aggro cells, not guessed enemy
        # circles. Their positions/scene bytes are verified from this ROM.
        coord_events = paths.events(name, 'coord_event')
        coord_offset = 3 + len(warps) * 5
        native_coord = read(name + '_MapEvents', 1 + len(coord_events) * 8, coord_offset)
        assert native_coord[0] == len(coord_events)
        for i, event in enumerate(coord_events):
            x, y = event['xy']
            encoded = native_coord[1 + i * 8:9 + i * 8]
            assert tuple(encoded[1:3]) == (y, x)
            assert encoded[0] == (int(event['arguments'].split(',', 1)[0]) & 255)
            draw.rectangle((x * 16 + 2, y * 16 + 2, x * 16 + 13, y * 16 + 13),
                           outline='#ff62da', width=1)
        enlarged = overlay.resize((w * 64, h * 64), Image.Resampling.NEAREST)
        framed = Image.new('RGB', (enlarged.width, enlarged.height + 64), '#201b16')
        framed.paste(enlarged)
        caption = ImageDraw.Draw(framed)
        caption.text((5, enlarged.height + 4), name + ': ROM native / overlay x2', fill='#ffe2ad')
        caption.text((5, enlarged.height + 18), 'Reconstruction, pas capture de jeu.', fill='#ffe2ad')
        caption.text((5, enlarged.height + 32), 'Rouge:murs | Vert:chemin | Cyan:portails', fill='#ffe2ad')
        caption.text((5, enlarged.height + 46), 'Ivoire:porte fortifiee.', fill='#ffe2ad')
        framed.save(OUT / (name + '_collision_warp_overlay_2x.png'))
        roads = {(i % w, i // w) for i, block in enumerate(data) if block in paths.ROAD_IDS}
        connected = {next(iter(roads))} if roads else set()
        todo = deque(connected)
        while todo:
            x, y = todo.popleft()
            for dx, dy in paths.OFFSETS.values():
                pos = (x + dx, y + dy)
                if pos in roads and pos not in connected:
                    connected.add(pos); todo.append(pos)
        maps[name] = {'map_id': zones.MAP_NUMBERS[name], 'blocks': [w, h],
                      'pixels': [w * 32, h * 32], 'gbc_viewport': [160, 144],
                      'horizontal_screens': w * 32 / 160, 'vertical_screens': h * 32 / 144,
                      'block_bytes_sha256': digest(data),
                      'native_blocks_equal_current_source': True, 'warps': warp_proof,
                      'all_painted_road_blocks_connected': roads == connected,
                      'road_block_count': len(roads),
                      'native_coord_event_cells': coord_events,
                      'coordinate_events_verified_from_rom': True}
    edges = []
    for from_name, index, to_name, reverse, direction, a, b in zones.REQUIRED_ROUTE:
        if from_name not in maps:
            continue
        forward = next(w for w in maps[from_name]['warps'] if w['index'] == index)
        other_warps = maps[to_name]['warps'] if to_name in maps else zones.warp_events(to_name)
        backward = next(w for w in other_warps if w['index'] == reverse)
        assert forward['target_name'] == to_name and forward['target_warp'] == reverse
        assert backward['target_name'] == from_name and backward['target_warp'] == index
        edges.append({'from_zone': a, 'to_zone': b, 'from_map': from_name, 'to_map': to_name,
                      'expected_direction': direction, 'from_xy': forward['xy'], 'to_xy': backward['xy'],
                      'reciprocal_warp_indices_correct': True,
                      'source_exit_on_outer_map_edge': forward['on_outer_map_edge'],
                      'destination_on_outer_map_edge': backward.get('on_outer_map_edge')})
    report = {'passed': True, 'rom_sha256': args.expected_sha,
              'native_rom_graphics_metatiles_palettes_collision_and_warps_decoded': True,
              'native_tiled_background_reconstruction_not_runtime_screenshot': True,
              'source_maps_and_rom_bytes_identical': True, 'maps': maps, 'target_edges': edges,
              'red_is_an_annotation_of_mountain_collision_not_a_requested_native_color': True,
              'annotated_user_image_file_not_present': True,
              'reference_geometry_source': 'tools/build_peon_valley_zones_v025.py::REFERENCE_RECTS, measurements from user conversation',
              'native_files_changed': False, 'ram_or_savestate_edits': False}
    # Side-by-side schematic: user's approximate rectangle measurements on
    # the left, whole native maps placed in those rectangles on the right.
    # It deliberately exposes that legacy zones1/2 contain several screens.
    comparison = Image.new('RGB', (1330, 635), '#201b16')
    d = ImageDraw.Draw(comparison)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 10)
    d.text((15, 10), 'Cible: positions des 7 zones, mesures approximatives', font=font, fill='#ffe2ad')
    d.text((675, 10), 'Actuel: cartes entieres decodees depuis la ROM', font=font, fill='#ffe2ad')
    for side in (0, 660):
        for number, (x0, y0, x1, y1) in zones.REFERENCE_RECTS.items():
            name = zones.ZONE_NAMES[number]
            box = (side + x0 + 10, y0 + 40, side + x1 + 10, y1 + 40)
            if side:
                image = Image.open(OUT / (name + '_rom_decoded.png'))
                image = image.resize((x1 - x0, y1 - y0), Image.Resampling.NEAREST)
                comparison.paste(image, box[:2])
                d = ImageDraw.Draw(comparison)
            else:
                d.rectangle(box, fill='#54422e')
                d.text((box[0] + 4, box[1] + 20), name, font=small, fill='#ffe2ad')
            d.rectangle(box, outline='#94d67b', width=2)
            d.text((box[0] + 4, box[1] + 3), str(number), font=font, fill='#c2ff9a', stroke_width=1, stroke_fill='#201b16')
            if side:
                w, h = zones.DIMS[name]
                d.text((box[0] + 4, box[3] - 14), f'{w*32}x{h*32}px', font=small,
                       fill='#fff7da', stroke_width=1, stroke_fill='#201b16')
        for edge in edges:
            a, b = edge['from_zone'], edge['to_zone']
            if a not in zones.REFERENCE_RECTS or b not in zones.REFERENCE_RECTS:
                continue
            ar, br = zones.REFERENCE_RECTS[a], zones.REFERENCE_RECTS[b]
            ax, ay = (ar[0] + ar[2]) / 2 + side + 10, (ar[1] + ar[3]) / 2 + 40
            bx, by = (br[0] + br[2]) / 2 + side + 10, (br[1] + br[3]) / 2 + 40
            d.line((ax, ay, bx, by), fill='#fbd156', width=2)
            t = 0.64
            x, y = ax + (bx-ax)*t, ay + (by-ay)*t
            vx, vy = bx-ax, by-ay
            norm = (vx*vx+vy*vy) ** 0.5
            ux, uy = vx/norm, vy/norm
            d.polygon([(x+ux*7, y+uy*7), (x-ux*5-uy*4, y-uy*5+ux*4),
                       (x-ux*5+uy*4, y-uy*5-ux*4)], fill='#fbd156')
    d.text((15, 603), 'Les fleches montrent les liens; aucun nouveau terrain n\'est implemente. Rouge du plan = montagne bloquante.',
           font=font, fill='#ffe2ad')
    comparison.save(OUT / 'seven_zones_target_vs_native_contact_sheet.png')
    assert digest((ROOT / 'pokecrystal.gbc').read_bytes()) == args.expected_sha
    (OUT / 'native_geography_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'rom_sha256': args.expected_sha, 'maps': len(maps),
                      'reciprocal_edges': len(edges), 'native_files_changed': False}))


if __name__ == '__main__':
    main()
