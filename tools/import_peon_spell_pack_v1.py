#!/usr/bin/env python3
"""Import the four supplied Shaman abilities into native RGBDS graphics.

The canonical PNGs are read only. Every native pixel keeps its source coordinate
and binary alpha; only color is fitted to the Game Boy Color palette budget.
One static frame is imported from each individual file. Animation is supplied
by the battle engine, not by generated or redrawn artwork.
"""
from collections import Counter
from itertools import combinations
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import shutil
import struct
import subprocess

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'references/characters/peon_of_warcraft_spell_effects_pack_v1'
NATIVE = ROOT / 'gfx/peon_spell_pack_v1'
EVIDENCE = ROOT / 'references/generated/spell_tests'
ASM = ROOT / 'gfx/peon_spell_pack_v1.asm'
ABILITIES = [('lightning_bolt', 'Lightning'), ('rockbiter', 'Rockbiter'),
             ('earth_shock', 'EarthShock'), ('earth_totem', 'EarthTotem')]
DMG = [255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0] + [0] * 756
WHITE = (31, 31, 31)
BG6 = [WHITE, (22, 15, 7), (8, 17, 6), (3, 2, 2)]
LZ_FLAGS = ['--matching', '--align', '4']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def rgb555(color):
    return tuple(channel >> 3 for channel in color[:3])


def expand(color):
    return tuple((channel << 3) | (channel >> 2) for channel in color)


def distance(a, b):
    # Integer, source-derived medoids; no averaged colors or dithering.
    return sum(weight * (src - dst) ** 2
               for weight, src, dst in zip((2, 3, 2), a, b))


def color_order(color):
    return (-sum(weight * c for weight, c in zip((2, 3, 2), color)), color)


def palette_bytes(palettes):
    return b''.join(struct.pack('<H', r | g << 5 | b << 10)
                    for palette in palettes for r, g, b in palette)


def encode(pixels):
    result = bytearray()
    for y in range(8):
        row = pixels[y * 8:y * 8 + 8]
        result.extend((sum((value & 1) << (7 - x) for x, value in enumerate(row)),
                       sum((value >> 1) << (7 - x) for x, value in enumerate(row))))
    return bytes(result)


def pixel_list(image):
    return list(image.get_flattened_data())


def tiles(image):
    return [(x, y, image.crop((x, y, x + 8, y + 8)))
            for y in range(0, image.height, 8)
            for x in range(0, image.width, 8)]


def opaque_counts(image):
    return Counter(rgb555(pixel) for pixel in pixel_list(image) if pixel[3])


def fit_palettes(images, count):
    """Choose three real source colors per palette and fit aligned tile groups.

    All source-color triples are evaluated. Deterministic multi-start coordinate
    descent selects a small family whose tile-wise minimum total RGB555 error
    is lowest. An icon has a single family; OBJ frames share three per ability.
    Transparent pixels do not contribute to fitting and always remain index0.
    """
    tile_counts = [opaque_counts(tile) for image in images
                   for _, _, tile in tiles(image) if tile.getchannel('A').getbbox()]
    colors = sorted(set().union(*(set(counter) for counter in tile_counts)))
    assert len(colors) >= 3
    candidates = list(combinations(colors, 3))
    costs = [tuple(sum(n * min(distance(color, dst) for dst in candidate)
                       for color, n in counter.items())
                   for counter in tile_counts) for candidate in candidates]
    def score(selection):
        return sum(min(costs[i][tile] for i in selection)
                   for tile in range(len(tile_counts)))
    ranking = sorted(range(len(candidates)), key=lambda i: (sum(costs[i]), i))
    if count == 1:
        chosen = [ranking[0]]
    else:
        best = None
        for start in ranking[:16]:
            chosen = [start]
            while len(chosen) < count:
                chosen.append(min((i for i in range(len(candidates)) if i not in chosen),
                                  key=lambda i: (score(chosen + [i]), i)))
            # Each accepted substitution strictly improves the tuple, so this
            # fixed-point search cannot oscillate on equal-error palettes.
            while True:
                old = (score(chosen), tuple(sorted(chosen)))
                options = [(old, chosen)]
                for slot in range(count):
                    fixed = chosen[:slot] + chosen[slot + 1:]
                    replacement = min((i for i in range(len(candidates)) if i not in fixed),
                                      key=lambda i: (score(fixed + [i]), tuple(sorted(fixed + [i]))))
                    new = fixed + [replacement]
                    options.append(((score(new), tuple(sorted(new))), new))
                key, new = min(options, key=lambda option: option[0])
                if key >= old:
                    break
                chosen = new
            result = (score(chosen), tuple(sorted(chosen)))
            if best is None or result < best:
                best = result
        chosen = list(best[1])
    opaque = [tuple(sorted(candidates[i], key=color_order)) for i in chosen]
    opaque.sort(key=lambda p: tuple(color_order(c) for c in p))
    return [[WHITE, *palette] for palette in opaque], {
        'source_rgb555_colors': len(colors), 'evaluated_source_color_triples': len(candidates),
        'fit': '16-start coordinate descent over real RGB555 source-color triples',
        'distance_weights_rgb': [2, 3, 2], 'total_weighted_squared_rgb555_error': score(chosen),
        'palette_count': count, 'opaque_colors_per_palette': 3,
        'palette_colors_are_real_source_colors': True}


def convert(image, palettes, bg=False):
    indexes = Image.new('P', image.size)
    indexes.putpalette(DMG)
    rendered = Image.new('RGBA', image.size)
    cells = []
    total_error = 0
    changed555 = 0
    max_error = 0
    exact555 = 0
    opaque_total = 0
    for x, y, tile in tiles(image):
        pixels = pixel_list(tile)
        counts = opaque_counts(tile)
        def score(palette):
            return sum(n * min(distance(color, dst) for dst in palette[1:])
                       for color, n in counts.items())
        palette_index = min(range(len(palettes)), key=lambda i: (score(palettes[i]), i))
        palette = palettes[palette_index]
        converted = []
        for n, pixel in enumerate(pixels):
            if pixel[3]:
                src = rgb555(pixel)
                index = min(range(1, 4), key=lambda i: (distance(src, palette[i]), i))
                error = distance(src, palette[index])
                total_error += error
                max_error = max(max_error, error)
                exact555 += error == 0
                changed555 += error != 0
                opaque_total += 1
                color = (*expand(palette[index]), 255)
            else:
                index = 0
                color = (*expand(WHITE), 255) if bg else (0, 0, 0, 0)
            converted.append(index)
            indexes.putpixel((x + n % 8, y + n // 8), index)
            rendered.putpixel((x + n % 8, y + n // 8), color)
        cells.append({'x': x, 'y': y, 'palette': palette_index,
                      'pixels': bytes(converted), 'nonempty': bool(counts),
                      'source_opaque_rgb555_colors': len(counts),
                      'weighted_squared_rgb555_error': score(palette)})
    if not bg:
        assert rendered.getchannel('A').tobytes() == image.getchannel('A').tobytes()
    return indexes, rendered, cells, {
        'opaque_pixels': opaque_total, 'exact_rgb555_pixels': exact555,
        'changed_rgb555_pixels': changed555,
        'total_weighted_squared_rgb555_error': total_error,
        'mean_weighted_squared_rgb555_error': round(total_error / opaque_total, 6),
        'max_weighted_squared_rgb555_error': max_error,
        'native_scale': 1, 'dithered': False, 'resampled': False,
        'alpha_preserved': not bg, 'full_canvas_preserved': True,
        'opaque_pixels_always_nonzero_index': True}


def run(command):
    subprocess.run([str(arg) for arg in command], cwd=ROOT, check=True)


def compile_png(png, rgbgfx, expected, compress=False):
    binary = png.with_suffix('.2bpp')
    run([rgbgfx, '--colors', 'dmg', '-Weverything', '-o', binary, png])
    assert binary.read_bytes() == expected, f'rgbgfx index mismatch: {relative(png)}'
    result = {'png': relative(png), 'png_sha256': sha(png.read_bytes()),
              '2bpp': relative(binary), '2bpp_sha256': sha(expected),
              '2bpp_bytes': len(expected), 'tiles': len(expected) // 16,
              'rgbgfx_verified_against_expected_indexes': True}
    if compress:
        compressed = Path(str(binary) + '.lz')
        run([ROOT / 'tools/lzcompress', *LZ_FLAGS, '--', binary, compressed])
        check = NATIVE / '.lz_roundtrip.2bpp'
        run([ROOT / 'tools/lzcompress', '--uncompress', '--', compressed, check])
        assert check.read_bytes() == expected, f'LZ roundtrip mismatch: {relative(compressed)}'
        check.unlink()
        result.update({'lz': relative(compressed), 'lz_sha256': sha(compressed.read_bytes()),
                       'lz_bytes': compressed.stat().st_size, 'lz_flags': LZ_FLAGS,
                       'lz_roundtrip_verified': True})
    return result


def load_source(row):
    path = SOURCE / row['file']
    image = Image.open(path)
    assert image.mode == 'RGBA', f'Expected canonical RGBA source: {row["file"]}'
    assert image.size == (int(row['width']), int(row['height']))
    assert image.size in ((16, 16), (16, 32), (32, 32))
    assert set(image.getchannel('A').get_flattened_data()) <= {0, 255}
    return image


def preview(source, native, filename, title):
    # Preview enlargement uses nearest-neighbor only; native PNGs stay 1:1.
    width = max(16, source.width)
    height = max(16, source.height)
    image = Image.new('RGB', (width * 8 + 32, height * 4 + 34), (40, 40, 40))
    draw = ImageDraw.Draw(image)
    draw.text((4, 4), title + ' | source / native', fill='white')
    for slot, art in enumerate((source, native)):
        left = 8 + slot * (width * 4 + 16)
        draw.rectangle((left, 24, left + width * 4 - 1, 24 + height * 4 - 1), fill=(110, 110, 110))
        enlarged = art.resize((art.width * 4, art.height * 4), Image.Resampling.NEAREST)
        image.paste(enlarged, (left, 24), enlarged)
    image.save(filename)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_rgbgfx = shutil.which('rgbgfx') or '/workspace/toolchains/rgbds-1.0.4/rgbgfx'
    parser.add_argument('--rgbgfx', default=os.environ.get('RGBGFX', default_rgbgfx))
    args = parser.parse_args()
    NATIVE.mkdir(parents=True, exist_ok=True)
    previews = EVIDENCE / 'staticpreviews'
    previews.mkdir(parents=True, exist_ok=True)
    with (SOURCE / 'manifest.csv').open(encoding='utf-8-sig', newline='') as handle:
        inventory = list(csv.DictReader(handle))
    before = {relative(path): sha(path.read_bytes()) for path in SOURCE.rglob('*') if path.is_file()}
    asm = ['; Generated by tools/import_peon_spell_pack_v1.py from canonical individual PNGs.',
           '; Include inside SECTION "Peon Spell Effects v1"; no SECTION switches.',
           '; All positions are centered full-canvas coordinates, not alpha-bounding-box crops.',
           '; OBJ color0 is transparent; attributes select OBJ palettes4/5/6.']
    records = []
    packets = []
    audit = []
    for ability, label in ABILITIES:
        rows = [row for row in inventory if row['spell'] == ability
                and row['role'] != 'combined_sheet']
        frames = [row for row in rows if row['role'] != 'icon']
        frames.sort(key=lambda row: {'player_back': 0, 'enemy_front': 1, 'target': 2}[row['orientation']])
        images = [load_source(row) for row in frames]
        palettes, fit = fit_palettes(images, 3)
        pal_path = NATIVE / f'{ability}_obj.gbcpal'
        pal_path.write_bytes(palette_bytes(palettes))
        unique = []
        lookup = {}
        oam_bodies = []
        asset_records = []
        for row, image in zip(frames, images):
            role = {'player_back': 'Player', 'enemy_front': 'Enemy', 'target': 'Impact'}[row['orientation']]
            indexes, rendered, cells, metrics = convert(image, palettes)
            if ability == 'earth_totem' and row['orientation'] == 'player_back':
                persistent_indexes, persistent_rendered = indexes, rendered
                persistent_cells, persistent_metrics = cells, metrics
                persistent_palettes = palettes
            native_png = NATIVE / f'{ability}_{row["orientation"]}.png'
            indexes.save(native_png)
            rgba_png = previews / f'{ability}_{row["orientation"]}_native.png'
            rendered.save(rgba_png)
            preview(image, rendered, previews / f'{ability}_{row["orientation"]}_comparison_4x.png',
                    f'{label} {role}')
            oam = []
            offsets = []
            for cell in cells:
                item = {key: value for key, value in cell.items() if key != 'pixels'}
                item['source_box'] = [cell['x'], cell['y'], cell['x'] + 8, cell['y'] + 8]
                if cell['nonempty']:
                    # Patterns can share one tile even when their palettes differ;
                    # each OAM row independently carries its real palette slot.
                    tile = encode(cell['pixels'])
                    if tile not in lookup:
                        lookup[tile] = len(unique)
                        unique.append(cell['pixels'])
                    tile_index = lookup[tile]
                    attributes = 4 + cell['palette']
                    xcell = cell['x'] // 8 - image.width // 16
                    ycell = cell['y'] // 8 - image.height // 16
                    oam.append((xcell, ycell, tile_index, attributes))
                    item.update({'tile_index': tile_index, 'packet_byte_offset': tile_index * 16,
                                 'oam_pixel_offset': [xcell * 8, ycell * 8],
                                 'oam_palette_slot': attributes})
                else:
                    item.update({'tile_index': None, 'omitted_from_oam': True})
                offsets.append(item)
            prefix = f'PeonSpellV1{label}{role}'
            asm_body = [f'DEF {prefix}OAMCount EQU {len(oam)}', f'{prefix}OAM::',
                        f'; {row["file"]}; SHA256 {sha((SOURCE / row["file"]).read_bytes())}']
            asm_body += [f'\tdbsprite {x}, {y}, 0, 0, ${tile:02x}, ${attr:02x}'
                         for x, y, tile, attr in oam]
            asm_body += [f'\tassert @ - {prefix}OAM == {prefix}OAMCount * 4']
            oam_bodies.extend(asm_body)
            source_colors = opaque_counts(image)
            source_record = {'source': relative(SOURCE / row['file']),
                             'source_sha256': sha((SOURCE / row['file']).read_bytes()),
                             'role': row['role'], 'orientation': row['orientation'],
                             'canvas': list(image.size), 'source_crop': [0, 0, *image.size],
                             'source_alpha_values': sorted(set(image.getchannel('A').get_flattened_data())),
                             'source_alpha_sha256': sha(image.getchannel('A').tobytes()),
                             'native_alpha_sha256': sha(rendered.getchannel('A').tobytes()),
                             'source_alpha_bbox': list(image.getchannel('A').getbbox()),
                             'source_opaque_rgb555_colors': len(source_colors),
                             'source_max_opaque_colors_per_8x8': max(c['source_opaque_rgb555_colors'] for c in cells),
                             'static_source_frames': 1, 'oam_label': prefix + 'OAM',
                             'oam_count': len(oam), 'oam_max_per_8px_row': max(Counter(y for _, y, _, _ in oam).values()),
                             'native_index_png': relative(native_png),
                             'native_index_sha256': sha(native_png.read_bytes()),
                             'static_native_preview': relative(rgba_png),
                             'native_palette_slots': sorted(set(attr for _, _, _, attr in oam)),
                             'tile_offset_records': offsets, 'conversion': metrics}
            asset_records.append(source_record)
            audit.append({key: source_record[key] for key in (
                'source', 'source_sha256', 'canvas', 'source_crop', 'source_alpha_values',
                'source_opaque_rgb555_colors', 'source_max_opaque_colors_per_8x8',
                'oam_count', 'oam_max_per_8px_row', 'conversion')})
        sheet = Image.new('P', (8, len(unique) * 8))
        sheet.putpalette(DMG)
        for n, pixels in enumerate(unique):
            tile = Image.frombytes('P', (8, 8), pixels)
            sheet.paste(tile, (0, n * 8))
        sheet_path = NATIVE / f'{ability}_tiles.png'
        sheet.save(sheet_path)
        packet = compile_png(sheet_path, args.rgbgfx, b''.join(encode(p) for p in unique), True)
        assert packet['tiles'] < 79, f'OBJ VRAM allocation overflow: {ability}'
        prefix = f'PeonSpellV1{label}'
        asm += ['', f'DEF {prefix}GFXTileCount EQU {packet["tiles"]}', f'{prefix}GFX::',
                f'\tINCBIN "{packet["lz"]}"', f'{prefix}OBPalettes::',
                f'\tINCBIN "{relative(pal_path)}"',
                f'\tassert @ - {prefix}OBPalettes == 3 palettes', *oam_bodies]
        packet.update({'ability': ability, 'gfx_label': prefix + 'GFX',
                       'palette_label': prefix + 'OBPalettes', 'obj_palette_slots': [4, 5, 6],
                       'obj_palettes_rgb555': palettes, 'palette_fit': fit,
                       'palette_file': relative(pal_path), 'palette_sha256': sha(pal_path.read_bytes()),
                       'assets': asset_records})
        packets.append(packet)
        # The existing icon loader consumes exactly four row-major tiles and a
        # single BG palette. It may load this palette through a far pointer.
        icon_row = next(row for row in rows if row['role'] == 'icon')
        icon_source = load_source(icon_row)
        icon_palettes, icon_fit = fit_palettes([icon_source], 1)
        icon_indexes, icon_rendered, icon_cells, icon_metrics = convert(icon_source, icon_palettes)
        icon_png = NATIVE / f'{ability}_icon.png'
        icon_indexes.save(icon_png)
        icon_binary = compile_png(icon_png, args.rgbgfx, b''.join(encode(c['pixels']) for c in icon_cells))
        icon_pal_path = NATIVE / f'{ability}_icon.gbcpal'
        icon_pal_path.write_bytes(palette_bytes(icon_palettes))
        icon_rendered.save(previews / f'{ability}_icon_native.png')
        preview(icon_source, icon_rendered, previews / f'{ability}_icon_comparison_4x.png', label + ' icon')
        asm += [f'{prefix}IconGFX::', f'\tINCBIN "{icon_binary["2bpp"]}"',
                f'\tassert @ - {prefix}IconGFX == 4 * LEN_2BPP_TILE',
                f'{prefix}IconPalette::', f'\tINCBIN "{relative(icon_pal_path)}"',
                f'\tassert @ - {prefix}IconPalette == 1 palettes']
        records.append({'ability': ability, 'source': relative(SOURCE / icon_row['file']),
                        'source_sha256': sha((SOURCE / icon_row['file']).read_bytes()),
                        'canvas': [16, 16], 'source_crop': [0, 0, 16, 16],
                        'source_alpha_values': sorted(set(icon_source.getchannel('A').get_flattened_data())),
                        'source_opaque_rgb555_colors': len(opaque_counts(icon_source)),
                        'source_max_opaque_colors_per_8x8': max(c['source_opaque_rgb555_colors'] for c in icon_cells),
                        'source_alpha_sha256': sha(icon_source.getchannel('A').tobytes()),
                        'native_alpha_sha256': sha(icon_rendered.getchannel('A').tobytes()),
                        'gfx_label': prefix + 'IconGFX', 'palette_label': prefix + 'IconPalette',
                        'palette_rgb555': icon_palettes[0], 'palette_fit': icon_fit,
                        'palette_file': relative(icon_pal_path),
                        'palette_sha256': sha(icon_pal_path.read_bytes()),
                        'conversion': icon_metrics, **icon_binary})
    totem_row = next(row for row in inventory if row['spell'] == 'earth_totem'
                     and row['orientation'] == 'player_back')
    totem_source = load_source(totem_row)
    # This is the current portrait palette6, not a replacement palette. Verify
    # that contract before emitting a persistent BG conversion using it.
    assert (ROOT / 'gfx/user_battle_v0211/shaman/back/palettes.bin').read_bytes()[8:16] == palette_bytes([BG6])
    # Retain the initial fixed-BG6 conversion as an unused audit derivative.
    # The runtime uses the three-palette player conversion below as sparse OBJ.
    bg_indexes, bg_rendered, bg_cells, bg_metrics = convert(totem_source, [BG6])
    bg_png = NATIVE / 'earth_totem_bg.png'
    bg_indexes.save(bg_png)
    bg_binary = compile_png(bg_png, args.rgbgfx, b''.join(encode(c['pixels']) for c in bg_cells))
    assert bg_binary['tiles'] == 16
    bg_rendered.save(previews / 'earth_totem_persistent_bg_native.png')
    preview(totem_source, bg_rendered, previews / 'earth_totem_persistent_bg_comparison_4x.png', 'Totem existing BG6')
    persistent_png = NATIVE / 'earth_totem_persistent.png'
    persistent_indexes.save(persistent_png)
    persistent_binary = compile_png(persistent_png, args.rgbgfx,
                                    b''.join(encode(c['pixels']) for c in persistent_cells))
    assert persistent_binary['tiles'] == 16
    persistent_rendered.save(previews / 'earth_totem_persistent_obj_native.png')
    preview(totem_source, persistent_rendered,
            previews / 'earth_totem_persistent_obj_comparison_4x.png', 'Totem persistent OBJ')
    persistent_oam = [(cell['x'] // 8 - 2, cell['y'] // 8 - 2, n, 4 + cell['palette'])
                      for n, cell in enumerate(persistent_cells) if cell['nonempty']]
    asm += ['', 'PeonSpellV1EarthTotemBGTiles::', f'\tINCBIN "{bg_binary["2bpp"]}"',
            '\tassert @ - PeonSpellV1EarthTotemBGTiles == 16 * LEN_2BPP_TILE',
            'PeonSpellV1EarthTotemPersistentGFX::', f'\tINCBIN "{persistent_binary["2bpp"]}"',
            '\tassert @ - PeonSpellV1EarthTotemPersistentGFX == 16 * LEN_2BPP_TILE',
            f'DEF PeonSpellV1EarthTotemPersistentOAMCount EQU {len(persistent_oam)}',
            'PeonSpellV1EarthTotemPersistentOAM::',
            '; Persistent OBJ uses row-major raw tile offsets, VRAM bank1, cast palettes4/5/6, behind BG.']
    asm += [f'\tdbsprite {x}, {y}, 0, 0, ${tile:02x}, OAM_PRIO | OAM_BANK1 | {palette}'
            for x, y, tile, palette in persistent_oam]
    asm += ['\tassert @ - PeonSpellV1EarthTotemPersistentOAM == PeonSpellV1EarthTotemPersistentOAMCount * 4']
    ASM.write_text('\n'.join(asm) + '\n')
    before_after = {relative(path): sha(path.read_bytes()) for path in SOURCE.rglob('*') if path.is_file()}
    assert before_after == before, 'Canonical source changed during import'
    pairs = []
    for ability, _ in ABILITIES:
        back = next(row for row in inventory if row['spell'] == ability and row['orientation'] == 'player_back')
        front = next(row for row in inventory if row['spell'] == ability and row['orientation'] == 'enemy_front')
        player, enemy = load_source(back), load_source(front)
        pairs.append({'ability': ability, 'separate_source_hashes_and_oam_rows': True,
                      'exact_horizontal_rgba_mirrors': player.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes() == enemy.tobytes(),
                      'exact_vertical_rgba_mirrors': player.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes() == enemy.tobytes(),
                      'exact_vertical_alpha_mirrors': player.getchannel('A').transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes() == enemy.getchannel('A').tobytes()})
    manifest = {'source_pack': relative(SOURCE), 'canonical_source_file_count': len(before),
                'all_source_hashes_unchanged': True, 'canonical_source_sha256': before,
                'source_inventory': relative(SOURCE / 'manifest.csv'),
                'generated_by': 'tools/import_peon_spell_pack_v1.py',
                'source_selection': 'Individual icons/player_back/enemy_front/impacts only; no spell_sheets',
                'asm_include': relative(ASM), 'asm_sha256': sha(ASM.read_bytes()),
                'section_contract': 'Include inside same Peon Spell Effects v1 ROMX section as renderer; no SECTION switch',
                'rgbgfx': str(args.rgbgfx), 'rgbgfx_flags': ['--colors', 'dmg', '-Weverything'],
                'lzcompress': 'tools/lzcompress', 'lz_flags': LZ_FLAGS,
                'obj_packet_tile_budget': 78, 'obj_palette_slots': [4, 5, 6],
                'obj_oam_maximum_active_source_entries': 14, 'source_frame_count_per_asset': 1,
                'motion_frames': 'Native battle-engine timing and placement; no invented raster frames',
                'packets': packets, 'icons': records, 'orientation_pairs': pairs,
                'persistent_earth_totem': {
                    'source': relative(SOURCE / totem_row['file']),
                    'source_sha256': sha((SOURCE / totem_row['file']).read_bytes()),
                    'source_crop': [0, 0, 32, 32], 'canvas': [32, 32],
                    'gfx_label': 'PeonSpellV1EarthTotemPersistentGFX',
                    'palette_label': 'PeonSpellV1EarthTotemOBPalettes',
                    'obj_palettes_rgb555': persistent_palettes,
                    'persistent_rendering': 'Sparse OBJ behind BG; no BG canvas writes',
                    'persistent_obj_palette_slots': [4, 5, 6],
                    'bg_palette_is_not_written_by_import': True,
                    'source_alpha_sha256': sha(totem_source.getchannel('A').tobytes()),
                    'transparent_pixels_to_index0': True,
                    'opaque_mask_preserved_as_nonzero_indexes': True,
                    'native_tile_indexes_row_major': list(range(16)),
                    'intended_vram_bank': 1, 'intended_obj_tile_ids': ['$ad', '$bc'],
                    'oam_label': 'PeonSpellV1EarthTotemPersistentOAM',
                    'oam_count': len(persistent_oam), 'oam_attributes': 'OAM_PRIO | OAM_BANK1 | per-tile4/5/6',
                    'oam_tile_offsets': [tile for _, _, tile, _ in persistent_oam],
                    'oam_obj_palette_slots': [palette for _, _, _, palette in persistent_oam],
                    'conversion': persistent_metrics, **persistent_binary},
                'unused_fixed_bg6_derivative': {
                    'gfx_label': 'PeonSpellV1EarthTotemBGTiles',
                    'fixed_existing_bg_palette_slot': 6, 'fixed_existing_bg_palette_rgb555': BG6,
                    'runtime_use': False, 'conversion': bg_metrics, **bg_binary}}
    (EVIDENCE / 'import_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (EVIDENCE / 'asset_audit.json').write_text(json.dumps({
        'source_pngs': audit + records, 'orientation_pairs': pairs,
        'source_unchanged': True, 'binary_alpha_required': True,
        'conversion_policy': 'Only color is fitted; source alpha, pixel coordinates and full canvases preserved',
        'review_evidence': 'staticpreviews are source/native comparisons, not emulator captures',
        'hardware_limits': {'objects_total': 40, 'objects_per_scanline': 10,
                            'native_effect_objects_max': 14, 'native_effect_objects_per_source_row_max': 4},
        'build_and_runtime_validation': 'Owned by integration agent; importer does not claim gameplay validation'
    }, indent=2) + '\n')
    print('Imported canonical Shaman spell frames and icons without source changes.')
    for packet in packets:
        print(f'{packet["ability"]}: {packet["tiles"]} deduplicated tiles, '
              f'{packet["lz_bytes"]} compressed bytes; '
              f'OAM {[asset["oam_count"] for asset in packet["assets"]]}')
    print('Persistent Earth Totem: 16 raw tiles / 13 sparse OBJ, same three cast palettes, no BG palette replacement.')


if __name__ == '__main__':
    main()
