#!/usr/bin/env python3
"""Polish real door lanes and stone thresholds without changing geography.

The existing v0.2.5 vector/pixel drawing functions remain the source for
unchanged scenery. New doorway panels, right-aligned cave opening, path
pebbles and the separately authored Horde emblem compile within 192 slots.
All emitted review files are new v0.2.6 evidence; published v0.2.5 files are
never written. Native map IDs, block arrays, collisions and event rows stay
unchanged. PNG maps/door diagrams are compiler reconstructions, not gameplay.
"""
from collections import Counter
from io import BytesIO
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

from PIL import Image, ImageDraw

import build_peon_environment_v025 as art
import build_peon_wayfinding_v025 as paths
import build_peon_valley_zones_v025 as zones

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/visual_polish_v026/paths_doors'
BASE = 'd2806e2'
OLD_HUT, OLD_DEN, OLD_ROAD = art.horde_hut, art.horde_den, art.road
OLD_SPECIAL = art.special_tiles


def baseline(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def door_panel():
    """One readable 16px foot opening shared by Orc/Troll/large Den doors."""
    panel = Image.new('L', (16, 16), 2)
    d = ImageDraw.Draw(panel)
    d.polygon([(0, 15), (0, 6), (2, 3), (6, 0), (10, 0),
               (14, 4), (15, 7), (15, 15)], fill=3)
    d.polygon([(1, 14), (1, 7), (4, 3), (7, 1), (10, 2),
               (14, 6), (14, 14)], fill=1)
    d.polygon([(3, 15), (3, 7), (5, 5), (8, 3), (11, 5),
               (14, 8), (14, 15)], fill=3)
    # The east-approached Razor hut needs an open right edge, not a solid jamb.
    d.line((15, 7, 15, 12), fill=3)
    d.line((3, 13, 15, 13), fill=1)
    d.line((3, 14, 15, 14), fill=2)
    d.line((3, 15, 15, 15), fill=3)
    return panel


def hut(troll=False):
    canvas = OLD_HUT(troll)
    canvas.indices.paste(door_panel(), (16, 16))
    return art.finish_paint(canvas)


def den():
    canvas = OLD_DEN()
    canvas.indices.paste(door_panel(), (16, 48))
    return art.finish_paint(canvas)


def road(openings, full=False, threshold=False):
    canvas = OLD_ROAD(openings, full=full, threshold=False)
    d = ImageDraw.Draw(canvas.indices)
    # A fixed tile-local pebble is shared along every orientation. It adds
    # texture/relief without introducing a solid border or a false obstacle.
    for ty in range(4):
        for tx in range(4):
            x, y = tx * 8 + 3, ty * 8 + 5
            if canvas.indices.getpixel((x, y)):
                for dx, dy, value in ((1, 0, 2), (1, 1, 3)):
                    if canvas.indices.getpixel((x + dx, y + dy)):
                        d.point((x + dx, y + dy), value)
    if threshold:
        # Low flat stones are a universal map threshold, not a closed door.
        # All four quadrants of ID16 remain WARP_PANEL in native collision.
        d.line((0, 14, 31, 14), fill=2)
        d.line((0, 15, 31, 15), fill=3)
        d.line((0, 16, 31, 16), fill=1)
        for x in (0, 8, 16, 24):
            d.line((x, 14, x, 16), fill=3)
    canvas.mask = canvas.indices.point(lambda n: 255 if n else 0)
    return canvas


def build_blocks():
    from peon_horde_emblem_v026 import horde_emblem_indices
    emblem = horde_emblem_indices()
    assert emblem.mode == 'L' and emblem.size == (16, 16)
    assert set(emblem.tobytes()) <= {1, 3}

    def special(library):
        OLD_SPECIAL(library)
        for i in range(4):
            pixels = emblem.crop((i % 2 * 8, i // 2 * 8,
                                  i % 2 * 8 + 8, i // 2 * 8 + 8))
            library[f'emblem_{i}'] = art.Tile(
                pixels, 6, Image.new('L', (8, 8), 255), f'emblem_{i}')

    saved = art.horde_hut, art.horde_den, art.road, art.special_tiles
    art.horde_hut, art.horde_den, art.road, art.special_tiles = hut, den, road, special
    try:
        blocks, composite, library = art.build_blocks()
    finally:
        art.horde_hut, art.horde_den, art.road, art.special_tiles = saved
    # Cave doorway lies directly above the real right-hand movement lane.
    # Its left half reads as stone, not a second black opening with no warp.
    blocks[15] = art.array([
        ['rock_cap', 'rock_cap', 'cave_arc_l', 'cave_arc_r'],
        ['rock_face', 'rock_seam', 'cave_dark', 'cave_side_r'],
        ['rock_face', 'rock_seam', 'cave_dark', 'cave_side_r'],
        ['rock_foot_l', 'rock_foot_r', 'cave_dark', 'cave_side_r'],
    ], library)
    # Reuse the actual broad geological faces, rather than small generic
    # vertical grooves which would read as timber beside the opening.
    cliff_tiles = list(blocks[1].tiles())
    for y in range(4):
        for x in (0, 1):
            blocks[15].put(cliff_tiles[y * 4 + x], x, y)
    # The watchtower has no enter event. Closed timber shutters distinguish it
    # from the actual dark foot doorway used by linked buildings.
    blocks[31].put(library['timber'], 1, 1)
    blocks[31].put(library['timber'], 2, 1)
    return blocks, composite, library


def frozen_geometry():
    report = {}
    for name, dimensions in zones.DIMS.items():
        path = f'maps/{name}.blk'
        data = (ROOT / path).read_bytes()
        assert data == baseline(path), (name, 'Published map bytes changed')
        source = (ROOT / f'maps/{name}.asm').read_text()
        old_source = baseline(f'maps/{name}.asm').decode()
        kinds = ('warp_event', 'coord_event', 'bg_event', 'object_event')
        for kind in kinds:
            assert paths.events(name, kind, source) == paths.events(name, kind, old_source), (name, kind)
        report[name] = {'blocks': list(dimensions), 'sha256': sha(data),
                        'warps_events_actors_exactly_preserved': True}
    assert (ROOT / 'constants/map_constants.asm').read_bytes() == baseline('constants/map_constants.asm')
    assert (ROOT / 'data/tilesets/peon_collision.asm').read_bytes() == baseline('data/tilesets/peon_collision.asm')
    return report


def original_blocks():
    sheet = Image.open(BytesIO(baseline('gfx/tilesets/peon.png')))
    meta = baseline('data/tilesets/peon_metatiles.bin')
    attrs = baseline('gfx/tilesets/peon_palette_map.bin')
    blocks = []
    for block in range(47):
        canvas = art.Canvas()
        for j, tid in enumerate(meta[block * 16:block * 16 + 16]):
            index = tid if tid < 96 else tid - 32
            pixels = sheet.crop((index % 16 * 8, index // 16 * 8,
                                 index % 16 * 8 + 8, index // 16 * 8 + 8)).convert('L')
            # The committed sheet's palette is monochrome 255/170/85/0.
            pixels = pixels.point(lambda p: (255 - p) // 85)
            pal = (attrs[tid // 2] >> (tid % 2 * 4)) & 7
            canvas.put(art.Tile(pixels, pal, Image.new('L', (8, 8), 255), 'baseline'), j % 4, j // 4)
        blocks.append(canvas)
    return blocks


def compose_den(blocks):
    canvas = art.Canvas((64, 64))
    for i in range(4):
        block = blocks[9 + i]; x, y = i % 2 * 32, i // 2 * 32
        canvas.indices.paste(block.indices, (x, y))
        canvas.mask.paste(block.mask, (x, y))
        canvas.palettes.paste(block.palettes, (x // 8, y // 8))
    return canvas


def reduce_tiles(blocks, library):
    """Use the existing strict silhouette/palette-preserving seven-pixel rule."""
    return art.reduce_shade_variants(blocks, library)


def emit_review(blocks, old_blocks, map_report):
    for folder in ('props', 'blocks', 'maps', 'before', 'annotated'):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    for ident, block in enumerate(blocks):
        im = art.rgba(block)
        im.save(OUT / 'blocks' / f'{ident:02d}_{art.NAMES[ident]}.png')
        assert set(im.getchannel('A').tobytes()) <= {0, 255}
    props = {'orc_hut': 4, 'troll_hut': 29, 'cave_mouth_right_lane': 15,
             'stone_map_threshold': 16, 'horde_banner': 6, 'watchtower_closed_shutters': 31}
    for name, ident in props.items():
        im = art.rgba(blocks[ident])
        im.save(OUT / 'props' / f'{name}_native.png')
        im.resize((256, 256), Image.Resampling.NEAREST).save(OUT / 'props' / f'{name}_8x.png')
    den_image = art.rgba(compose_den(blocks))
    den_image.save(OUT / 'props/the_den_door_native.png')
    den_image.resize((512, 512), Image.Resampling.NEAREST).save(OUT / 'props/the_den_door_8x.png')
    contact = Image.new('RGB', (768, 390), '#25190f')
    d = ImageDraw.Draw(contact)
    for row, ident in enumerate((4, 29, 15)):
        for column, source in enumerate((old_blocks, blocks)):
            im = art.rgba(source[ident], transparent=False).resize((128, 128), Image.Resampling.NEAREST)
            contact.paste(im, (column * 384 + 12, row * 130 + 1))
            d.text((column * 384 + 155, row * 130 + 18),
                   ('v0.2.5 compiled' if column == 0 else 'v0.2.6 compiled') + '\n' + art.NAMES[ident],
                   fill='#f5dfb1')
    contact.save(OUT / 'door_and_cave_before_after_compiler.png')
    for name, dimensions in zones.DIMS.items():
        width, height = dimensions
        pals = paths.palettes('ValleyOfTrials' if name in zones.NEW_NAMES else name)
        data = (ROOT / f'maps/{name}.blk').read_bytes()
        canvas = Image.new('RGB', (width * 32, height * 32))
        for pos, ident in enumerate(data):
            tile = art.rgba(blocks[ident], pals, False).convert('RGB')
            canvas.paste(tile, (pos % width * 32, pos // width * 32))
        canvas.save(OUT / 'maps' / f'{name}.png')
        canvas.resize((width * 64, height * 64), Image.Resampling.NEAREST).save(
            OUT / 'maps' / f'{name}_2x.png')
        overlay = canvas.resize((width * 64, height * 64), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(overlay)
        for warp in zones.warp_events(name):
            x, y = (v * 32 for v in warp['xy'])
            draw.rectangle((x, y, x + 31, y + 31), outline='#86ffff', width=2)
            draw.text((x + 2, y + 2), f"W{warp['index']}", fill='white', stroke_width=1, stroke_fill='black')
        bottom = Image.new('RGB', (overlay.width, overlay.height + 24), '#25190f')
        bottom.paste(overlay)
        ImageDraw.Draw(bottom).text((6, overlay.height + 6),
            'COMPILER VIEW: cyan marks real warp cells; geometry unchanged.', fill='#f5dfb1')
        bottom.save(OUT / 'annotated' / f'{name}_actual_warp_cells.png')
    map_report['native_reconstructions_include_all18_maps'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-only', action='store_true',
                        help='Compile/review without modifying the native graphics inputs.')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    frozen = frozen_geometry()
    blocks, _den, library = build_blocks()
    reduction = reduce_tiles(blocks, library)
    bank, meta, budget = art.compile_tiles(blocks)
    (OUT / 'budget_review.json').write_text(json.dumps({**budget, 'reduction': reduction}, indent=2) + '\n')
    assert len(bank) <= 192, f'{len(bank)} native patterns exceed 192'
    sheet = Image.new('P', (128, 96))
    sheet.putpalette([255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0] + [0] * 756)
    attributes = [7] * 256
    for i, item in enumerate(bank):
        sheet.paste(item.pixels, (i % 16 * 8, i // 16 * 8))
        attributes[art.native_id(i)] = item.palette | (8 if i >= 96 else 0)
    packed = bytes(attributes[i] | attributes[i + 1] << 4 for i in range(0, 256, 2))
    assert len(meta) == 47 * 16 and len(packed) == 128
    old = original_blocks()
    changes = []
    for ident, (before, after) in enumerate(zip(old, blocks)):
        a = art.rgba(before, transparent=False).convert('RGB').tobytes()
        b = art.rgba(after, transparent=False).convert('RGB').tobytes()
        count = sum(a[i:i + 3] != b[i:i + 3] for i in range(0, len(a), 3))
        changes.append({'id': ident, 'name': art.NAMES[ident], 'changed_pixels': count})
    for ident in (4, 11, 29):
        assert blocks[ident].indices.crop((16, 16, 32, 32)).tobytes() == door_panel().tobytes()
    mouth = blocks[15].indices
    assert sum(mouth.getpixel((x, y)) == 3 for x in range(16, 28) for y in range(8, 32)) > 200
    frames = b''.join(bytes(art.encode_2bpp(t.pixels)) for phase in range(3) for t in art.flame_tiles(phase))
    assert frames == baseline('gfx/tilesets/peon_environment_fire.bin')
    if not args.review_only:
        sheet.save(ROOT / 'gfx/tilesets/peon.png')
        (ROOT / 'gfx/tilesets/peon_palette_map.bin').write_bytes(packed)
        (ROOT / 'data/tilesets/peon_metatiles.bin').write_bytes(meta)
        (ROOT / 'gfx/tilesets/peon_environment_fire.bin').write_bytes(frames)
    emit_review(blocks, old, frozen)
    manifest = {'passed': True, 'baseline_commit': BASE, 'review_only': args.review_only,
                'native_inputs_written': not args.review_only,
                'native_sheet_slots': 192, 'native_patterns': len(bank), 'metatile_count': 47,
                'all18_map_arrays_warps_events_actors_and_collision_rows_preserved': True,
                'maps': frozen, 'pixel_changes_from_v025': changes, 'shade_variant_reduction': reduction,
                'horde_emblem_source': 'tools/peon_horde_emblem_v026.py::horde_emblem_indices',
                'huts_and_den_dark_door_panel': 'actual BR 16x16 quadrant, with open east lip',
                'cave_mouth': 'right-hand x16..31 lane aligned over actual map28 warp(5,2)',
                'threshold16': 'flat stone step, four original WARP_PANEL quadrants retained',
                'watchtower': 'closed shutters; no fake foot door',
                'animated_fire_tiles': [0, 1], 'fire_frames_unchanged': True,
                'pngs_are_compiler_reconstructions_not_runtime': True,
                'geometry_changed': False, 'save_format_changed': False}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: v for k, v in manifest.items() if k not in ('maps', 'pixel_changes_from_v025',
                                                                    'shade_variant_reduction')}, indent=2))


if __name__ == '__main__':
    main()
