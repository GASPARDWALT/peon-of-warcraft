#!/usr/bin/env python3
"""Reduce floor grain only; keep source scenery and all movement cells exact.

The user requested fewer details in the ground on 2026-10-14. This is an
explicit floor derivation, not a claim that the canonical PNG was imported
unchanged. Two complete grain groups from the supplied Durotar PNG punctuate
the quiet floor. Three more complete groups make occasional irregular patches.
No primitive shape, smoothing, source overwrite, or historical generator is used.
"""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess

from PIL import Image
import import_peon_user_environment_v0211 as native
import import_peon_zone_passages_v0213 as passage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/quieter_ground_v0214'
GFX = ROOT / 'gfx/quieter_ground_v0214'
PACK = ROOT / 'references/characters/peon_of_warcraft_environment_pack_v2_art_quality'
SOURCE = PACK / 'durotar_valley/ground_durotar_dirt_01_32x32.png'
NAMES = ('PeonOpening', *passage.NAMES, 'BurningBladeCavern')
QUIET_ANCHORS = ((5, 4), (4, 20))
PATCH_ANCHORS = ((18, 9), (4, 16), (11, 17))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def grain_groups():
    """Select complete four-connected source grains, retaining their coordinates."""
    source = Image.open(SOURCE).convert('RGB')
    colors = list(source.get_flattened_data())
    base = Counter(colors).most_common(1)[0][0]
    detail = {i for i, color in enumerate(colors) if abs(sum(color) - sum(base)) >= 45}
    groups = {}
    while detail:
        seed = min(detail)
        group = {seed}
        todo = [seed]
        detail.remove(seed)
        while todo:
            i = todo.pop()
            x, y = i % 32, i // 32
            for nx, ny in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                j = ny*32+nx
                if 0 <= nx < 32 and 0 <= ny < 32 and j in detail:
                    detail.remove(j)
                    group.add(j)
                    todo.append(j)
        for i in group:
            groups[(i % 32, i // 32)] = group
    records = []
    stencils = []
    for anchors in (QUIET_ANCHORS, QUIET_ANCHORS + PATCH_ANCHORS):
        indices = [1]*1024
        selected = set()
        for anchor in anchors:
            group = groups[anchor]
            assert 2 <= len(group) <= 8, (anchor, 'expected an intact small source grain')
            selected.update(group)
        for i in selected:
            indices[i] = 0 if sum(colors[i]) > sum(base) else 2
        stencils.append(indices)
        records.append({'source_grain_anchors': list(anchors),
                        'complete_source_grain_pixels': [[i % 32, i // 32] for i in sorted(selected)],
                        'nonbackground_pixels_per_32x32': len(selected),
                        'source_geometry_unchanged': True,
                        'native_shade_mapping': {'base': 1, 'lighter_grain': 0, 'darker_grain': 2}})
    return stencils, records


def protection(name, size):
    """All opaque source props and approved facade pixels are immutable."""
    mask = Image.new('1', size)
    canonical = json.loads((ROOT/'references/generated/canonical_decor_v0213/manifest.json').read_text())
    report = next(r for r in canonical['maps'] if r['map'] == name)
    for record in report['imports']:
        image = Image.open(ROOT/record['source']).convert('RGBA')
        mask.paste(image.getchannel('A').point(lambda a: 255 if a else 0).convert('1'),
                   tuple(record['world_origin_pixels']))
    facade = ROOT/'references/generated/canonical_decor_v0213'/f'{name}_preserved_facade_mask.png'
    if facade.exists():
        existing = Image.open(facade).convert('1')
        mask.paste(1, (0, 0), existing)
    if name in passage.NAMES:
        manifest = json.loads((passage.OUT/'manifest.json').read_text())
        report = next(r for r in manifest['maps'] if r['map'] == name)
        for record in report['imports']:
            if 'asset' not in record:
                continue
            image = Image.open(ROOT/record['asset']).convert('RGBA').crop(tuple(record['source_rect']))
            x, y = record['world_rect'][:2]
            mask.paste(1, (x, y), image.getchannel('A').point(lambda a: 255 if a else 0).convert('1'))
    return mask


def grid_for(name, blocks, data):
    w, h = native.DIMS[name]
    return [[blocks[data[(y//4)*w+x//4]][y%4*4+x%4] for x in range(w*4)]
            for y in range(h*4)]


def import_map(name, stencils):
    w, h = native.DIMS[name]
    folder = passage.GFX if name in passage.NAMES else ROOT/'gfx/canonical_decor_v0213'
    bank, blocks, rows = passage.read_packet(name, folder)
    baseline = OUT/'baseline/maps'/f'{name}.blk'
    if not baseline.exists():
        baseline.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/f'maps/{name}.blk', baseline)
    original_data = baseline.read_bytes()
    # Stable canonical meaning38 is explicitly retained by the previous import.
    # An inactive meaning8 in a later packet may instead refer to a cliff slot.
    _, canonical_blocks, _ = passage.read_packet(name, ROOT/'gfx/canonical_decor_v0213')
    grain_keys = {tile.key for tile in canonical_blocks[38]}
    assert all(tile.pal == 1 for tile in canonical_blocks[38])
    before = grid_for(name, blocks, original_data)
    pals = native.map_palettes(name, native.parse_palettes(ROOT/'gfx/tilesets/peon_bg.pal'))
    original = passage.render(before, pals)
    protected = protection(name, original.size)
    # A block shared with any protected source pixel keeps that entire8x8 cell.
    blocked = set()
    for pos, ident in enumerate(original_data):
        bx, by = pos % w, pos // w
        for j in range(16):
            x, y = bx*32+j%4*8, by*32+j//4*8
            if protected.crop((x, y, x+8, y+8)).getbbox():
                blocked.add((ident, j))

    def transformed(ident, stencil):
        result = list(blocks[ident])
        for j, tile in enumerate(result):
            cell = (j//4//2)*2+j%4//2
            if tile.key not in grain_keys or tile.priority or rows[ident][cell] == 'WALL' or (ident, j) in blocked:
                continue
            x, y = j % 4*8, j//4*8
            pixels = bytes(stencil[(y+dy)*32+x+dx] for dy in range(8) for dx in range(8))
            result[j] = native.Tile(pixels, tile.pal, tile.priority)
        return result

    result_blocks = [transformed(i, stencils[0]) for i in range(len(blocks))]
    result_rows = list(rows)
    data = bytearray(original_data)
    patches = []
    for pos, ident in enumerate(original_data):
        bx, by = pos % w, pos // w
        # A few intact groups in open ground; irregular grain outlines make no
        # square tile-border edge. Never place a patch over an actor or prop.
        if rows[ident] != ('FLOOR',)*4 or not all(t.key in grain_keys for t in blocks[ident]):
            continue
        if (bx*7+by*3+len(name)) % 11 != 0:
            continue
        if any((ident, j) in blocked for j in range(16)):
            continue
        patch = transformed(ident, stencils[1])
        aliases = [i for i, b in enumerate(result_blocks) if b == patch and result_rows[i] == rows[ident]]
        alias = aliases[0] if aliases else len(result_blocks)
        if not aliases:
            result_blocks.append(patch)
            result_rows.append(rows[ident])
        assert alias < 128, (name, 'native metatile limit', alias)
        data[pos] = alias
        patches.append([bx, by])

    after = grid_for(name, result_blocks, data)
    image = passage.render(after, pals)
    changed_pixels = protected_pixels = unchanged_cells = 0
    for y in range(h*32):
        for x in range(w*32):
            old, new = original.getpixel((x, y)), image.getpixel((x, y))
            if protected.getpixel((x, y)):
                assert old == new, (name, 'opaque canonical scenery changed', x, y)
                protected_pixels += 1
            changed_pixels += old != new
    for y, row in enumerate(after):
        for x, tile in enumerate(row):
            assert tile.pal == before[y][x].pal and tile.priority == before[y][x].priority
            unchanged_cells += tile == before[y][x]
    for pos, ident in enumerate(data):
        assert result_rows[ident] == rows[original_data[pos]], (name, 'collision changed', pos)

    # Only active blocks and scripted changeblock meanings consume tile budget.
    active = set(data) | {1}
    text = (ROOT/f'maps/{name}.asm').read_text()
    active.update(int(v) for v in re.findall(r'changeblock\s+\d+,\s*\d+,\s*(\d+)', text))
    patterns = list(bank[:4])
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
    assert len(patterns) <= capacity <= 216, (name, 'native tile budget', len(patterns), capacity)
    assert patterns[:4] == bank[:4]
    attrs = [7]*256
    priority = bytearray(32)
    sheet = Image.new('P', (128, ((capacity+15)//16)*8))
    sheet.putpalette([255,255,255,170,170,170,85,85,85,0,0,0]+[0]*756)
    for i, tile in enumerate(patterns):
        tid = i if i < 96 else i+32
        attrs[tid] = tile.pal | (8 if i >= 96 else 0)
        if tile.priority:
            priority[tid//8] |= 0x80 >> (tid % 8)
        sheet.paste(Image.frombytes('L', (8,8), tile.pixels), (i % 16*8, i//16*8))
    outputs = {'.2bpp': b''.join(native.encode(t) for t in patterns)+bytes((capacity-len(patterns))*16),
               '_meta.bin': bytes(meta),
               '_palmap.bin': bytes(attrs[i] | attrs[i+1] << 4 for i in range(0, 256, 2)),
               '_priority.bin': bytes(priority),
               '_coll.asm': ''.join('\tpeon_user_tilecoll '+', '.join(row)+f' ; {i:02x} identical_v0213_collision\n'
                                    for i, row in enumerate(result_rows)).encode()}
    for suffix, content in outputs.items():
        (GFX/(name+suffix)).write_bytes(content)
    sheet.save(GFX/f'{name}.png')
    subprocess.run([str(ROOT/'tools/lzcompress'), '--', str(GFX/f'{name}.2bpp'), str(GFX/f'{name}.2bpp.lz')],
                   check=True, stdout=subprocess.DEVNULL)
    (OUT/'maps'/f'{name}.blk').write_bytes(data)
    original.save(OUT/f'{name}_before_native.png')
    image.save(OUT/f'{name}_after_native.png')
    protected.save(OUT/f'{name}_protected_source_pixels.png')
    side = Image.new('RGB', (w*64, h*32))
    side.paste(original, (0, 0))
    side.paste(image, (w*32, 0))
    side.save(OUT/f'{name}_comparison_native.png')
    # Exact PPU-sized crops: source preview only; runtime screenshots follow build.
    crop = (max(0, w*16-80), max(0, h*16-72))
    for suffix, im in (('before', original), ('after', image)):
        view = im.crop((crop[0], crop[1], crop[0]+160, crop[1]+144))
        view.save(OUT/f'{name}_{suffix}_160x144.png')
        view.resize((640,576), Image.Resampling.NEAREST).save(OUT/f'{name}_{suffix}_160x144_4x.png')
    return {'map': name, 'input_packet': str(folder.relative_to(ROOT)),
            'input_packet_sha256': sha((folder/f'{name}.2bpp').read_bytes()),
            'native_pattern_capacity': capacity, 'unique_patterns': len(patterns),
            'metatiles': len(result_blocks), 'sparse_detail_patch_blocks': patches,
            'native_pixels_changed': changed_pixels, 'opaque_scenery_pixels_preserved': protected_pixels,
            'unchanged_native_8x8_cells': unchanged_cells, 'native_8x8_cells': w*h*16,
            'collision_cells_unchanged': w*h*4, 'per_cell_palette_and_priority_unchanged': True,
            'native_map_source_sha256': sha((ROOT/f'maps/{name}.asm').read_bytes()),
            'source_pngs_unchanged': True, 'animated_patterns_0_to_3_unchanged': True,
            'runtime_verified': False, 'preview_is_source_composition': True,
            'native_after_sha256': sha(image.tobytes()), 'output_map_sha256': sha(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Bind staged packets and apply only block aliases.')
    parser.add_argument('--apply-staged', action='store_true', help='Bind a previously verified preview without regenerating it.')
    parser.add_argument('--verify-rom', type=Path, help='Read-only check of exact final ROM packet bindings.')
    parser.add_argument('--symbols', type=Path, help='Same-build RGBDS symbols for --verify-rom.')
    args = parser.parse_args()
    if args.verify_rom:
        assert args.symbols, '--verify-rom requires --symbols'
        verify_rom(args.verify_rom, args.symbols)
        return
    if args.apply_staged:
        manifest = json.loads((OUT/'manifest.json').read_text())
        assert sha(SOURCE.read_bytes()) == manifest['source_sha256']
        for report in manifest['maps']:
            name = report['map']
            assert sha((ROOT/report['input_packet']/f'{name}.2bpp').read_bytes()) == report['input_packet_sha256']
            assert sha((OUT/'maps'/f'{name}.blk').read_bytes()) == report['output_map_sha256']
            assert sha((ROOT/f'maps/{name}.asm').read_bytes()) == report['native_map_source_sha256']
            baseline = OUT/'baseline/maps'/f'{name}.blk'
            if not baseline.exists():
                baseline.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/f'maps/{name}.blk', baseline)
        apply(manifest['maps'])
        manifest['applied'] = True
        (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        print('Applied verified quieter-ground packets for 13 maps; event scripts unchanged.')
        return
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'maps').mkdir(exist_ok=True)
    GFX.mkdir(parents=True, exist_ok=True)
    stencils, records = grain_groups()
    reports = [import_map(name, stencils) for name in NAMES]
    for index, stencil in enumerate(stencils):
        im = Image.frombytes('P', (32,32), bytes(stencil))
        pals = native.map_palettes('TheDen', native.parse_palettes(ROOT/'gfx/tilesets/peon_bg.pal'))
        im.putpalette(sum((list(c) for c in pals[1]), [])+[0]*756)
        im.save(OUT/f'ground_derivation_{index}_32x32.png')
    manifest = {'authorized_change': 'User requests less aggressive ground grain, with detail only in patches.',
                'canonical_grain_source': str(SOURCE.relative_to(ROOT)), 'source_sha256': sha(SOURCE.read_bytes()),
                'native_background_index': 1, 'native_regional_palettes_unchanged': True,
                'original_texture_sources_preserved': True, 'derivation': records,
                'redrawn_shapes': False, 'smoothing': False, 'interiors_changed': False,
                'warps_and_map_scripts_unchanged': True, 'applied': args.apply, 'maps': reports}
    if args.apply:
        apply(reports)
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({r['map']: {'patterns': r['unique_patterns'], 'capacity': r['native_pattern_capacity'],
                                'patches': len(r['sparse_detail_patch_blocks'])} for r in reports}))


def apply(reports):
    for report in reports:
        name = report['map']
        shutil.copyfile(OUT/'maps'/f'{name}.blk', ROOT/f'maps/{name}.blk')
    for source in (ROOT/'gfx/peon_user_environment_v0211.asm', ROOT/'gfx/peon_user_environment_palettes_v0211.asm'):
        text = source.read_text()
        for name in NAMES:
            for prior in ('gfx/zone_passages_v0213', 'gfx/canonical_decor_v0213'):
                text = text.replace(f'{prior}/{name}', f'gfx/quieter_ground_v0214/{name}')
        source.write_text(text)


def verify_rom(rom_path, symbol_path):
    cartridge = rom_path.read_bytes()
    symbols = {}
    for line in symbol_path.read_text().splitlines():
        match = re.match(r'([0-9a-fA-F]+):([0-9a-fA-F]{4})\s+(\S+)', line)
        if match:
            symbols[match[3]] = (int(match[1], 16), int(match[2], 16))

    def bound(label, content):
        bank, address = symbols[label]
        offset = bank*0x4000+address-(0x4000 if bank else 0)
        assert cartridge[offset:offset+len(content)] == content, (label, 'cartridge binding differs')

    manifest = json.loads((OUT/'manifest.json').read_text())
    assert manifest['applied'] and len(manifest['maps']) == len(NAMES)
    checks = []
    codes = {'FLOOR': 0, 'WALL': 7, 'WARP_PANEL': 0x7c}
    for report in manifest['maps']:
        name = report['map']
        for label, suffix in (('GFX', '.2bpp.lz'), ('Meta', '_meta.bin'), ('PalMap', '_palmap.bin'), ('Priority', '_priority.bin')):
            bound('PeonUserEnv'+name+label, (GFX/(name+suffix)).read_bytes())
        bound('PeonUserEnv'+name+'Coll', bytes(codes[c] for row in passage.rows(GFX/f'{name}_coll.asm') for c in row))
        data = (ROOT/f'maps/{name}.blk').read_bytes()
        assert sha(data) == report['output_map_sha256']
        assert sha((ROOT/f'maps/{name}.asm').read_bytes()) == report['native_map_source_sha256']
        bound(name+'_Blocks', data)
        assert symbols['PeonUserEnv'+name+'PalMap'][0] == symbols['_LoadOverworldAttrmapPals'][0]
        checks.append({'map': name, 'native_graphics_metatiles_palette_priority_collision_blocks_exact': True,
                       'event_script_sha256_unchanged': True, 'patterns': report['unique_patterns'],
                       'capacity': report['native_pattern_capacity']})
    result = {'result': 'PASS', 'rom': str(rom_path), 'rom_sha256': sha(cartridge),
              'ordinary_runtime_playtest': False, 'maps': checks}
    (OUT/'native_binding_validation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'result': 'PASS', 'native_packet_bindings': len(checks), 'rom_sha256': result['rom_sha256']}))


if __name__ == '__main__':
    main()
