#!/usr/bin/env python3
"""Derive one quiet soil texture, including transparent scenery backdrops.

The v20 user choice is the plain ochre alternative, not alternating dense and
quiet patches. The floor's base and one complete two-pixel grain come from the
supplied dirt PNG. Native scenery RGB, priority, path borders, collision rows, map blocks and
scripts remain exact. Three unused BG3 slots are separately derived to retain
exact brown scenery colors against the regional soil. Source PNGs and all older packets
are read-only inputs. This tool only writes its two versioned output folders.

The existing shared brazier animation has dirt in its transparent pixels too.
An exterior-only 192-byte phase packet is emitted; the engine must select it
only outside. Its opaque flame indices and the original interior phases remain
exact. There is no source redraw, smoothing, resizing or primitive substitute.
"""
from collections import Counter, defaultdict
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

from PIL import Image

import import_peon_quieter_ground_v0214 as previous
import import_peon_user_environment_v0211 as native
import import_peon_zone_passages_v0213 as passage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/quieter_ground_v0220'
GFX = ROOT / 'gfx/quieter_ground_v0220'
INPUT = ROOT / 'gfx/quieter_ground_v0214'
SOURCE = previous.SOURCE
NAMES = previous.NAMES
GRAIN = ((5, 4), (6, 4))
FLAT_SOURCE_RECT = (0, 0, 4, 4)
FACADE_BACKGROUND_IDS = {4, 9, 10, 11, 12, 29, 31, 34, 39}
CANONICAL_SOIL_BACKING_IDS = {3, 42, 13, 36, 37, 30, 33, 6, 28, 8, 38}
SUFFIXES = ('.2bpp', '.2bpp.lz', '_meta.bin', '_palmap.bin', '_priority.bin', '_coll.asm')
EXTRA_BG3 = ('TheDen', 'RazorHill', 'OrgrimmarGate')
OLD_PATH_GRAIN = {5*8+3: 2, 5*8+4: 2, 6*8+4: 3}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text())


def binary_tile(data, offset, palette=1):
    pixels = bytes(((data[offset+y*2] >> (7-x)) & 1)
                   | (((data[offset+y*2+1] >> (7-x)) & 1) << 1)
                   for y in range(8) for x in range(8))
    return native.Tile(pixels, palette)


def source_stencil():
    source = Image.open(SOURCE).convert('RGB')
    flat = source.crop(FLAT_SOURCE_RECT)
    colors = set(flat.get_flattened_data())
    assert len(colors) == 1, 'The supplied flat soil region is no longer flat'
    base = next(iter(colors))
    assert Counter(source.get_flattened_data()).most_common(1)[0][0] == base
    stencils, groups = previous.grain_groups()
    complete = set(map(tuple, groups[0]['complete_source_grain_pixels']))
    assert set(GRAIN) <= complete
    # The other quiet group is separate. The selected complete horizontal
    # group has exactly these two source cells; no authored line is introduced.
    assert source.getpixel(GRAIN[0]) == source.getpixel(GRAIN[1])
    selected = set()
    for x, y in GRAIN:
        selected.add((x, y))
        for nx, ny in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            if (nx, ny) in complete:
                selected.add((nx, ny))
    assert selected == set(GRAIN), 'The selected grain must be kept complete'
    assert all(stencils[0][y*32+x] == 2 for x, y in GRAIN)
    return {
        'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': sha(SOURCE.read_bytes()),
        'source_size': list(source.size), 'flat_source_rect': list(FLAT_SOURCE_RECT),
        'flat_source_rgb': list(base), 'flat_region_repeated_without_resampling': True,
        'complete_source_grain_pixels': [list(p) for p in GRAIN],
        'source_grain_rgb': [list(source.getpixel(p)) for p in GRAIN],
        'native_indices': {'base': 1, 'dark_grain': 2},
        'detail_pixels_per_32x32': len(GRAIN), 'dense_patch_variants': 0,
    }


def mask_alpha(mask, image, xy):
    alpha = image.getchannel('A').point(lambda a: 255 if a else 0).convert('1')
    mask.paste(1, tuple(xy), alpha)


def soil_lineage(name, size, canonical, passages, architecture, old_manifest):
    """Track actual soil backing through the previous source-composition layers.

    Unlike v14's whole-8x8 exclusion, the final opaque alpha union protects
    individual scenery pixels. Geometry is recovered from recorded clear_rect
    operations and original native soil tiles, never guessed from RGB alone.
    """
    w, h = native.DIMS[name]
    soil = Image.new('1', size)
    protected = Image.new('1', size)
    facade_path = ROOT / f'references/generated/canonical_decor_v0213/{name}_preserved_facade_mask.png'
    facade = Image.open(facade_path).convert('1')
    canonical_folder = ROOT / 'gfx/canonical_decor_v0213'
    _, canonical_blocks, _ = passage.read_packet(name, canonical_folder)
    grain_keys = {t.key for t in canonical_blocks[38]}
    assert all(t.pal == 1 for t in canonical_blocks[38])
    old_report = next(r for r in old_manifest['maps'] if r['map'] == name)
    _, prequiet_blocks, _ = passage.read_packet(name, ROOT / old_report['input_packet'])
    prequiet_data = (previous.OUT / 'baseline/maps' / f'{name}.blk').read_bytes()
    canonical_data = (ROOT / 'references/generated/canonical_decor_v0213/maps' / f'{name}.blk').read_bytes()
    for blocks, data in ((prequiet_blocks, prequiet_data), (canonical_blocks, canonical_data)):
        grid = previous.grid_for(name, blocks, data)
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                if tile.key in grain_keys:
                    soil.paste(1, (x*8, y*8, x*8+8, y*8+8))
    original_data = (native.BASE / 'maps' / f'{name}.blk').read_bytes()
    for record in architecture:
        if record.get('map') != name or not record['source'].endswith('exterior_96x80.png'):
            continue
        x, y = record['world_origin_pixels']
        for by in range(y//32, (y+79)//32+1):
            for bx in range(x//32, (x+95)//32+1):
                if original_data[by*w+bx] in FACADE_BACKGROUND_IDS:
                    soil.paste(1, (bx*32, by*32, bx*32+32, by*32+32))
    report = next(r for r in canonical['maps'] if r['map'] == name)
    source_records = []
    for record in report['imports']:
        path = ROOT / record['source']
        image = Image.open(path).convert('RGBA')
        x, y = record['world_origin_pixels']
        bx, by = record['original_anchor_block']
        if record['original_baseline_metatile'] != 28:
            # v13 clears exactly this complete anchor to the existing soil.
            soil.paste(1, (bx*32, by*32, bx*32+32, by*32+32))
        else:
            # Preserve the exact left coastal-water strip at each palm anchor.
            soil.paste(1, (bx*32+8, by*32, bx*32+32, by*32+32))
            above = original_data[(by-1)*w+bx]
            if above in CANONICAL_SOIL_BACKING_IDS:
                soil.paste(1, (x, y, x+32, y+16))
        mask_alpha(protected, image, (x, y))
        source_records.append({'source': record['source'], 'sha256': sha(path.read_bytes()),
                               'size': list(image.size), 'opaque_pixels': sum(bool(a) for a in image.getchannel('A').get_flattened_data()),
                               'transparent_pixels': sum(not a for a in image.getchannel('A').get_flattened_data()),
                               'world_origin_pixels': [x, y]})
    protected.paste(1, (0, 0), facade)
    if name in passage.NAMES:
        report = next(r for r in passages['maps'] if r['map'] == name)
        for threshold in report['thresholds']:
            xs = [p[0] for p in threshold['corridor_cells']]
            ys = [p[1] for p in threshold['corridor_cells']]
            rect = (min(xs)*16, min(ys)*16, (max(xs)+1)*16, (max(ys)+1)*16)
            assert not facade.crop(rect).getbbox(), (name, 'world corridor overlaps a building')
            # The previous threshold layer clears obsolete props here.
            protected.paste(0, rect)
        for record in report['imports']:
            if record['type'] == 'obsolete gateway marker removed':
                rect = tuple(record['world_rect'])
                assert not facade.crop(rect).getbbox()
                soil.paste(0, rect)
                protected.paste(0, rect)
            elif 'asset' in record:
                image = Image.open(ROOT / record['asset']).convert('RGBA').crop(tuple(record['source_rect']))
                mask_alpha(protected, image, record['world_rect'][:2])
    return soil, protected, source_records


def world_fire():
    source_path = ROOT / 'gfx/tilesets/peon_environment_fire.bin'
    source = source_path.read_bytes()
    assert len(source) == 3*4*16
    phases, reports = [], []
    for phase in range(3):
        path = native.SOURCES / f'brazier_frame_0{phase+1}_16x16.png'
        image = Image.open(path).convert('RGBA')
        assert image.size == (16, 16)
        tiles, changed, opaque = [], 0, 0
        for j in range(4):
            old = binary_tile(source, phase*64+j*16)
            pixels = bytearray(old.pixels)
            for y in range(8):
                for x in range(8):
                    i = y*8+x
                    if image.getpixel((j%2*8+x, j//2*8+y))[3]:
                        opaque += 1
                    else:
                        changed += pixels[i] != 1
                        pixels[i] = 1
            tiles.append(native.Tile(bytes(pixels), old.pal, old.priority))
        phases.append(tiles)
        reports.append({'phase': phase, 'source': str(path.relative_to(ROOT)),
                        'source_sha256': sha(path.read_bytes()),
                        'opaque_source_indices_preserved': opaque,
                        'transparent_background_indices_changed': changed})
    assert len({t.key for t in phases[0]}) == 4
    content = b''.join(native.encode(t) for phase in phases for t in phase)
    (GFX / 'fire_frames_world.bin').write_bytes(content)
    return phases, {'input': str(source_path.relative_to(ROOT)), 'input_sha256': sha(source),
                    'output': str((GFX/'fire_frames_world.bin').relative_to(ROOT)),
                    'output_sha256': sha(content), 'bytes': len(content),
                    'exterior_only_binding_required': True, 'interior_original_untouched': True,
                    'phase_reports': reports}


def extra_ground_palettes():
    """Use a proven-unused BG slot for exact soil behind brown scenery."""
    binary = bytearray()
    lines, records = [], []
    for name in EXTRA_BG3:
        palettes = native.map_palettes(name, native.parse_palettes(ROOT/'gfx/tilesets/peon_bg.pal'))
        palette = (palettes[1][1], palettes[5][0], palettes[5][2], palettes[5][3])
        rgb555 = [tuple(c >> 3 for c in rgb) for rgb in palette]
        for r, g, b in rgb555:
            binary.extend((r | g << 5 | b << 10).to_bytes(2, 'little'))
        lines.append('\tRGB ' + ', '.join(str(c) for rgb in rgb555 for c in rgb) + f' ; {name} unused BG3\n')
        records.append({'map': name, 'slot': 3, 'byte_offset': len(binary)-8,
                        'rgb555': [list(rgb) for rgb in rgb555],
                        'derived_from': ['regional BG1 soil', 'regional BG5 light/brown/ink'],
                        'requires_exterior_only_palette_upload': True})
    assert len(binary) == 24
    (GFX/'ground_bg3.bin').write_bytes(binary)
    (GFX/'ground_bg3.pal').write_text(''.join(lines))
    return {'binary': str((GFX/'ground_bg3.bin').relative_to(ROOT)),
            'binary_sha256': sha(binary), 'bytes': len(binary), 'maps': records}


def export_map(name, canonical, passages, architecture, old_manifest, fire_phases, cached):
    w, h = native.DIMS[name]
    bank, blocks, collision = passage.read_packet(name, INPUT)
    data = (ROOT / 'maps' / f'{name}.blk').read_bytes()
    old_report = next(r for r in old_manifest['maps'] if r['map'] == name)
    assert sha(data) == old_report['output_map_sha256'], (name, 'map differs from frozen v14 packet')
    assert len(data) == w*h
    before = previous.grid_for(name, blocks, data)
    palettes = native.map_palettes(name, native.parse_palettes(ROOT/'gfx/tilesets/peon_bg.pal'))
    original_palettes = list(palettes)
    original = passage.render(before, palettes)
    if name in EXTRA_BG3:
        assert all(t.pal != 3 for block in blocks for t in block), (name, 'BG3 is already used by an input metatile')
        assert all(t.pal != 3 for t in bank[:4])
        palettes[3] = (palettes[1][1], palettes[5][0], palettes[5][2], palettes[5][3])
    soil, protected, source_records = soil_lineage(name, original.size, canonical, passages, architecture, old_manifest)
    fire_lookup = {tile.key: j for j, tile in enumerate(bank[:4])}
    original_fire = (ROOT/'gfx/tilesets/peon_environment_fire.bin').read_bytes()
    assert b''.join(native.encode(t) for t in bank[:4]) == original_fire[:64]
    phase0_alpha = Image.open(native.SOURCES/'brazier_frame_01_16x16.png').convert('RGBA').getchannel('A')
    # Restore the opaque native flame pixels to the proof mask while allowing
    # only its source-transparent background to change in the first quartet.
    for y, row in enumerate(before):
        for x, tile in enumerate(row):
            if tile.key not in fire_lookup:
                continue
            j = fire_lookup[tile.key]
            soil.paste(0, (x*8, y*8, x*8+8, y*8+8))
            alpha = phase0_alpha.crop((j%2*8, j//2*8, j%2*8+8, j//2*8+8))
            mask_alpha(protected, Image.merge('RGBA', (alpha, alpha, alpha, alpha)), (x*8, y*8))
    after = []
    palette_backgrounds = Counter()
    target = palettes[1][1]
    grain_target = palettes[1][2]
    changes, fire_cells = 0, []
    reassigned, path_cells, path_removed, path_added = [], 0, 0, 0
    allowed = soil.copy()
    for y, row in enumerate(before):
        result = []
        for x, tile in enumerate(row):
            if tile.key in fire_lookup:
                j = fire_lookup[tile.key]
                converted = fire_phases[0][j]
                assert converted.pal == tile.pal and converted.priority == tile.priority
                result.append(converted)
                fire_cells.append([x, y, j])
                alpha = phase0_alpha.crop((j%2*8, j//2*8, j%2*8+8, j//2*8+8))
                inverse = alpha.point(lambda a: 0 if a else 255).convert('1')
                allowed.paste(1, (x*8, y*8), inverse)
                continue
            pixels = bytearray(tile.pixels)
            base = min(range(4), key=lambda v: (native.distance(target, palettes[tile.pal][v]), v))
            grain = min(range(4), key=lambda v: (native.distance(grain_target, palettes[tile.pal][v]), v))
            for dy in range(8):
                for dx in range(8):
                    wx, wy = x*8+dx, y*8+dy
                    if not soil.getpixel((wx, wy)) or protected.getpixel((wx, wy)):
                        continue
                    is_grain = (wx%32, wy%32) in GRAIN
                    value = grain if is_grain else base
                    pixels[dy*8+dx] = value
                    if not is_grain:
                        palette_backgrounds[(tile.pal, base, palettes[tile.pal][base])] += 1
            # Existing BG4 road patterns contain one repeated three-pixel V.
            # Clear only those texture indices. In particular, index0 route
            # edges and the dark endpoint rows must remain exact.
            if tile.pal == 4 and not tile.priority:
                touched = False
                for i, value in OLD_PATH_GRAIN.items():
                    wx, wy = x*8+i%8, y*8+i//8
                    if tile.pixels[i] == value and not protected.getpixel((wx, wy)):
                        pixels[i] = 1
                        allowed.putpixel((wx, wy), 1)
                        path_removed += 1
                        touched = True
                for dy in range(8):
                    for dx in range(8):
                        wx, wy = x*8+dx, y*8+dy
                        if (wx%32, wy%32) not in GRAIN or protected.getpixel((wx, wy)):
                            continue
                        i = dy*8+dx
                        if tile.pixels[i] == 1:
                            pixels[i] = 2
                            allowed.putpixel((wx, wy), 1)
                            path_added += 1
                            touched = True
                path_cells += touched
                assert all(old != 0 or pixels[i] == 0 for i, old in enumerate(tile.pixels)), (name, 'route border changed')
            palette = tile.pal
            if name in EXTRA_BG3 and tile.pal == 5:
                mutable = {i for i in range(64) if soil.getpixel((x*8+i%8, y*8+i//8))
                           and not protected.getpixel((x*8+i%8, y*8+i//8))}
                fixed = {original_palettes[tile.pal][v] for i, v in enumerate(tile.pixels) if i not in mutable}
                if mutable and fixed <= set(palettes[3]):
                    palette = 3
                    for i, value in enumerate(tile.pixels):
                        if i not in mutable:
                            pixels[i] = palettes[3].index(original_palettes[tile.pal][value])
                        elif ((x*8+i%8)%32, (y*8+i//8)%32) in GRAIN:
                            pixels[i] = min(range(4), key=lambda v: native.distance(grain_target, palettes[3][v]))
                        else:
                            pixels[i] = 0
                            palette_backgrounds[(tile.pal, base, palettes[tile.pal][base])] -= 1
                            palette_backgrounds[(3, 0, target)] += 1
                    reassigned.append([x, y, len(mutable)])
            result.append(native.Tile(bytes(pixels), palette, tile.priority))
        after.append(result)
    # Existing map block IDs are retained, including the old patch aliases.
    # A shared ID must produce the same final block at every occurrence.
    occurrences = defaultdict(set)
    result_blocks = [list(block) for block in blocks]
    for pos, ident in enumerate(data):
        by, bx = divmod(pos, w)
        block = tuple(after[by*4+dy][bx*4+dx] for dy in range(4) for dx in range(4))
        occurrences[ident].add(block)
        result_blocks[ident] = list(block)
    assert all(len(values) == 1 for values in occurrences.values()), (name, 'would need a map alias')
    text = (ROOT/'maps'/f'{name}.asm').read_text()
    changeblocks = {int(v) for v in re.findall(r'changeblock\s+\d+,\s*\d+,\s*(\d+)', text)}
    if 38 in changeblocks:
        assert name == 'ValleyOfTrials'
        # Harvesting a cactus leaves the same quiet source-derived soil.
        result_blocks[38] = [native.Tile(bytes(2 if (j%4*8+dx, j//4*8+dy) in GRAIN else 1
                                                        for dy in range(8) for dx in range(8)), 1)
                             for j in range(16)]
    image = passage.render(after, palettes)
    protected_count = outside_count = soil_count = 0
    for y in range(h*32):
        for x in range(w*32):
            old, new = original.getpixel((x, y)), image.getpixel((x, y))
            if protected.getpixel((x, y)):
                assert old == new, (name, 'opaque source scenery changed', x, y)
                protected_count += 1
            if not allowed.getpixel((x, y)):
                assert old == new, (name, 'non-soil pixel changed', x, y)
                outside_count += 1
            soil_count += bool(soil.getpixel((x, y))) and not protected.getpixel((x, y))
            changes += old != new
    for y, row in enumerate(after):
        for x, tile in enumerate(row):
            assert tile.priority == before[y][x].priority
            assert tile.pal == before[y][x].pal or (name in EXTRA_BG3 and before[y][x].pal == 5 and tile.pal == 3)
    active = set(data) | {1} | changeblocks
    patterns = list(fire_phases[0])
    lookup = {t.key: i for i, t in enumerate(patterns)}
    meta = []
    for ident, block in enumerate(result_blocks):
        if ident not in active:
            meta.extend([4]*16)
            continue
        for tile in block:
            if tile.key not in lookup:
                lookup[tile.key] = len(patterns)
                patterns.append(tile)
            i = lookup[tile.key]
            meta.append(i if i < 96 else i+32)
    capacity = len(bank)
    assert len(patterns) <= capacity == 216, (name, 'native tile budget', len(patterns), capacity)
    attrs, priority = [7]*256, bytearray(32)
    sheet = Image.new('P', (128, 14*8))
    sheet.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    for i, tile in enumerate(patterns):
        tid = i if i < 96 else i+32
        attrs[tid] = tile.pal | (8 if i >= 96 else 0)
        if tile.priority:
            priority[tid//8] |= 0x80 >> (tid%8)
        sheet.paste(Image.frombytes('L', (8, 8), tile.pixels), (i%16*8, i//16*8))
    output = {'.2bpp': b''.join(native.encode(t) for t in patterns)+bytes((capacity-len(patterns))*16),
              '_meta.bin': bytes(meta),
              '_palmap.bin': bytes(attrs[i] | attrs[i+1] << 4 for i in range(0,256,2)),
              '_priority.bin': bytes(priority),
              # Keep even the old comments/formatting byte-exact.
              '_coll.asm': (INPUT/f'{name}_coll.asm').read_bytes()}
    for suffix, content in output.items():
        (GFX/(name+suffix)).write_bytes(content)
    sheet.save(GFX/f'{name}.png')
    previous_output = cached.get(name, {}).get('output_sha256', {})
    compressed = GFX/f'{name}.2bpp.lz'
    if not (previous_output.get('.2bpp') == sha(output['.2bpp']) and compressed.exists()
            and previous_output.get('.2bpp.lz') == sha(compressed.read_bytes())):
        subprocess.run([str(ROOT/'tools/lzcompress'), '--', str(GFX/f'{name}.2bpp'), str(compressed)],
                       check=True, stdout=subprocess.DEVNULL)
    # Read the emitted native packet back rather than validating only a gallery.
    _, emitted, emitted_rows = passage.read_packet(name, GFX)
    assert emitted_rows == collision and len(emitted) == len(blocks)
    assert passage.render(previous.grid_for(name, emitted, data), palettes).tobytes() == image.tobytes()
    for ident in active:
        assert emitted[ident] == result_blocks[ident]
    assert not any(96 <= t < 128 for t in output['_meta.bin'])
    original.save(OUT/f'{name}_before_native.png')
    image.save(OUT/f'{name}_after_native.png')
    soil.save(OUT/f'{name}_soil_lineage_mask.png')
    protected.save(OUT/f'{name}_protected_source_pixels.png')
    side = Image.new('RGB', (w*64, h*32))
    side.paste(original, (0, 0)); side.paste(image, (w*32, 0))
    side.save(OUT/f'{name}_comparison_native.png')
    closeups = [r for r in source_records if 'rock_' in r['source']] or source_records[:1]
    if closeups:
        r = closeups[0]; x, y = r['world_origin_pixels']; ww, hh = r['size']
        original.crop((x, y, x+ww, y+hh)).resize((ww*4, hh*4), Image.Resampling.NEAREST).save(OUT/f'{name}_prop_before_4x.png')
        image.crop((x, y, x+ww, y+hh)).resize((ww*4, hh*4), Image.Resampling.NEAREST).save(OUT/f'{name}_prop_after_4x.png')
    return {'map': name, 'input_packet': str(INPUT.relative_to(ROOT)),
            'input_sha256': {s: sha((INPUT/(name+s)).read_bytes()) for s in SUFFIXES},
            'output_sha256': {s: sha((GFX/(name+s)).read_bytes()) for s in SUFFIXES},
            'unique_patterns': len(patterns), 'native_pattern_capacity': capacity,
            'native_metatiles': len(blocks), 'map_blocks_sha256_unchanged': sha(data),
            'map_script_sha256_unchanged': sha(text.encode()),
            'map_block_ids_unchanged': True, 'collision_rows_byte_exact': True,
            'movement_cells_unchanged': w*h*4, 'native_pixels_changed': changes,
            'source_opaque_pixels_preserved': protected_count,
            'outside_soil_and_path_texture_pixels_preserved': outside_count,
            'soil_pixels_normalized': soil_count,
            'native_priority_per_world_8x8_cell_exact': True,
            'palette_slots_preserved_except_exact_RGB_BG5_to_unused_BG3': True,
            'BG3_unused_in_every_input_metatile': name in EXTRA_BG3,
            'BG5_to_BG3_cells': reassigned,
            'path_texture_cells': path_cells,
            'path_old_grain_pixels_removed': path_removed,
            'path_source_grain_pixels_added': path_added,
            'path_colors_index0_borders_and_dark_end_bands_exact': True,
            'opaque_source_records': source_records,
            'background_palette_limit': [{'palette': p, 'index': v, 'rgb': list(rgb),
                                          'pixels': count, 'exact_regional_soil_rgb': rgb == target}
                                         for (p, v, rgb), count in sorted(palette_backgrounds.items()) if count],
            'regional_soil_rgb': list(target),
            'animated_cells': fire_cells, 'fire_phase0_matches_exterior_phase_packet': True,
            'all_dense_patch_aliases_use_same_stencil': True,
            'native_after_sha256': sha(image.tobytes()),
            'native_packet_round_trip_exact': True, 'runtime_verified': False,
            'preview_is_native_packet_composition': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    GFX.mkdir(parents=True, exist_ok=True)
    provided_path = ROOT/'references/generated/world_redraw_v0217/source_png_hashes.json'
    provided = load(provided_path)['source_files']
    assert len(provided) == 499
    assert all(sha((ROOT/path).read_bytes()) == expected for path, expected in provided.items())
    protected_paths = [ROOT/'maps'/f'{n}.{ext}' for n in NAMES for ext in ('blk', 'asm')]
    protected_paths += [ROOT/'gfx/tilesets'/n for n in ('peon_bg.pal', 'peon_regions.pal', 'peon_interiors.pal', 'peon_environment_fire.bin')]
    protected_paths += [INPUT/(n+s) for n in NAMES for s in SUFFIXES]
    lineage_paths = [ROOT/'references/generated/canonical_decor_v0213/manifest.json',
                     ROOT/'references/generated/zone_passages_v0213/manifest.json',
                     native.OUT/'manifest.json', previous.OUT/'manifest.json']
    lineage_paths += [native.BASE/'gfx/tilesets'/n for n in ('peon_bg.pal', 'peon_regions.pal', 'peon_interiors.pal')]
    lineage_paths += [ROOT/'tools'/n for n in ('import_peon_quieter_ground_v0214.py',
                                              'import_peon_canonical_decor_v0213.py',
                                              'import_peon_user_environment_v0211.py',
                                              'import_peon_zone_passages_v0213.py')]
    for name in NAMES:
        lineage_paths += [native.BASE/'maps'/f'{name}.blk', previous.OUT/'baseline/maps'/f'{name}.blk',
                          ROOT/'references/generated/canonical_decor_v0213/maps'/f'{name}.blk',
                          ROOT/'references/generated/canonical_decor_v0213'/f'{name}_preserved_facade_mask.png']
        for folder in {ROOT/'gfx/canonical_decor_v0213', passage.GFX if name in passage.NAMES else ROOT/'gfx/canonical_decor_v0213'}:
            lineage_paths += [folder/(name+s) for s in SUFFIXES if s != '.2bpp.lz']
    protected_paths += lineage_paths
    protected_hashes = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in protected_paths}
    canonical = load(ROOT/'references/generated/canonical_decor_v0213/manifest.json')
    passages = load(ROOT/'references/generated/zone_passages_v0213/manifest.json')
    architecture = load(native.OUT/'manifest.json')['source_imports']
    old_manifest = load(previous.OUT/'manifest.json')
    stencil = source_stencil()
    phases, fire_report = world_fire()
    bg3_report = extra_ground_palettes()
    cached = {r['map']: r for r in load(OUT/'manifest.json')['maps']} if (OUT/'manifest.json').exists() else {}
    reports = [export_map(n, canonical, passages, architecture, old_manifest, phases, cached) for n in NAMES]
    assert all(sha((ROOT/path).read_bytes()) == expected for path, expected in provided.items())
    assert all(sha((ROOT/path).read_bytes()) == expected for path, expected in protected_hashes.items())
    manifest = {'version': 'v0.2.20', 'result': 'PASS',
                'native_outputs': str(GFX.relative_to(ROOT)), 'applied': False,
                'user_choice': 'plain ochre soil; no alternate dense patch variant',
                'source_stencil': stencil, 'exterior_fire': fire_report,
                'extra_exterior_BG3': bg3_report,
                'original_source_pngs_byte_exact': len(provided),
                'source_hash_manifest': str(provided_path.relative_to(ROOT)),
                'protected_input_files_sha256': protected_hashes,
                'existing_maps_scripts_palettes_packets_and_interior_fire_untouched': True,
                'opaque_prop_geometry_and_native_RGB_unchanged': True,
                'redraw': False, 'resampling': False, 'engine_changes': False,
                'map_block_changes': False, 'rom_build_performed': False,
                'runtime_verified': False, 'maps': reports,
                'known_limits': [
                    'A scenery tile has four BG colors. Three maps reuse proven-unused BG3 for soil plus the exact old brown/ink/light. Remaining cells needing four opaque colors plus a fifth soil color retain the nearest existing background tone; every opaque prop color stays exact.',
                    'The separate exterior fire phase packet must be selected only on the 13 listed maps. The old shared phase packet must remain selected inside.',
                    'Native previews are decoded packet compositions; emulator checks must follow engine integration.'
                ]}
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'result': 'PASS', 'maps': len(reports),
                      'original_pngs_unchanged': len(provided),
                      'maximum_unique_patterns': max(r['unique_patterns'] for r in reports),
                      'opaque_source_pixels_preserved': sum(r['source_opaque_pixels_preserved'] for r in reports),
                      'collision_cells_unchanged': sum(r['movement_cells_unchanged'] for r in reports),
                      'world_fire_bytes': fire_report['bytes']}))


if __name__ == '__main__':
    main()
